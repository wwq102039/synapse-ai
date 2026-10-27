"""Web 漏洞检测工具 — XSS/SQLi/安全头审计/通用漏洞扫描"""
import json
import re
import ssl
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from .. import register
from ..web_search import _is_safe_url

# XSS 探针负载
XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '"><script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '"><img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '"><svg onload=alert(1)>',
    "';alert(1);//",
    'javascript:alert(1)',
]

# SQLi 探针负载
SQLI_PAYLOADS = [
    "'",
    '"',
    "' OR '1'='1",
    "\" OR \"1\"=\"1",
    "' OR 1=1 --",
    "\" OR 1=1 --",
    "1' AND '1'='1",
    "' UNION SELECT NULL--",
    "1; SELECT SLEEP(5)--",
]

SQL_ERROR_PATTERNS = [
    r"SQL syntax.*MySQL", r"Warning.*mysql_", r"MySQLSyntaxErrorException",
    r"valid MySQL result", r"PostgreSQL.*ERROR", r"Warning.*\Wpg_",
    r"Microsoft SQL Server", r"ODBC.*Driver", r"SQLite.*error",
    r"ORA-\d{5}", r"Oracle.*Driver", r"unclosed quotation mark",
    r"Unclosed quotation mark", r"SQLite3::query",
]


def _fetch_with_ssl(url: str, timeout: int = 8) -> tuple[int, str, dict]:
    """抓取 URL，返回 (状态码, 响应体, 响应头)"""
    ctx = ssl.create_default_context()
    try:
        ctx = ssl._create_unverified_context()
    except Exception:
        pass
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return e.code, body, dict(e.headers)
    except Exception as e:
        raise e


@register(
    "web_vuln_scan",
    "Web 漏洞快速扫描：检测敏感文件泄露（.git/.env/备份）、目录列表、默认页面等信息泄露。",
    {"url": {"type": "string", "description": "目标网站 URL，如 https://example.com"}}
)
def web_vuln_scan(url: str) -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    base = url.rstrip("/")
    findings = []

    # 敏感文件检查
    sensitive = [
        (".git/HEAD", "Git 仓库泄露"),
        (".env", "环境变量文件泄露"),
        (".env.backup", "环境变量备份泄露"),
        (".env.local", "本地环境变量泄露"),
        ("backup.zip", "备份文件泄露"),
        ("dump.sql", "数据库备份泄露"),
        ("config.php.bak", "PHP 配置备份泄露"),
        ("wp-config.php.bak", "WordPress 配置备份"),
        ("web.config", "IIS 配置文件泄露"),
        (".DS_Store", "macOS 文件泄露"),
        ("phpinfo.php", "PHP 信息泄露"),
        ("info.php", "PHP 信息泄露"),
        ("actuator/env", "Spring Boot 环境信息泄露"),
        ("actuator/mappings", "Spring Boot 路由泄露"),
        ("server-status", "Apache 状态页泄露"),
        ("server-info", "Apache 信息页泄露"),
    ]

    for path, desc in sensitive:
        test_url = f"{base}/{path}"
        try:
            code, body, _ = _fetch_with_ssl(test_url, timeout=5)
            if code == 200:
                findings.append({
                    "type": "info_leak", "severity": "high",
                    "url": test_url, "description": desc,
                    "evidence": body[:200],
                })
            elif code == 403:
                findings.append({
                    "type": "info_leak", "severity": "info",
                    "url": test_url, "description": f"{desc} (存在但返回 403)",
                })
        except Exception:
            pass

    # 目录列表检查
    try:
        _, body, _ = _fetch_with_ssl(base, timeout=8)
        if re.search(r'(Index of|Directory Listing|Parent Directory)', body, re.I):
            findings.append({
                "type": "dir_listing", "severity": "medium",
                "url": base, "description": "目录列表功能开启，可能暴露文件结构",
            })
    except Exception:
        pass

    return json.dumps({
        "url": base, "findings_count": len(findings), "findings": findings,
    }, ensure_ascii=False)


@register(
    "xss_test",
    "XSS 反射点检测。向 URL 参数注入 XSS 探针，检查是否在响应中原样回显。",
    {"url": {"type": "string", "description": "目标 URL（含参数），如 https://example.com/search?q=test"}}
)
def xss_test(url: str) -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []

    for param_name in params:
        for payload in XSS_PAYLOADS[:5]:
            test_params = params.copy()
            test_params[param_name] = [payload]
            new_query = urlencode(test_params, doseq=True)
            test_url = urlunparse(parsed._replace(query=new_query))

            try:
                _, body, _ = _fetch_with_ssl(test_url, timeout=8)
                if payload in body:
                    findings.append({
                        "parameter": param_name, "payload": payload,
                        "reflected": True,
                        "context": body[max(0, body.index(payload)-50):body.index(payload)+len(payload)+50],
                    })
                    break  # 一个参数找到反射点就换下一个
            except Exception:
                continue

    return json.dumps({
        "url": url, "params_tested": len(params),
        "vulnerable_params": len(findings), "findings": findings,
    }, ensure_ascii=False)


@register(
    "sqli_test",
    "SQL 注入点检测。向 URL 参数注入 SQL 探针，分析响应中的数据库错误信息。",
    {"url": {"type": "string", "description": "目标 URL（含参数），如 https://example.com/product?id=1"}}
)
def sqli_test(url: str) -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []

    for param_name in params:
        for payload in SQLI_PAYLOADS[:6]:
            test_params = params.copy()
            test_params[param_name] = [payload]
            new_query = urlencode(test_params, doseq=True)
            test_url = urlunparse(parsed._replace(query=new_query))

            try:
                _, body, _ = _fetch_with_ssl(test_url, timeout=8)
                for pattern in SQL_ERROR_PATTERNS:
                    if re.search(pattern, body, re.I):
                        findings.append({
                            "parameter": param_name, "payload": payload,
                            "db_type": pattern.split(r"\W")[0],
                            "evidence": re.findall(pattern, body, re.I)[0][:100]
                            if re.findall(pattern, body, re.I) else "",
                        })
                        break
                if any(f["parameter"] == param_name for f in findings):
                    break
            except Exception:
                continue

    return json.dumps({
        "url": url, "params_tested": len(params),
        "vulnerable_params": len(findings), "findings": findings,
    }, ensure_ascii=False)


@register(
    "http_header_audit",
    "HTTP 安全头审计。检查目标网站的安全相关 HTTP 响应头是否缺失或配置不当。",
    {"url": {"type": "string", "description": "目标网站 URL"}}
)
def http_header_audit(url: str) -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    try:
        _, body, headers = _fetch_with_ssl(url, timeout=10)
    except Exception as e:
        return json.dumps({"error": f"无法访问 {url}: {e}"})

    checks = [
        ("Content-Security-Policy", "CSP 防止 XSS/代码注入", "critical", None),
        ("Strict-Transport-Security", "HSTS 强制 HTTPS", "high", None),
        ("X-Content-Type-Options", "防止 MIME 嗅探", "medium", "nosniff"),
        ("X-Frame-Options", "防止点击劫持", "medium", None),
        ("X-XSS-Protection", "浏览器 XSS 过滤", "low", "1; mode=block"),
        ("Referrer-Policy", "控制 Referer 泄露", "low", None),
        ("Permissions-Policy", "限制浏览器 API", "low", None),
        ("X-Permitted-Cross-Domain-Policies", "跨域策略控制", "low", "none"),
        ("Cross-Origin-Resource-Policy", "跨源资源策略", "low", "same-origin"),
    ]

    results = []
    for header, desc, severity, recommended in checks:
        value = headers.get(header) or headers.get(header.lower())
        if value:
            status = "present"
            note = value[:100]
        else:
            status = "missing"
            note = f"建议设置: {recommended}" if recommended else "建议添加此头"

        results.append({
            "header": header, "status": status, "severity": severity,
            "description": desc, "value": note,
        })

    # Server 头信息泄露
    server = headers.get("Server") or headers.get("server") or ""
    if server:
        results.append({
            "header": "Server", "status": "info_leak", "severity": "low",
            "description": "Server 头泄露服务器软件和版本",
            "value": server[:100],
        })

    # X-Powered-By
    powered = headers.get("X-Powered-By") or headers.get("x-powered-by") or ""
    if powered:
        results.append({
            "header": "X-Powered-By", "status": "info_leak", "severity": "low",
            "description": "泄露后端技术栈信息",
            "value": powered[:100],
        })

    missing_critical = sum(1 for r in results if r["status"] == "missing" and r["severity"] in ("critical", "high"))

    return json.dumps({
        "url": url, "headers_checked": len(checks) + 2,
        "missing_critical": missing_critical,
        "results": results,
    }, ensure_ascii=False)
