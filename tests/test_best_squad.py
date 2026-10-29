from collections import Counter
from pathlib import Path
import json
import pytest
from app.services.projections import ProjectionStore
from app.services.rules import load_module

ROOT=Path(__file__).resolve().parents[1]

def legal(data,budget,bans=()):
    players=data["players"];xi=data["startingXI"];bench=data["bench"]
    ids={p["playerId"] for p in players}
    assert len(players)==len(ids)==15
    assert Counter(p["position"] for p in players)=={"GK":2,"DEF":5,"MID":5,"FWD":3}
    assert max(Counter(p["club"] for p in players).values())<=3
    assert not ids.intersection(bans)
    assert sum(p["price"] for p in players)<=budget+1e-8
    assert data["squadCost"]==pytest.approx(sum(p["price"] for p in players))
    assert len(xi)==11 and len(bench)==4
    assert {p["playerId"] for p in xi}.isdisjoint(p["playerId"] for p in bench)
    assert {p["playerId"] for p in xi+bench}==ids
    counts=Counter(p["position"] for p in xi)
    assert counts["GK"]==1 and counts["DEF"]>=3 and counts["MID"]>=2 and counts["FWD"]>=1
    assert bench[0]["position"]=="GK"
    assert [p["projectedPoints"] for p in bench[1:]]==sorted((p["projectedPoints"] for p in bench[1:]),reverse=True)
    assert data["captainPlayerId"] in {p["playerId"] for p in xi}
    assert sum(p["isCaptain"] for p in players)==1
    assert data["captain"]["projectedPoints"]==max(p["projectedPoints"] for p in xi)
    assert data["xiProjection"]==pytest.approx(sum(p["projectedPoints"] for p in xi))
    assert data["captainBonus"]==data["captain"]["projectedPoints"]
    assert data["projectedTotal"]==pytest.approx(data["xiProjection"]+data["captainBonus"])

@pytest.mark.parametrize("budget",[95.,100.,105.,115.])
def test_real_export_budgets_and_streamlit_equivalence(setup_api,budget):
    client,app,state=setup_api
    app.state.projections.path=ROOT/"data/projections.json"
    service=app.state.optimizer;snapshot=service.snapshot()
    week=snapshot.gameweeks[0]
    response=client.post("/optimize/best-squad",json={"gameweek":week,"budget":budget,"banned_player_ids":[]})
    assert response.status_code==200,response.text
    data=response.json();legal(data,budget)
    rules=load_module("best_squad_rules.py")
    candidates=rules.get_squad_candidates(snapshot.frame,[f"GW{week}"])
    expected=rules.build_best_squad(candidates,f"GW{week}",budget)
    assert data["squadProjection"]==pytest.approx(expected[f"GW{week}"].sum())
    expected_xi=service.core.calculate_multi_gw_team_sheets(expected,[f"GW{week}"])[0]
    assert data["xiProjection"]==pytest.approx(expected_xi["starting_xi_base"])
    assert not state["calls"]  # No FPL entry lookup or model refresh required.

def test_real_export_ban_reoptimizes_by_id(setup_api):
    client,app,_=setup_api;app.state.projections.path=ROOT/"data/projections.json"
    week=app.state.optimizer.snapshot().gameweeks[0]
    first=client.post("/optimize/best-squad",json={"gameweek":week,"budget":100.}).json()
    banned=[first["captainPlayerId"]]
    result=client.post("/optimize/best-squad",json={"gameweek":week,"budget":100.,"banned_player_ids":banned})
    assert result.status_code==200,result.text
    legal(result.json(),100.,banned)

def test_duplicate_names_are_independent_and_bans_use_ids(setup_api,fixture_data):
    client,_,_=setup_api;path,payload,_=fixture_data
    for row in payload["projections"]:
        if row["playerId"] in [1,2]:row["name"]="Palmer"
    path.write_text(json.dumps(payload))
    both=client.post("/optimize/best-squad",json={"gameweek":9,"banned_player_ids":[100]}).json()
    assert {p["playerId"] for p in both["players"] if p["name"]=="Palmer"}=={1,2}
    response=client.post("/optimize/best-squad",json={"gameweek":9,"banned_player_ids":[1]})
    assert response.status_code==200,response.text
    data=response.json();legal(data,100.,[1])
    assert any(p["playerId"]==2 and p["name"]=="Palmer" for p in data["players"])

@pytest.mark.parametrize("body",[
 {"budget":94.9},{"budget":115.1},{"budget":100.01},{"budget":True},
 {"banned_player_ids":[1,1]},{"banned_player_ids":[999999]},
 {"gameweek":38},{"gameweek":True},{"modelUpdatedAt":"old"},
])
def test_invalid_best_squad_requests(setup_api,body):
    client,_,_=setup_api
    response=client.post("/optimize/best-squad",json={"gameweek":9}|body)
    assert response.status_code==(409 if "modelUpdatedAt" in body else 422),response.text

def test_infeasible_pool_and_budget(setup_api,fixture_data):
    client,_,_=setup_api;path,payload,_=fixture_data
    response=client.post("/optimize/best-squad",json={"gameweek":9,"banned_player_ids":[1,2,100]})
    assert response.status_code==422 and response.json()["error"]["code"]=="no_legal_squad"
    for row in payload["projections"]:row["price"]=10.
    path.write_text(json.dumps(payload))
    response=client.post("/optimize/best-squad",json={"gameweek":9,"budget":95.})
    assert response.status_code==422 and response.json()["error"]["code"]=="no_legal_squad"
