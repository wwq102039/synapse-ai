import json
import sqlite3
from pathlib import Path
from . import register

DB_PATH = Path(__file__).parent.parent / "synapse_memory.db"


def _ensure_db():
    if not DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()


def _is_readonly_sql(sql: str) -> bool:
    """只允许 SELECT 语句，阻止任何修改操作"""
    stripped = sql.strip()
    upper = stripped.upper()
    dangerous = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
                 "ALTER", "TRUNCATE", "REPLACE", "ATTACH", "DETACH",
                 "PRAGMA", "REINDEX", "VACUUM", "GRANT", "REVOKE")
    for keyword in dangerous:
        if upper.startswith(keyword) or f" {keyword} " in upper or f"\n{keyword}" in upper:
            return False
    if not upper.startswith("SELECT"):
        return False
    return True


@register(
    "db_query",
    "查询本地 SQLite 数据库（只读）。用于检索记忆、任务或任何结构化数据。",
    {"sql": {"type": "string", "description": "SELECT 查询语句（只读，INSERT/UPDATE/DELETE 请用 db_memory）"}}
)
def db_query(sql: str) -> str:
    if not _is_readonly_sql(sql):
        return json.dumps({
            "error": "只允许 SELECT 查询。修改数据请使用 db_memory 工具。"
        })

    try:
        _ensure_db()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return json.dumps({"rows": rows, "count": len(rows)}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@register(
    "db_memory",
    "保存或检索键值记忆。AI 可以跨对话记住信息。",
    {"action": {"type": "string", "description": "操作：'save'（保存）、'get'（获取）、'list'（列出全部）、'delete'（删除）"},
     "key": {"type": "string", "description": "记忆的键名（save/get/delete 需要）"},
     "value": {"type": "string", "description": "要存储的值（save 需要）"}}
)
def db_memory(action: str, key: str = "", value: str = "") -> str:
    try:
        _ensure_db()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        if action == "save":
            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()
            conn.close()
            return json.dumps({"success": True, "key": key})

        elif action == "get":
            row = conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
            conn.close()
            if row:
                return json.dumps({"key": key, "value": dict(row)["value"]}, ensure_ascii=False)
            return json.dumps({"error": f"Memory '{key}' not found"})

        elif action == "list":
            rows = conn.execute("SELECT key, value FROM memories ORDER BY created_at DESC").fetchall()
            conn.close()
            return json.dumps({"memories": [dict(r) for r in rows]}, ensure_ascii=False)

        elif action == "delete":
            conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return json.dumps({"success": True, "deleted": key})

        conn.close()
        return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
