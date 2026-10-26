import json
import pytest
from app.services.projections import ProjectionStore

def assert_sheet(sheet):
    xi,bench=sheet["startingXI"],sheet["bench"]
    assert len(xi)==11 and len(bench)==4
    assert sum(p["position"]=="GK" for p in xi)==1 and bench[0]["position"]=="GK"
    assert sum(p["position"]=="DEF" for p in xi)>=3
    assert sum(p["position"]=="MID" for p in xi)>=2
    assert sum(p["position"]=="FWD" for p in xi)>=1
    assert len({p["playerId"] for p in xi+bench})==15
    assert sum(p["isCaptain"] for p in xi)==1 and sum(p["isViceCaptain"] for p in xi)==1
    cap=next(p for p in xi if p["isCaptain"]);vice=next(p for p in xi if p["isViceCaptain"])
    assert cap["playerId"]!=vice["playerId"]
    assert cap["projectedPoints"]==max(p["projectedPoints"] for p in xi)
    assert vice["projectedPoints"]==sorted((p["projectedPoints"] for p in xi),reverse=True)[1]
    assert sheet["xiProjection"]==pytest.approx(sum(p["projectedPoints"] for p in xi))
    assert sheet["captainBonus"]==pytest.approx(cap["projectedPoints"])
    assert sheet["projectedTotal"]==pytest.approx(sheet["xiProjection"]+sheet["captainBonus"])
    assert [p["projectedPoints"] for p in bench[1:]]==sorted((p["projectedPoints"] for p in bench[1:]),reverse=True)

def test_health_docs_openapi(setup_api):
    client,_,_=setup_api
    assert client.get("/health").json()=={"status":"ok"}
    assert client.get("/docs").status_code==200
    spec=client.get("/openapi.json").json()
    for endpoint in ("/team/{team_id}","/optimize/team-sheet","/optimize/transfers"):assert endpoint in spec["paths"]

def test_real_shaped_team_5406_and_cache(setup_api):
    client,app,state=setup_api
    for _ in range(2):
        response=client.get("/team/5406")
        assert response.status_code==200,response.text
        data=response.json()
        assert len(data["players"])==15 and data["diagnostics"]["matchedCount"]==15
        assert data["bank"]==.4 and data["squadSourceGw"]==8
    assert app.state.projections.parse_count==1
    assert sum(p.endswith("/history/") for p in state["calls"])==1

def test_free_hit_restores_pre_chip_squad(setup_api):
    client,_,state=setup_api
    state["chips"]=[{"name":"freehit","event":8}]
    data=client.get("/team/5406").json()
    assert data["freeHitDetected"] and data["squadSourceGw"]==7
    assert {p["playerId"] for p in data["players"]}==set(range(1,16))
    assert not any("/event/8/" in p for p in state["calls"])

def test_multi_gw_existing_optimizer(setup_api):
    client,_,_=setup_api
    response=client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9,10]})
    assert response.status_code==200,response.text
    sheets=response.json()["gameweeks"]
    for sheet in sheets:assert_sheet(sheet)
    assert {p["playerId"] for p in sheets[0]["startingXI"]}!={p["playerId"] for p in sheets[1]["startingXI"]}

@pytest.mark.parametrize("count",[0,1,2,3])
def test_transfers_legal_and_preview(setup_api,count):
    client,_,_=setup_api
    body={"teamId":5406,"gameweeks":[9],"numberOfTransfers":count,"transferHit":4,"bankOverride":.4,"excludedPlayerIds":[100]}
    response=client.post("/optimize/transfers",json=body)
    assert response.status_code==200,response.text
    data=response.json();ids=set(range(1,16))
    assert data["moneyInBank"]==.4
    assert len(data["recommendations"])<=10
    for option in data["recommendations"]:
        outs=[m["out"]["playerId"] for m in option["moves"]];ins=[m["in"]["playerId"] for m in option["moves"]]
        assert len(set(outs))==len(outs) and len(set(ins))==len(ins)
        assert not set(ins)&ids and 100 not in ins
        assert all(m["out"]["position"]==m["in"]["position"] for m in option["moves"])
        assert len(option["updatedSquadIds"])==15
        assert option["bankAfter"]>=0
        assert option["netGain"]==pytest.approx(option["grossGain"]-option["transferCost"])
    best=data["recommendations"][0]
    preview=client.post("/optimize/transfers/preview",json=body|{"moves":[{"outId":m["out"]["playerId"],"inId":m["in"]["playerId"]} for m in best["moves"]]})
    assert preview.status_code==200,preview.text
    for sheet in preview.json()["updatedTeamSheet"]["gameweeks"]:assert_sheet(sheet)

def test_roll_wins_and_no_hit_is_charged(setup_api):
    client,app,_=setup_api
    snap=app.state.projections.get()
    # Test input makes every non-owned player weaker; no optimizer rule is changed.
    for pid in range(100,104):
        snap.frame.loc[snap.frame["Player ID"]==pid,["GW9","GW10"]]=0.
    response=client.post("/optimize/transfers",json={"teamId":5406,"gameweeks":[9],"numberOfTransfers":3,"transferHit":12})
    assert response.status_code==200,response.text
    best=response.json()["recommendations"][0]
    assert best["id"]=="roll" and best["netGain"]==0 and best["transferCost"]==0

@pytest.mark.parametrize("change",[
    {"teamId":0},{"teamId":True},{"gameweeks":[9,9]},{"gameweeks":[39]},
    {"gameweeks":[8]},{"numberOfTransfers":4},{"bankOverride":-1},{"excludedPlayerIds":[0]},
    {"projectionPath":"private/file.xlsx"},{"transferHit":True}])
def test_invalid_requests(setup_api,change):
    client,_,_=setup_api
    response=client.post("/optimize/transfers",json={"teamId":5406,"gameweeks":[9]}|change)
    assert response.status_code==422,response.text
    assert "Traceback" not in response.text and "private/file.xlsx" not in response.text

def test_missing_player_is_visible_and_blocks_optimization(setup_api,fixture_data):
    client,_,_=setup_api
    path,payload,_=fixture_data
    payload["projections"]=[r for r in payload["projections"] if r["playerId"]!=15]
    path.write_text(json.dumps(payload))
    team=client.get("/team/5406").json()
    assert len(team["players"])==15 and team["diagnostics"]["matchedCount"]==14
    assert team["diagnostics"]["missingPlayers"][0]["playerId"]==15
    response=client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9]})
    assert response.status_code==503 and response.json()["error"]["code"]=="missing_projections"

def test_errors_no_paths(setup_api):
    client,app,state=setup_api
    state["historyStatus"]=404
    assert client.get("/team/999999").status_code==404
    state["historyStatus"]=503
    assert client.get("/team/5406").status_code==503
    app.state.projections.path=app.state.projections.path.with_name("private-missing.json")
    response=client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9]})
    assert response.status_code==503 and "private-missing" not in response.text

def test_cors_sizes_and_version(setup_api):
    client,_,_=setup_api
    response=client.options("/optimize/transfers",headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"POST","Access-Control-Request-Headers":"content-type"})
    assert response.status_code==200 and response.headers["access-control-allow-origin"]=="http://localhost:5173"
    response=client.options("/team/5406",headers={"Origin":"https://untrusted.example","Access-Control-Request-Method":"GET"})
    assert "access-control-allow-origin" not in response.headers
    assert client.post("/optimize/team-sheet",content="x"*17000,headers={"Content-Type":"application/json"}).status_code==413
    assert client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9],"modelUpdatedAt":"stale"}).status_code==409

def test_bounded_concurrency_and_safe_500(setup_api,monkeypatch):
    client,app,_=setup_api
    capacity=app.state.optimizer.capacity
    capacity.acquire()
    try:
        response=client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9]})
        assert response.status_code==503 and response.headers["retry-after"]=="5"
    finally:capacity.release()
    def broken(*args):raise RuntimeError("private/secret/path")
    monkeypatch.setattr(app.state.optimizer.core,"calculate_multi_gw_team_sheets",broken)
    response=client.post("/optimize/team-sheet",json={"teamId":5406,"gameweeks":[9]})
    assert response.status_code==500 and "private/secret/path" not in response.text



def test_bank_affordability_and_club_limits(setup_api,fixture_data):
    from collections import Counter
    client,_,_=setup_api
    path,payload,_=fixture_data
    for row in payload["projections"]:
        if row["playerId"]>=100:
            row["price"]=7.
            row["club"]="C0"
    path.write_text(json.dumps(payload))
    body={"teamId":5406,"gameweeks":[9],"numberOfTransfers":1}
    first=client.post("/optimize/transfers",json=body)
    assert first.status_code==200,first.text
    assert first.json()["recommendations"][0]["id"]=="roll"
    response=client.post("/optimize/transfers",json=body|{"bankOverride":2.})
    assert response.status_code==200,response.text
    data=response.json();assert data["moneyInBank"]==.4 and data["bankUsed"]==2.
    assert data["recommendations"][0]["moves"]
    by_id={r["playerId"]:r for r in payload["projections"]}
    for r in data["recommendations"]:
        assert r["bankAfter"]==pytest.approx(2-r["cost"])
        assert max(Counter(by_id[i]["club"] for i in r["updatedSquadIds"]).values())<=3

@pytest.mark.parametrize("moves",[
    [{"outId":1,"inId":1}],
    [{"outId":1,"inId":101}],
    [{"outId":1,"inId":100},{"outId":1,"inId":102}],
    [{"outId":1,"inId":100},{"outId":2,"inId":100}],
])
def test_preview_rejects_illegal_batches(setup_api,moves):
    client,_,_=setup_api
    response=client.post("/optimize/transfers/preview",json={
        "teamId":5406,"gameweeks":[9],"numberOfTransfers":3,"moves":moves})
    assert response.status_code==422,response.text

