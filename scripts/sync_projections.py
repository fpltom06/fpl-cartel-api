"""Copy only the clean projection JSON; never invoke the model or read Excel."""
import argparse,json,os,tempfile
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source",type=Path,required=True)
parser.add_argument("--destination",type=Path,default=Path(__file__).resolve().parents[1]/"data/projections.json")
args=parser.parse_args()
if args.source.suffix.lower()!=".json" or args.destination.suffix.lower()!=".json":
    parser.error("Only JSON projection files are supported.")
data=args.source.read_bytes()
payload=json.loads(data)
if payload.get("schemaVersion")!=1 or not isinstance(payload.get("projections"),list):parser.error("Invalid projection export.")
args.destination.parent.mkdir(parents=True,exist_ok=True)
with tempfile.NamedTemporaryFile(dir=args.destination.parent,suffix=".tmp",delete=False) as handle:
    temporary=Path(handle.name);handle.write(data)
try:os.replace(temporary,args.destination)
finally:temporary.unlink(missing_ok=True)
print("Projection snapshot copied. API file-version cache reloads it on the next request.")

