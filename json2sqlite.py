import sqlite_utils, json
import hashlib
import re
from datetime import datetime, timezone
import sys

dbpath = sys.argv[1]

db = sqlite_utils.Database(dbpath)


def format_datetime(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(round(ts), tz=timezone.utc).strftime("%d-%m-%Y %H:%M:%S GMT")



def safe_table_name(title: str, chat_id: str, timestamp=None) -> str:
    base = re.sub(r"\W+", "_", title.strip().lower())[:50] or "chat"
    if timestamp is not None:
        prefix = str(round(timestamp))
    else:
        prefix = hashlib.sha1(chat_id.encode()).hexdigest()[:8]
    if base.startswith("sqlite_"):
        base = f"t_{base}"
    return f"chat_{prefix}_{base}"


for chat in db["chats"].rows:
    chat_id = chat["id"]
    mapping_str = chat.get("mapping")
    if not mapping_str:
        continue

    try:
        mapping = json.loads(mapping_str)
    except Exception:
        continue

    # Try to use the smallest create_time among message nodes
    create_times = [
        (node.get("message") or {}).get("create_time")
        for node in mapping.values()
        if (node.get("message") or {}).get("create_time")
    ]
    ts = min(create_times) if create_times else None

    table_name = safe_table_name(chat.get("title") or "chat", chat_id, ts)

    if table_name not in db.table_names():
        db[table_name].create({
            "node_id": str,
            "role": str,
            "content": str,
            "create_time": str,  # now stored as formatted text
            "update_time": float,
            "weight": float,
            "status": str,
            "parent": str,
            "children": str,
            "model_slug": str,
            "default_model_slug": str,
            "finish_type": str,
            "citations": str,
            "content_references": str
        }, pk="node_id")

    for node_id, node in mapping.items():
        msg = node.get("message") or {}
        meta = msg.get("metadata") or {}
        content_parts = ((msg.get("content") or {}).get("parts") or [])
        content = content_parts[0] if content_parts else None
        finish = meta.get("finish_details") or {}

        db[table_name].insert({
            "node_id": node_id,
            "role": ((msg.get("author") or {}).get("role")),
            "content": content,
            "create_time": format_datetime(msg.get("create_time")),
            "update_time": msg.get("update_time"),
            "weight": msg.get("weight"),
            "status": msg.get("status"),
            "parent": node.get("parent"),
            "children": json.dumps(node.get("children")) if node.get("children") else None,
            "model_slug": meta.get("model_slug"),
            "default_model_slug": meta.get("default_model_slug"),
            "finish_type": finish.get("type"),
            "citations": json.dumps(meta.get("citations")) if meta.get("citations") else None,
            "content_references": json.dumps(meta.get("content_references")) if meta.get("content_references") else None
        }, alter=True)
