from pathlib import Path
import json
import time

CACHE_DIR = Path("backend/runtime/source_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(source: str, market: str) -> Path:
    name = f"{source}_{market}.json"
    return CACHE_DIR / name


def load_cache(source: str, market: str, max_age_seconds: int = 300):
    path = cache_key(source, market)

    if not path.exists():
        return None

    data = json.loads(path.read_text())

    age = time.time() - data["timestamp"]

    if age > max_age_seconds:
        return None

    return data["payload"]


def save_cache(source: str, market: str, payload: dict):
    path = cache_key(source, market)

    path.write_text(json.dumps({
        "timestamp": time.time(),
        "payload": payload
    }))
