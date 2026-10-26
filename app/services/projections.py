"""Read and cache precomputed web output. No Excel or model calculation imports."""
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import math
from threading import RLock
import pandas as pd
from app.errors import ApiError

@dataclass
class Snapshot:
    model_updated_at:str
    gameweeks:list[int]
    frame:pd.DataFrame
    lookup:dict
    players:dict

class ProjectionStore:
    def __init__(self,path):
        self.path=path;self.lock=RLock();self.signature=None;self.snapshot=None;self.parse_count=0

    def get(self):
        with self.lock:
            try:
                stat=self.path.stat();signature=(stat.st_mtime_ns,stat.st_size)
                if self.snapshot is not None and signature==self.signature:return self.snapshot
                raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
                if raw.get("schemaVersion")!=1 or not isinstance(raw.get("projections"),list):
                    raise ValueError("Invalid export schema")
                version=raw["modelUpdatedAt"];datetime.fromisoformat(version.replace("Z","+00:00"))
                players={};lookup={}
                for row in raw["projections"]:
                    pid,gw=row["playerId"],row["gameweek"]
                    if type(pid) is not int or pid<=0 or type(gw) is not int or not 1<=gw<=38 or (pid,gw) in lookup:
                        raise ValueError("Invalid/duplicate identity")
                    if row["position"] not in {"GK","DEF","MID","FWD"} or any(not isinstance(row[k],str) or not row[k].strip() for k in ("name","club","fixture")):
                        raise ValueError("Invalid display fields")
                    if any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) for k in ("price","projectedPoints","minutesFactor")) or row["price"]<=0 or row["minutesFactor"]<0:
                        raise ValueError("Invalid numeric fields")
                    identity={"Player ID":pid,"Name":row["name"],"Club":row["club"],"Position":row["position"],"Price":row["price"]}
                    entry=players.setdefault(pid,identity.copy())
                    if any(entry[key]!=value for key,value in identity.items()):raise ValueError("Inconsistent player metadata")
                    entry[f"GW{gw}"]=float(row["projectedPoints"])
                    lookup[(pid,gw)]=row
                weeks=sorted({gw for pid,gw in lookup})
                frame=pd.DataFrame(players.values())
                columns=[f"GW{gw}" for gw in weeks]
                if not frame.empty and frame[columns].isna().any().any():raise ValueError("Incomplete player gameweeks")
                if not frame.empty:frame["Predicted Total"]=frame[columns].sum(axis=1)
                current=self.path.stat()
                if (current.st_mtime_ns,current.st_size)!=signature:raise ValueError("Export changed during read")
                self.snapshot=Snapshot(version,weeks,frame,lookup,players);self.signature=signature;self.parse_count+=1
                return self.snapshot
            except Exception:
                logging.exception("Projection snapshot could not be loaded")
                raise ApiError(503,"projections_unavailable","Projection data is unavailable. Refresh the precomputed export.") from None

