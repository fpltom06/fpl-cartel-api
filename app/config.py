from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    projections_path: Path
    allowed_origins: tuple[str, ...]
    fpl_base_url: str
    metadata_ttl: int = 300
    manager_ttl: int = 60
    timeout: float = 10
    max_request_bytes: int = 16384
    optimizer_concurrency: int = 1

def get_settings():
    load_dotenv(ROOT / ".env", override=False)
    raw = Path(os.getenv("PROJECTIONS_PATH", "data/projections.json"))
    origins = tuple(part.strip().rstrip("/") for part in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if part.strip())
    if any("*" in origin or urlparse(origin).scheme not in {"http","https"} or not urlparse(origin).netloc or urlparse(origin).path for origin in origins):
        raise ValueError("ALLOWED_ORIGINS must contain exact HTTP(S) origins, without wildcard or paths.")
    base = os.getenv("FPL_BASE_URL", "https://fantasy.premierleague.com/api/").rstrip("/") + "/"
    if urlparse(base).scheme not in {"http","https"} or not urlparse(base).netloc:
        raise ValueError("FPL_BASE_URL must be an HTTP(S) API base.")
    return Settings(projections_path=(ROOT/raw).resolve() if not raw.is_absolute() else raw.resolve(),
        allowed_origins=origins, fpl_base_url=base,
        metadata_ttl=max(1,int(os.getenv("FPL_METADATA_TTL","300"))),
        manager_ttl=max(1,int(os.getenv("FPL_MANAGER_TTL","60"))),
        timeout=max(1,float(os.getenv("FPL_TIMEOUT_SECONDS","10"))),
        max_request_bytes=max(256,min(65536,int(os.getenv("MAX_REQUEST_BYTES","16384")))),
        optimizer_concurrency=max(1,min(4,int(os.getenv("MAX_OPTIMIZER_CONCURRENCY","1")))))

