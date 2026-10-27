import json
import re
import hashlib
from collections import Counter
from . import register


@register(
    "text_process",
    "文本处理：统计字数、提取邮箱/网址/数字、词频分析、计算哈希、正则搜索。用于分析和处理文本。",
    {"action": {"type": "string", "description": "操作类型：'stats'（统计）、'extract_emails'（提取邮箱）、'extract_urls'（提取网址）、'extract_numbers'（提取数字）、'word_freq'（词频）、'hash'（哈希）、'regex_find'（正则查找）"},
     "text": {"type": "string", "description": "要处理的文本"},
     "pattern": {"type": "string", "description": "正则表达式（regex_find 操作需要）"}}
)
def text_process(action: str, text: str, pattern: str = "") -> str:
    try:
        if action == "stats":
            words = text.split()
            return json.dumps({
                "char_count": len(text),
                "word_count": len(words),
                "line_count": text.count("\n") + 1,
                "unique_words": len(set(w.lower() for w in words)),
                "avg_word_length": round(sum(len(w) for w in words) / max(len(words), 1), 1),
            })

        elif action == "extract_emails":
            found = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
            return json.dumps({"emails": list(set(found))})

        elif action == "extract_urls":
            found = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
            return json.dumps({"urls": list(set(found))})

        elif action == "extract_numbers":
            found = re.findall(r'-?\d+\.?\d*', text)
            nums = [float(n) if "." in n else int(n) for n in found]
            return json.dumps({"numbers": nums, "sum": sum(nums) if nums else 0})

        elif action == "word_freq":
            words = re.findall(r'\b\w+\b', text.lower())
            freq = Counter(words).most_common(20)
            return json.dumps({"word_frequencies": [{"word": w, "count": c} for w, c in freq]})

        elif action == "hash":
            return json.dumps({
                "md5": hashlib.md5(text.encode()).hexdigest(),
                "sha1": hashlib.sha1(text.encode()).hexdigest(),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            })

        elif action == "regex_find":
            matches = re.findall(pattern, text)
            return json.dumps({"pattern": pattern, "matches": matches})

        return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@register(
    "text_transform",
    "文本转换：大小写转换、base64编解码、反转、排序、去重、替换、裁剪、换行。",
    {"action": {"type": "string", "description": "操作类型：'upper'（大写）、'lower'（小写）、'title'（标题）、'reverse'（反转）、'sort_lines'（排序）、'deduplicate_lines'（去重）、'replace'（替换）、'base64_encode'（base64编码）、'base64_decode'（base64解码）、'trim'（裁剪）、'word_wrap'（换行）"},
     "text": {"type": "string", "description": "要转换的文本"},
     "arg": {"type": "string", "description": "额外参数（如 replace 用 old|new，word_wrap 用宽度）"}}
)
def text_transform(action: str, text: str, arg: str = "") -> str:
    import base64
    import textwrap
    try:
        if action == "upper":
            return json.dumps({"result": text.upper()})
        elif action == "lower":
            return json.dumps({"result": text.lower()})
        elif action == "title":
            return json.dumps({"result": text.title()})
        elif action == "reverse":
            return json.dumps({"result": text[::-1]})
        elif action == "sort_lines":
            lines = text.split("\n")
            return json.dumps({"result": "\n".join(sorted(lines))})
        elif action == "deduplicate_lines":
            seen = set()
            lines = text.split("\n")
            unique = [l for l in lines if not (l in seen or seen.add(l))]
            return json.dumps({"result": "\n".join(unique)})
        elif action == "replace":
            parts = arg.split("|", 1) if arg else ["", ""]
            old, new = parts[0], parts[1] if len(parts) > 1 else ""
            return json.dumps({"result": text.replace(old, new)})
        elif action == "base64_encode":
            return json.dumps({"result": base64.b64encode(text.encode()).decode()})
        elif action == "base64_decode":
            return json.dumps({"result": base64.b64decode(text.encode()).decode()})
        elif action == "trim":
            return json.dumps({"result": text.strip()})
        elif action == "word_wrap":
            width = int(arg) if arg.isdigit() else 80
            return json.dumps({"result": textwrap.fill(text, width=width)})
        return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
