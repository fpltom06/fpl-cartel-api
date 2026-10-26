"""Extracted unchanged functions. See provenance.json; do not edit optimizer rules here."""
from __future__ import annotations
from itertools import combinations
import pandas as pd
POSITION_ORDER = ["GK","DEF","MID","FWD"]
BEAM_WIDTH = 10
BUYS_PER_SELLER = 3

def player(row):
    return {"playerId":int(row["Player ID"]),"name":str(row["Name"]),"club":str(row["Club"]),"position":str(row["Position"]),"price":float(row["Price"])}

def valid_buys(frame,current,out,bank,excluded,shortlist=False):
    # Guard an empty input pool: pandas 3 can drop columns inside the legacy apply filter.
    ids=set(current["Player ID"].astype(int))|excluded
    pool=frame[(frame["Position"]==out["Position"]) & (~frame["Player ID"].isin(ids)) & (frame["Price"]<=float(out["Price"])+bank)]
    if pool.empty:return frame.iloc[0:0].copy()
    if shortlist:pool=pool.sort_values("Transfer Search Score" if "Transfer Search Score" in pool else "Predicted Total",ascending=False).head(24)
    return model.get_valid_buy_options(pool,current,out,bank,"Player ID",excluded)

def search_options(frame,squad,bank,columns,mode,count,hit,banned):
    original=set(squad["Player ID"].astype(int))
    # Existing affordability, club limits and positive horizon upgrade rules at every step.
    states=[(squad,bank,[],0.0)]
    packages={():states[0]}
    for _ in range(count):
        expanded={}
        for current,cash,moves,gain in states:
            sold={a for a,b in moves};bought={b for a,b in moves}
            for _,out in current[~current["Player ID"].isin(sold|bought)].iterrows():
                candidates=valid_buys(frame,current,out,cash,original|bought|sold|banned,shortlist=count>1)
                if candidates.empty:continue
                scored=model.add_transfer_upgrade_scores(candidates,out,columns,mode)
                scored=scored[scored["Upgrade Score"]>1e-9]
                # One transfer is exhaustive; subsequent beam steps use per-seller shortlists.
                if count>1:scored=scored.head(BUYS_PER_SELLER)
                for _,incoming in scored.iterrows():
                    pair=(int(out["Player ID"]),int(incoming["Player ID"]))
                    batch=moves+[pair];key=tuple(sorted(batch))
                    if key in expanded:continue
                    updated=current[current["Player ID"]!=pair[0]]
                    updated=pd.concat([updated,incoming.to_frame().T],ignore_index=True)
                    new_bank=cash+float(out["Price"])-float(incoming["Price"])
                    if new_bank < -1e-8:continue
                    expanded[key]=(updated,max(0.0,new_bank),batch,gain+float(incoming["Upgrade Score"]))
        packages.update(expanded)
        states=sorted(expanded.values(),key=lambda state:(-state[3],len(state[2]),tuple(sorted(state[2]))))[:BEAM_WIDTH]
        if not states:break
    ordered=sorted(packages.values(),key=lambda state:(-(state[3]-(hit if state[2] else 0)),len(state[2]),tuple(sorted(state[2]))))
    by_id=frame.set_index("Player ID",drop=False)
    result=[]
    for updated,cash,moves,gain in ordered[:10]:
        outs=[by_id.loc[a] for a,b in moves];ins=[by_id.loc[b] for a,b in moves]
        outgoing=sum(model.get_projection_score(p,columns,mode) for p in outs)
        incoming=sum(model.get_projection_score(p,columns,mode) for p in ins)
        result.append({"id":"roll" if not moves else "_".join(f"{a}-{b}" for a,b in sorted(moves)),
            "moves":[{"out":player(by_id.loc[a]),"in":player(by_id.loc[b])} for a,b in moves],
            "outgoingProjection":outgoing,"incomingProjection":incoming,
            "grossGain":incoming-outgoing,"transferCost":hit if moves else 0,
            "netGain":incoming-outgoing-(hit if moves else 0),
            "cost":sum(float(p["Price"]) for p in ins)-sum(float(p["Price"]) for p in outs),
            "bankAfter":cash,
            "breakdown":[{"gameweek":int(c[2:]),"out":sum(float(p[c]) for p in outs),"in":sum(float(p[c]) for p in ins),"gain":sum(float(p[c]) for p in ins)-sum(float(p[c]) for p in outs)} for c in columns]})
    # Keep roll available even if ten positive packages outrank it.
    if not any(r["id"]=="roll" for r in result):
        result=result[:9]+[{"id":"roll","moves":[],"outgoingProjection":0,"incomingProjection":0,"grossGain":0,"transferCost":0,"netGain":0,"cost":0,"bankAfter":bank,"breakdown":[]}]
    return result
