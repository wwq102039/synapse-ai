"""信息收集工具 — WHOIS/DNS/URL 安全分析"""
import json
import re
import socket
import ssl
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlunparse
from .. import register
from ..web_search import _is_safe_url

# WHOIS 服务器映射 (TLD → whois server)
WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
    "cn": "whois.cnnic.cn",
    "io": "whois.nic.io",
    "co": "whois.nic.co",
    "dev": "whois.nic.google",
    "app": "whois.nic.google",
    "ai": "whois.nic.ai",
    "me": "whois.nic.me",
    "info": "whois.afilias.net",
    "biz": "whois.nic.biz",
    "xyz": "whois.nic.xyz",
    "top": "whois.nic.top",
    "vip": "whois.nic.vip",
}


def _whois_query(domain: str, server: str) -> str:
    """向 WHOIS 服务器发送查询"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((server, 43))
        sock.send(f"{domain}\r\n".encode())
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8", errors="replace")
    finally:
        sock.close()


def _build_dns_query(domain: str, qtype: int) -> bytes:
    """手动构造 DNS 查询包"""
    # 简化的 DNS 查询构造
    tid = b"\x00\x01"
    flags = b"\x01\x00"  # 标准查询 + RD
    qdcount = b"\x00\x01"
    ancount = b"\x00\x00"
    nscount = b"\x00\x00"
    arcount = b"\x00\x00"

    question = b""
    for label in domain.encode("idna").decode().split("."):
        question += bytes([len(label)]) + label.encode()
    question += b"\x00"
    question += qtype.to_bytes(2, "big")
    question += b"\x00\x01"  # IN class

    return tid + flags + qdcount + ancount + nscount + arcount + question


def _parse_dns_response(data: bytes) -> list[str]:
    """从 DNS 响应中提取 IP 地址"""
    results = []
    try:
        # 跳过头部 12 字节 + question section
        offset = 12
        # 跳过 question
        while offset < len(data) and data[offset] != 0:
            offset += data[offset] + 1
        offset += 5  # skip null byte + QTYPE + QCLASS

        # 解析 answer section
        while offset < len(data) - 10:
            if data[offset] == 0xC0:
                offset += 2  # pointer
            else:
                while offset < len(data) and data[offset] != 0:
                    offset += data[offset] + 1
                offset += 1

            if offset + 10 > len(data):
                break

            rtype = int.from_bytes(data[offset:offset+2], "big")
            offset += 2
            rclass = int.from_bytes(data[offset:offset+2], "big")
            offset += 2
            offset += 4  # TTL
            rdlength = int.from_bytes(data[offset:offset+2], "big")
            offset += 2

            if rtype == 1 and rdlength == 4:  # A record
                ip = ".".join(str(b) for b in data[offset:offset+4])
                results.append(ip)
            elif rtype == 15 and rdlength >= 2:  # MX
                offset += 2  # preference
                name = ""
                pos = offset
                while pos < offset + rdlength - 2:
                    if data[pos] == 0xC0:
                        pos += 2
                        break
                    elif data[pos] == 0:
                        break
                    else:
                        length = data[pos]
                        pos += 1
                        name += data[pos:pos+length].decode("ascii", errors="replace") + "."
                        pos += length
                results.append(f"MX: {name.rstrip('.')}")

            offset += rdlength
    except Exception:
        pass
    return results


@register(
    "whois_lookup",
    "查询域名 WHOIS 信息：注册商、注册/到期日期、名称服务器等。",
    {"domain": {"type": "string", "description": "要查询的域名，如 example.com"}}
)
def whois_lookup(domain: str) -> str:
    domain = domain.lower().strip()
    # 提取主域名
    parts = domain.split(".")
    if len(parts) < 2:
        return json.dumps({"error": "无效域名"})

    tld = parts[-1]
    server = WHOIS_SERVERS.get(tld, "whois.iana.org")

    try:
        raw = _whois_query(domain, server)

        # 如果返回的是 refer 到另一个服务器
        ref_match = re.search(r'(?:Registrar WHOIS Server|whois server|Whois Server|refer):\s*(\S+)', raw, re.I)
        if ref_match and ref_match.group(1) != server:
            try:
                raw = _whois_query(domain, ref_match.group(1))
            except Exception:
                pass

        info = {}
        # 提取关键信息
        for key, pattern in [
            ("registrar", r"(?:Registrar|Sponsoring Registrar):\s*(.+)"),
            ("creation_date", r"(?:Creation Date|Created on|Registration Time):\s*(.+)"),
            ("expiration_date", r"(?:Registry Expiry Date|Expiry Date|Expiration Date|Expiration Time):\s*(.+)"),
            ("name_servers", r"Name Server:\s*(.+)"),
            ("status", r"(?:Domain Status|Status):\s*(.+)"),
        ]:
            matches = re.findall(pattern, raw, re.I)
            if key == "name_servers":
                info[key] = [m.strip().lower() for m in matches]
            elif matches:
                info[key] = matches[0].strip()

        return json.dumps({
            "domain": domain, "whois_server": server,
            "info": info,
            "raw": raw[:3000],
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"WHOIS 查询失败: {e}"})


@register(
    "dns_enum",
    "DNS 记录枚举。查询域名的 A/MX/NS/TXT/CNAME/SOA 记录。",
    {
        "domain": {"type": "string", "description": "目标域名"},
        "record_types": {"type": "string", "description": "记录类型，逗号分隔，默认 'A,MX,NS,TXT'"},
    }
)
def dns_enum(domain: str, record_types: str = "A,MX,NS,TXT") -> str:
    domain = domain.lower().strip()
    type_map = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16}
    requested = [t.strip().upper() for t in record_types.split(",") if t.strip().upper() in type_map]

    if not requested:
        requested = ["A", "MX", "NS", "TXT"]

    results = {}
    dns_servers = ["8.8.8.8", "1.1.1.1", "114.114.114.114"]

    for rtype in requested:
        qtype = type_map[rtype]
        for dns_ip in dns_servers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)
                query = _build_dns_query(domain, qtype)
                sock.sendto(query, (dns_ip, 53))
                data, _ = sock.recvfrom(1024)
                sock.close()
                records = _parse_dns_response(data)
                if records:
                    results[rtype] = records
                    break
            except Exception:
                continue

    # 使用 socket.gethostbyname 作为 A 记录的回退
    if "A" not in results:
        try:
            ip = socket.gethostbyname(domain)
            results["A"] = [ip]
        except Exception:
            pass

    return json.dumps({
        "domain": domain,
        "record_types_queried": requested,
        "records": results,
    }, ensure_ascii=False)


@register(
    "url_analyzer",
    "URL 安全分析：检测钓鱼特征、短链接展开、重定向链跟踪、域名仿冒分析。",
    {"url": {"type": "string", "description": "要分析的 URL"}}
)
def url_analyzer(url: str) -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    findings = []
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path

    # 1. IP 地址作为主机名
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain.split(":")[0]):
        findings.append({"type": "ip_hostname", "severity": "medium",
                        "description": "使用 IP 地址代替域名，常见于钓鱼"})

    # 2. 异常端口
    if ":" in domain:
        try:
            port = int(domain.split(":")[1])
            if port not in (80, 443, 8080, 8443):
                findings.append({"type": "unusual_port", "severity": "low",
                                "description": f"使用了非标准端口: {port}"})
        except ValueError:
            pass

    # 3. @ 符号（用户信息欺骗）
    if "@" in parsed.netloc.split(":")[0] if ":" in parsed.netloc else "@" in parsed.netloc:
        findings.append({"type": "at_symbol", "severity": "high",
                        "description": "URL 包含 @ 符号，可能是登录信息欺骗攻击"})

    # 4. 过长 URL
    if len(url) > 200:
        findings.append({"type": "long_url", "severity": "low",
                        "description": f"URL 过长 ({len(url)} 字符)"})

    # 5. 敏感路径关键词
    sensitive_keywords = ["login", "signin", "verify", "secure", "account",
                          "password", "bank", "paypal", "update", "confirm"]
    for kw in sensitive_keywords:
        if kw in path.lower():
            findings.append({"type": "sensitive_path", "severity": "low",
                            "description": f"路径包含敏感关键词: {kw}"})
            break

    # 6. 可疑 TLD
    suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".work", ".click"]
    for tld in suspicious_tlds:
        if domain.endswith(tld) or domain.split(":")[0].endswith(tld):
            findings.append({"type": "suspicious_tld", "severity": "medium",
                            "description": f"使用可疑顶级域名: {tld}"})
            break

    # 7. 短链接展开
    shorteners = ["bit.ly", "t.co", "tinyurl.com", "ow.ly", "is.gd", "buff.ly",
                  "goo.gl", "shorte.st", "adf.ly", "bc.vc", "short.link"]
    is_short = any(s in domain for s in shorteners)
    if is_short:
        expanded = url
        try:
            ctx = ssl.create_default_context()
            try:
                ctx = ssl._create_unverified_context()
            except Exception:
                pass
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                expanded = resp.geturl()
        except Exception:
            pass
        findings.append({"type": "short_url", "severity": "info",
                        "description": f"短链接，展开为: {expanded}"})

    # 8. 重定向链分析
    redirects = []
    current_url = url
    for _ in range(5):
        try:
            ctx = ssl.create_default_context()
            try:
                ctx = ssl._create_unverified_context()
            except Exception:
                pass
            req = urllib.request.Request(current_url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                final = resp.geturl()
                if final != current_url:
                    redirects.append({"from": current_url, "to": final, "status": resp.status})
                    current_url = final
                else:
                    break
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location", "")
                redirects.append({"from": current_url, "to": loc, "status": e.code})
                current_url = loc
            else:
                break
        except Exception:
            break

    return json.dumps({
        "url": url, "domain": domain,
        "findings_count": len(findings), "findings": findings,
        "redirects": redirects, "redirect_count": len(redirects),
    }, ensure_ascii=False)
