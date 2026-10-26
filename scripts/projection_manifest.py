"""Write a byte-level version manifest without recalculating projections."""
import hashlib, json, sys
from pathlib import Path
p=Path(sys.argv[1]); raw=p.read_bytes(); data=json.loads(raw)
metadata={"sha256":hashlib.sha256(raw).hexdigest(),"modelUpdatedAt":data["modelUpdatedAt"],"exportedAt":data["exportedAt"],"rowCount":len(data["projections"]),"players":len({r["playerId"] for r in data["projections"]}),"gameweeks":sorted({r["gameweek"] for r in data["projections"]})}
Path("DATA_VERSION.json").write_text(json.dumps(metadata,indent=2)+"\n")
print(json.dumps(metadata))
