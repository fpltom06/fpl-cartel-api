"""Load isolated copies of the extracted rule modules and inject only the FPL transport."""
import importlib.util
from pathlib import Path
VENDOR=Path(__file__).resolve().parents[1]/"vendor"

def load_module(filename):
    spec=importlib.util.spec_from_file_location("fpl_extracted_"+filename.removesuffix(".py"),VENDOR/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_rules(fpl):
    core=load_module("streamlit_rules.py")
    core.fetch_entry_history=fpl.history
    core.fetch_entry_picks=fpl.picks
    transfers=load_module("transfer_rules.py")
    transfers.model=core
    return core,transfers

