from collections import Counter
from contextlib import contextmanager
from datetime import datetime,timezone
from threading import BoundedSemaphore
import pandas as pd
from app.errors import ApiError
from app.services.rules import load_rules

SEARCH_NOTE="Existing Python search: all legal single buys; 2–3 moves use 10 beam states, top 24 affordable candidates and 3 buys per seller. Global optimality is not guaranteed."

class OptimizerService:
    def __init__(self,settings,store,fpl):
        self.store=store;self.fpl=fpl;self.core,self.transfers=load_rules(fpl)
        self.capacity=BoundedSemaphore(settings.optimizer_concurrency)

    @contextmanager
    def limited(self):
        if not self.capacity.acquire(blocking=False):
            raise ApiError(503,"optimizer_busy","The optimizer is busy. Please retry shortly.")
        try:yield
        finally:self.capacity.release()

    def snapshot(self,version=None):
        snapshot=self.store.get()
        if not snapshot.gameweeks:raise ApiError(503,"no_future_projections","No future projection gameweeks are available.")
        if version and version!=snapshot.model_updated_at:
            raise ApiError(409,"projection_version_mismatch","Projection data changed. Refresh website data and retry.")
        return snapshot

    def check_weeks(self,snapshot,weeks):
        if not set(weeks)<=set(snapshot.gameweeks):
            raise ApiError(422,"invalid_gameweeks","Requested gameweeks are not available in the projection export.")

    def player(self,row):
        return {"playerId":int(row["Player ID"]),"name":str(row["Name"]),"club":str(row["Club"]),
            "position":str(row["Position"]),"price":float(row["Price"])}

    def team(self,team_id,version=None,snapshot=None):
        snapshot=snapshot or self.snapshot(version)
        info=self.core.get_permanent_squad_before_gw(team_id,snapshot.gameweeks[0])
        ids=info["squad_player_ids"]
        if len(ids)!=15 or info["source_gameweek"] in info["ignored_free_hit_gameweeks"]:
            raise ApiError(503,"invalid_permanent_squad","A verified 15-player permanent squad is unavailable.")
        metadata=self.fpl.bootstrap()
        by_id={p["id"]:p for p in metadata["elements"]}
        clubs={t["id"]:t["short_name"] for t in metadata["teams"]}
        positions={1:"GK",2:"DEF",3:"MID",4:"FWD"}
        missing=[];players=[]
        for pid in sorted(ids):
            row=snapshot.players.get(pid)
            if row:players.append(self.player(row))
            else:
                p=by_id.get(pid,{})
                fallback={"playerId":pid,"name":p.get("web_name","Unknown player"),"club":clubs.get(p.get("team"),"Unknown club"),
                    "position":positions.get(p.get("element_type"),"Unknown position"),"price":float(p.get("now_cost",0))/10}
                players.append(fallback)
                missing.append({k:v for k,v in fallback.items() if k!="price"})
        return {"teamId":team_id,"bank":float(info["bank"]),"squadSourceGw":int(info["source_gameweek"]),
            "freeHitDetected":bool(info["ignored_free_hit_gameweeks"]),"players":players,
            "modelUpdatedAt":snapshot.model_updated_at,"loadedAt":datetime.now(timezone.utc).isoformat(),
            "gameweeks":snapshot.gameweeks,"sourceGameweek":int(info["source_gameweek"]),
            "planningGameweek":snapshot.gameweeks[0],"ignoredFreeHitGameweeks":info["ignored_free_hit_gameweeks"],
            "sourceNote":info.get("squad_source_note",""),
            "diagnostics":{"squadCount":15,"matchedCount":15-len(missing),"missingPlayers":missing,"squadPlayerIds":sorted(ids)},
            "transfers":0,"weeks":[],"overall":None}

    def squad(self,snapshot,team):
        if team["diagnostics"]["matchedCount"]!=15:
            raise ApiError(503,"missing_projections","All 15 squad players must match projection IDs.",team["diagnostics"])
        squad=snapshot.frame[snapshot.frame["Player ID"].isin(team["diagnostics"]["squadPlayerIds"])].copy()
        if squad["Position"].value_counts().to_dict()!={"GK":2,"DEF":5,"MID":5,"FWD":3}:
            raise ApiError(503,"invalid_projection_positions","Projection positions do not form a legal FPL squad.")
        return squad

    def pitch_player(self,row,gw,snapshot,captain=None,vice=None):
        pid=int(row["Player ID"]);projection=snapshot.lookup[(pid,gw)]
        return self.player(row)|{"fixture":projection["fixture"],"projectedPoints":float(projection["projectedPoints"]),
            "isCaptain":pid==captain,"isViceCaptain":pid==vice}

    def sheets(self,snapshot,team,squad,weeks):
        columns=[f"GW{g}" for g in weeks]
        raw=self.core.calculate_multi_gw_team_sheets(squad,columns)
        if len(raw)!=len(weeks):raise ApiError(500,"optimizer_failed","The existing optimizer could not produce every legal XI.")
        output=[]
        for gw,sheet in zip(weeks,raw):
            xi=sheet["starting_xi"];captain=int(sheet["captain"]["Player ID"])
            ranked=xi.sort_values(f"GW{gw}",ascending=False,kind="stable")
            vice=int(ranked[ranked["Player ID"]!=captain].iloc[0]["Player ID"])
            bench=squad[~squad["Player ID"].isin(xi["Player ID"])].copy()
            bench["keeperFirst"]=bench["Position"].map(lambda p:0 if p=="GK" else 1)
            bench=bench.sort_values(["keeperFirst",f"GW{gw}"],ascending=[True,False],kind="stable")
            output.append({"gameweek":gw,"formation":sheet["formation"],
                "startingXI":[self.pitch_player(p,gw,snapshot,captain,vice) for _,p in xi.iterrows()],
                "bench":[self.pitch_player(p,gw,snapshot) for _,p in bench.iterrows()],
                "captainPlayerId":captain,"viceCaptainPlayerId":vice,"xiProjection":float(sheet["starting_xi_base"]),
                "captainBonus":float(sheet["captain_bonus"]),"projectedTotal":float(sheet["projected_total"])})
        captains=Counter(w["captainPlayerId"] for w in output)
        most=max(captains,key=captains.get);best=max(output,key=lambda w:w["projectedTotal"])
        total=sum(w["projectedTotal"] for w in output)
        overall={"total":total,"average":total/len(weeks),"mostCaptained":{"playerId":most,
            "name":str(squad.loc[squad["Player ID"]==most,"Name"].iloc[0]),"count":captains[most]},
            "highestGameweek":{"gameweek":best["gameweek"],"projectedTotal":best["projectedTotal"]}}
        return {"team":team,"gameweeks":output,"overall":overall}

    def team_sheet(self,request):
        with self.limited():
            snapshot=self.snapshot(request.modelUpdatedAt);self.check_weeks(snapshot,request.gameweeks)
            team=self.team(request.teamId,snapshot=snapshot)
            return self.sheets(snapshot,team,self.squad(snapshot,team),request.gameweeks)

    def prepare_transfers(self,request):
        snapshot=self.snapshot(request.modelUpdatedAt);self.check_weeks(snapshot,request.gameweeks)
        if not set(request.excludedPlayerIds)<=set(snapshot.players):
            raise ApiError(422,"invalid_player_ids","Excluded Player IDs must exist in the projection export.")
        team=self.team(request.teamId,snapshot=snapshot);squad=self.squad(snapshot,team)
        frame=snapshot.frame.copy();columns=[f"GW{g}" for g in request.gameweeks]
        frame["Transfer Search Score"]=frame[columns].sum(axis=1)
        bank=team["bank"] if request.bankOverride is None else request.bankOverride
        return snapshot,team,squad,frame,columns,bank

    def optimize_transfers(self,request):
        with self.limited():
            snapshot,team,squad,frame,columns,bank=self.prepare_transfers(request)
            original=self.sheets(snapshot,team,squad,request.gameweeks)
            options=self.transfers.search_options(frame,squad,bank,columns,
                "Next GW" if len(columns)==1 else "Next 5 GWs",request.numberOfTransfers,request.transferHit,set(request.excludedPlayerIds))
            ids=set(team["diagnostics"]["squadPlayerIds"])
            for option in options:
                option["updatedSquadIds"]=sorted(ids-{m["out"]["playerId"] for m in option["moves"]}|{m["in"]["playerId"] for m in option["moves"]})
            return {"originalSquad":team,"moneyInBank":team["bank"],"bankUsed":bank,"gameweeks":request.gameweeks,
                "recommendations":options,"originalTeamSheet":original,"searchNote":SEARCH_NOTE}

    def preview(self,request):
        with self.limited():
            snapshot,team,squad,frame,columns,bank=self.prepare_transfers(request)
            if len(request.moves)>request.numberOfTransfers:raise ApiError(422,"invalid_moves","Too many transfer moves.")
            original=self.sheets(snapshot,team,squad,request.gameweeks)
            original_ids=set(team["diagnostics"]["squadPlayerIds"]);sold=set();bought=set();banned=set(request.excludedPlayerIds)
            for move in request.moves:
                out_id,in_id=move.outId,move.inId
                if out_id not in original_ids or out_id in sold or in_id in original_ids|sold|bought|banned:
                    raise ApiError(422,"invalid_moves","Owned, duplicate or circular transfer rejected.")
                outgoing=squad[squad["Player ID"]==out_id]
                valid=self.transfers.valid_buys(frame,squad,outgoing.iloc[0],bank,original_ids|sold|bought|banned)
                incoming=valid[valid["Player ID"]==in_id]
                if incoming.empty:raise ApiError(422,"invalid_moves","Transfer violates position, club or budget rules.")
                bank+=float(outgoing.iloc[0]["Price"])-float(incoming.iloc[0]["Price"])
                squad=pd.concat([squad[squad["Player ID"]!=out_id],incoming],ignore_index=True)
                sold.add(out_id);bought.add(in_id)
            updated_team=team|{"bank":max(0.0,bank),"players":[self.player(p) for _,p in squad.iterrows()],"diagnostics":team["diagnostics"]|{"squadPlayerIds":sorted(squad["Player ID"].astype(int).tolist())}}
            updated=self.sheets(snapshot,updated_team,squad,request.gameweeks)
            before=original["overall"]["total"];after=updated["overall"]["total"]
            return {"updatedTeamSheet":updated,"originalTotal":before,"updatedTotal":after,"grossTeamGain":after-before,
                "netTeamGain":after-before-(request.transferHit if request.moves else 0)}


