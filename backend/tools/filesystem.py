import os
import json
from pathlib import Path
from . import register

# 安全基准目录 — 所有文件操作必须在 BASE_DIR 或其子目录内
BASE_DIR = Path(os.path.expanduser("~")) / "synapse_ai_workspace"


def _resolve_safe_path(path: str) -> Path:
    """解析路径并确保它在 BASE_DIR 内（防止路径遍历）"""
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR / p
    # resolve 规范化路径，消除 .. 等符号链接
    resolved = p.resolve()
    base_resolved = BASE_DIR.resolve()
    # 确保 resolved 在 base 之内
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise PermissionError(f"禁止访问沙箱外路径: {path}")
    return resolved


def _ensure_base_dir():
    BASE_DIR.mkdir(parents=True, exist_ok=True)


@register(
    "file_read",
    "读取文件内容。用于查看文件、读取配置或检查文本文件。",
    {"path": {"type": "string", "description": "要读取的文件路径（必须在工作区内）"}}
)
def file_read(path: str) -> str:
    try:
        _ensure_base_dir()
        p = _resolve_safe_path(path)
        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})
        content = p.read_text(encoding="utf-8")
        if len(content) > 8000:
            content = content[:8000] + "\n... [truncated, file too large]"
        return json.dumps({"path": str(p), "content": content, "size": p.stat().st_size}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@register(
    "file_list",
    "列出目录中的文件和文件夹。用于浏览文件系统。",
    {"path": {"type": "string", "description": "要列出的目录路径（必须在工作区内）"}}
)
def file_list(path: str) -> str:
    try:
        _ensure_base_dir()
        p = _resolve_safe_path(path)
        if not p.exists() or not p.is_dir():
            return json.dumps({"error": f"Directory not found: {path}"})
        items = []
        for item in sorted(p.iterdir()):
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        return json.dumps({"path": str(p), "items": items[:100]}, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@register(
    "file_write",
    "写入内容到文件。用于创建或覆盖文件。",
    {"path": {"type": "string", "description": "要写入的文件路径（必须在工作区内）"},
     "content": {"type": "string", "description": "要写入文件的内容"}}
)
def file_write(path: str, content: str) -> str:
    try:
        _ensure_base_dir()
        p = _resolve_safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(p), "size": len(content)})
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@register(
    "file_search",
    "按文件名模式搜索文件。类似按文件名 grep。",
    {"directory": {"type": "string", "description": "搜索的根目录（必须在工作区内）"},
     "pattern": {"type": "string", "description": "Glob 匹配模式，如 *.py 或 **/*.json"}}
)
def file_search(directory: str, pattern: str) -> str:
    try:
        _ensure_base_dir()
        p = _resolve_safe_path(directory)
        results = list(p.rglob(pattern))[:50]
        return json.dumps({
            "directory": str(p),
            "pattern": pattern,
            "matches": [{"path": str(r), "type": "dir" if r.is_dir() else "file"} for r in results]
        }, ensure_ascii=False)
    except PermissionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})
