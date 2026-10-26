"""Verify extracted rule bodies against the recorded AST hashes and optional original files."""
import argparse,ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fingerprint(node):
    return hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
def verify(model_directory=None):
    manifest=json.loads((ROOT/"app/vendor/provenance.json").read_text())
    count=0
    def constants(text):
        return {target.id:ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) for target in n.targets if isinstance(target,ast.Name) and isinstance(n.value,(ast.Constant,ast.List))}
    for filename,entry in manifest.items():
        nodes={n.name:n for n in ast.parse((ROOT/"app/vendor"/filename).read_text(encoding="utf-8-sig")).body if isinstance(n,ast.FunctionDef)}
        for key,value in entry.get("constants",{}).items():
            assert constants((ROOT/"app/vendor"/filename).read_text(encoding="utf-8-sig"))[key]==value
        originals=None
        if model_directory:
            original=Path(model_directory)/entry["source"]
            if hashlib.sha256(original.read_bytes()).hexdigest()!=entry["sourceSha256"]:raise AssertionError("Original source changed: "+entry["source"])
            for key,value in entry.get("constants",{}).items():
                assert constants(original.read_text(encoding="utf-8-sig"))[key]==value
            originals={n.name:n for n in ast.parse(original.read_text(encoding="utf-8-sig")).body if isinstance(n,ast.FunctionDef)}
        for name,expected in entry["functions"].items():
            assert fingerprint(nodes[name])==expected,filename+"/"+name
            if originals is not None:assert fingerprint(originals[name])==expected,entry["source"]+"/"+name
            count+=1
    return count
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--model-dir")
    args=parser.parse_args()
    print(f"Verified {verify(args.model_dir)} unchanged rule functions.")

