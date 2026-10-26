import json
from dataclasses import replace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.services.fpl import FplClient

@pytest.fixture
def fixture_data(tmp_path):
    positions=["GK"]*2+["DEF"]*5+["MID"]*5+["FWD"]*3
    rows=[]
    metadata=[]
    for i,pos in enumerate(positions):
        metadata.append({"id":i+1,"web_name":f"Owned {i+1}","team":i//3+1,"element_type":{"GK":1,"DEF":2,"MID":3,"FWD":4}[pos],"now_cost":50})
        for gw,points in ((9,i+1),(10,15-i)):
            rows.append(dict(playerId=i+1,name=f"Owned {i+1}",club=f"C{i//3}",position=pos,price=5.,gameweek=gw,fixture="OPP (H)",projectedPoints=float(points),minutesFactor=1.))
    for i,pos in enumerate(("GK","DEF","MID","FWD")):
        metadata.append({"id":100+i,"web_name":f"Buy {pos}","team":6,"element_type":i+1,"now_cost":50})
        for gw in (9,10):
            rows.append(dict(playerId=100+i,name=f"Buy {pos}",club="NEW",position=pos,price=5.,gameweek=gw,fixture="OPP (A)",projectedPoints=30.,minutesFactor=1.))
    path=tmp_path/"projections.json"
    payload=dict(schemaVersion=1,modelUpdatedAt="2026-10-26T17:00:00+00:00",exportedAt="2026-10-26T17:00:01+00:00",projections=rows)
    path.write_text(json.dumps(payload),encoding="utf-8")
    return path,payload,metadata

@pytest.fixture
def setup_api(fixture_data):
    path,payload,metadata=fixture_data
    state={"chips":[],"historyStatus":200,"calls":[],"bank":4}
    def handler(request):
        key=request.url.path
        state["calls"].append(key)
        if key.endswith("/bootstrap-static/"):
            return httpx.Response(200,json={"elements":metadata,"teams":[{"id":i+1,"short_name":f"C{i}"} for i in range(5)]+[{"id":6,"short_name":"NEW"}]})
        if key.endswith("/history/"):
            return httpx.Response(state["historyStatus"],json={"chips":state["chips"]})
        if "/event/" in key:
            gw=int(key.split("/event/")[1].split("/")[0])
            ids=range(101,116) if any(c["event"]==gw for c in state["chips"]) else range(1,16)
            return httpx.Response(200,json={"picks":[{"element":i} for i in ids],"entry_history":{"bank":state["bank"]}})
        return httpx.Response(404)
    settings=Settings(path,("http://localhost:5173","http://127.0.0.1:5173"),"https://fpl.test/api/")
    transport=FplClient(settings,httpx.Client(base_url=settings.fpl_base_url,transport=httpx.MockTransport(handler)))
    application=create_app(settings,transport)
    with TestClient(application,raise_server_exceptions=False) as client:yield client,application,state

