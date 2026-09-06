import json, uuid, datetime

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]

def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)

def jload(s: str):
    return json.loads(s)
