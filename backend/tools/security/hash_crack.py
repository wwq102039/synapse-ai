"""哈希分析工具 — 哈希类型识别、密码强度审计"""
import json
import re
import math
import hashlib
import urllib.request
import ssl
from .. import register

# 哈希类型特征
HASH_PATTERNS = [
    ("MD5", r"^[a-f0-9]{32}$"),
    ("SHA-1", r"^[a-f0-9]{40}$"),
    ("SHA-256", r"^[a-f0-9]{64}$"),
    ("SHA-384", r"^[a-f0-9]{96}$"),
    ("SHA-512", r"^[a-f0-9]{128}$"),
    ("NTLM", r"^[A-F0-9]{32}$"),
    ("MySQL3", r"^[a-f0-9]{16}$"),
    ("MySQL4", r"^[a-f0-9]{16}$"),
    ("MySQL5", r"^\*[A-F0-9]{40}$"),
    ("MD5-Crypt", r"^\$1\$[./A-Za-z0-9]{1,8}\$[./A-Za-z0-9]{22}$"),
    ("SHA-256-Crypt", r"^\$5\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{43}$"),
    ("SHA-512-Crypt", r"^\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}$"),
    ("bcrypt", r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$"),
    ("bcrypt", r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{21}\.{0,2}[./A-Za-z0-9]{31}$"),
    ("Argon2", r"^\$argon2[id]\$"),
    ("SHA-1(Base64)", r"^[A-Za-z0-9+/]{27}=$"),
    ("SHA-256(Base64)", r"^[A-Za-z0-9+/]{43}=$"),
    ("SHA-512(Base64)", r"^[A-Za-z0-9+/]{86}==$"),
    ("CRC32", r"^[a-f0-9]{8}$"),
    ("RIPEMD-160", r"^[a-f0-9]{40}$"),
    ("Whirlpool", r"^[a-f0-9]{128}$"),
]

# 常见弱密码
COMMON_PASSWORDS = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "sunshine",
    "iloveyou", "princess", "admin", "welcome", "666666",
    "abc123", "football", "123123", "monkey", "654321",
    "!@#$%^&*", "password1", "qwerty123", "1q2w3e4r",
    "admin123", "letmein", "dragon", "baseball", "master",
    "shadow", "michael", "superman", "batman", "trustno1",
    "root", "toor", "changeme", "default", "temp123",
    "passw0rd", "P@ssw0rd", "Password123", "Admin@123",
]


@register(
    "hash_identifier",
    "识别哈希类型。根据格式特征判断哈希算法（MD5/SHA/bcrypt/NTLM 等）。",
    {"hash_value": {"type": "string", "description": "要识别的哈希字符串"}}
)
def hash_identifier(hash_value: str) -> str:
    hash_value = hash_value.strip()
    matches = []

    for name, pattern in HASH_PATTERNS:
        if re.match(pattern, hash_value):
            matches.append({
                "type": name, "confidence": "high", "length": len(hash_value),
            })

    if not matches:
        # 根据长度推测
        length_hints = {
            32: ["MD5", "NTLM (大写)", "CRC32"],
            40: ["SHA-1", "RIPEMD-160"],
            56: ["SHA-224"],
            64: ["SHA-256"],
            96: ["SHA-384"],
            128: ["SHA-512", "Whirlpool"],
        }
        hints = length_hints.get(len(hash_value), [])
        if hints:
            matches.append({
                "type": " / ".join(hints), "confidence": "low",
                "length": len(hash_value),
            })
        else:
            char_types = []
            if re.search(r'[a-f]', hash_value):
                char_types.append("hex小写")
            if re.search(r'[A-F]', hash_value):
                char_types.append("hex大写")
            if re.search(r'[g-zG-Z/+]', hash_value):
                char_types.append("Base64")
            if "$" in hash_value:
                char_types.append("类Unix crypt格式")
            matches.append({
                "type": "未知", "confidence": "none",
                "length": len(hash_value), "char_types": char_types,
            })

    return json.dumps({
        "hash_preview": hash_value[:50] + ("..." if len(hash_value) > 50 else ""),
        "matches": matches[:5],
    }, ensure_ascii=False)


def _calculate_entropy(password: str) -> float:
    """计算密码熵值"""
    if not password:
        return 0
    char_set = 0
    if re.search(r'[a-z]', password):
        char_set += 26
    if re.search(r'[A-Z]', password):
        char_set += 26
    if re.search(r'[0-9]', password):
        char_set += 10
    if re.search(r'[^a-zA-Z0-9]', password):
        char_set += 33
    if char_set == 0:
        return 0
    return len(password) * math.log2(char_set)


@register(
    "password_audit",
    "密码强度审计：分析密码长度、复杂度、熵值，检测是否为常见弱密码，查询 HaveIBeenPwned 泄露记录 (k-anonymity)。",
    {"password": {"type": "string", "description": "要审计的密码（仅用于分析，不会被存储）"}}
)
def password_audit(password: str) -> str:
    if not password:
        return json.dumps({"error": "密码不能为空"})

    issues = []
    score = 100

    # 长度检查
    length = len(password)
    if length < 8:
        issues.append({"type": "length", "severity": "high",
                       "description": f"密码太短 ({length} 字符)，建议至少 12 位"})
        score -= 30
    elif length < 12:
        issues.append({"type": "length", "severity": "medium",
                       "description": f"密码长度一般 ({length} 字符)，建议 12 位以上"})
        score -= 10

    # 复杂度检查
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[^a-zA-Z0-9]', password))

    complexity = sum([has_lower, has_upper, has_digit, has_special])
    if complexity < 3:
        issues.append({"type": "complexity", "severity": "medium",
                       "description": f"字符类型不足 ({complexity}/4)，应包含大小写字母、数字和特殊字符"})
        score -= 20

    # 常见模式检测
    if re.search(r'(.)\\1{2,}', password):
        issues.append({"type": "pattern", "severity": "low",
                       "description": "包含重复字符"})
        score -= 5

    # 键盘序列
    keyboard_seq = ["qwerty", "asdfgh", "zxcvbn", "qazwsx", "123456", "654321"]
    for seq in keyboard_seq:
        if seq in password.lower():
            issues.append({"type": "pattern", "severity": "medium",
                           "description": f"包含键盘序列: {seq}"})
            score -= 15
            break

    # 常见弱密码
    if password.lower() in COMMON_PASSWORDS or password in COMMON_PASSWORDS:
        issues.append({"type": "common", "severity": "critical",
                       "description": "这是最常见的弱密码之一"})
        score -= 40

    # 熵值
    entropy = _calculate_entropy(password)
    if entropy < 40:
        issues.append({"type": "entropy", "severity": "high",
                       "description": f"熵值过低 ({entropy:.1f} bits)，低于 40 bits 不安全"})
        score -= 20
    elif entropy < 60:
        issues.append({"type": "entropy", "severity": "medium",
                       "description": f"熵值一般 ({entropy:.1f} bits)，建议达到 60+ bits"})
        score -= 5

    # HaveIBeenPwned k-anonymity 检查
    pwned_result = None
    try:
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]
        ctx = ssl.create_default_context()
        try:
            ctx = ssl._create_unverified_context()
        except Exception:
            pass
        req = urllib.request.Request(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={"User-Agent": "SynapseAI-Security-Audit"}
        )
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            for line in resp.read().decode().splitlines():
                if line.startswith(suffix):
                    count = int(line.split(":")[1])
                    pwned_result = count
                    issues.append({"type": "breached", "severity": "critical",
                                   "description": f"此密码已在数据泄露中出现 {count} 次 (HaveIBeenPwned)"})
                    score -= 50
                    break
    except Exception:
        pwned_result = "查询失败"

    score = max(0, score)

    if score >= 80:
        grade, grade_color = "强", "green"
    elif score >= 50:
        grade, grade_color = "中等", "orange"
    else:
        grade, grade_color = "弱", "red"

    return json.dumps({
        "score": score, "grade": grade,
        "entropy_bits": round(entropy, 1),
        "length": length,
        "complexity": f"{complexity}/4 (小写:{has_lower} 大写:{has_upper} 数字:{has_digit} 特殊:{has_special})",
        "pwned_count": pwned_result,
        "issues_count": len(issues), "issues": issues,
    }, ensure_ascii=False)
