"""Synapse AI 安全工具集 — 端口扫描、子域名枚举、目录爆破"""
import json
import socket
import time
import ssl
import urllib.request
from urllib.parse import urlparse
from .. import register
from ..web_search import _is_safe_url

# 常见端口及其服务
COMMON_PORTS = [
    (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"), (53, "DNS"),
    (80, "HTTP"), (110, "POP3"), (111, "RPC"), (135, "RPC"), (139, "NetBIOS"),
    (143, "IMAP"), (443, "HTTPS"), (445, "SMB"), (993, "IMAPS"), (995, "POP3S"),
    (1723, "PPTP"), (3306, "MySQL"), (3389, "RDP"), (5432, "PostgreSQL"),
    (5900, "VNC"), (6379, "Redis"), (8080, "HTTP-Alt"), (8443, "HTTPS-Alt"),
    (9200, "ES"), (11211, "Memcached"), (27017, "MongoDB"),
]

# 常见子域名字典
SUBDOMAIN_LIST = [
    "www", "mail", "ftp", "smtp", "pop", "pop3", "imap", "webmail",
    "admin", "api", "dev", "staging", "test", "beta", "demo",
    "blog", "shop", "store", "cdn", "static", "assets", "media",
    "m", "mobile", "app", "apps", "dashboard", "portal", "login",
    "secure", "ssl", "vpn", "remote", "gateway", "proxy", "ns1", "ns2",
    "dns", "dns1", "dns2", "mx", "mx1", "mx2", "smtp2",
    "sql", "mysql", "db", "database", "data", "files", "docs",
    "wiki", "support", "help", "status", "monitor", "monitoring",
    "git", "svn", "jenkins", "ci", "jira", "confluence",
    "forum", "community", "news", "events", "careers", "jobs",
    "stage", "uat", "qa", "sandbox", "backup", "old", "new",
    "internal", "intranet", "staff", "employee", "hr",
    "autodiscover", "cpanel", "whm", "webdisk", "webmail2",
    "cloud", "cluster", "node1", "node2", "kibana", "grafana",
    "prometheus", "alertmanager", "traefik", "portainer",
    "vault", "consul", "etcd", "rancher", "argocd",
    "registry", "docker", "swarm", "k8s", "kubernetes",
    "minio", "s3", "storage", "bucket", "upload", "download",
    "rest", "soap", "graphql", "ws", "socket", "realtime",
    "chat", "messenger", "notification", "email", "newsletter",
    "hooks", "webhook", "callback", "oauth", "openid", "sso",
]

# 常见 Web 路径字典
COMMON_PATHS = [
    "admin", "login", "wp-admin", "administrator", "phpmyadmin",
    ".git/HEAD", ".env", ".env.backup", ".env.local", ".env.production",
    "backup", "backups", "backup.zip", "backup.tar.gz", "dump.sql",
    "robots.txt", "sitemap.xml", "crossdomain.xml", "security.txt",
    "README.md", "CHANGELOG.md", "LICENSE", "composer.json", "package.json",
    "web.config", ".htaccess", "config.php", "config.php.bak",
    "wp-config.php", "wp-config.php.bak", "wp-content/",
    "adminer.php", "info.php", "phpinfo.php", "test.php",
    "api", "api/v1", "api/v2", "graphql", "swagger", "swagger-ui",
    "docs", "documentation", "help", "manual",
    "uploads", "upload", "images", "img", "css", "js", "assets",
    "temp", "tmp", "cache", "logs", "log", "error.log", "access.log",
    "debug", "trace", "profiler", "phpinfo",
    ".svn/entries", ".DS_Store", ".well-known/security.txt",
    "actuator", "actuator/health", "actuator/env", "actuator/mappings",
    "console", "admin/console", "manager/html", "host-manager/html",
    "jmx-console", "web-console", "invoker/JMXInvokerServlet",
    "wp-login.php", "user/login", "user/register", "signup",
    "api/users", "api/admin", "api/health", "api/status",
    "server-status", "server-info", "status", "health", "ping",
    ".git/config", ".gitignore", ".travis.yml", "Jenkinsfile", "Dockerfile",
    "docker-compose.yml", "Makefile", "Gruntfile.js", "gulpfile.js",
    "cgi-bin/", "cgi-bin/test-cgi", "cgi-bin/php", "cgi-bin/php5",
    "owa/", "ecp/", "ews/", "owa/auth.owa", "Autodiscover/Autodiscover.xml",
]


@register(
    "port_scan",
    "TCP 端口扫描 + Banner 抓取。用于发现目标主机开放的服务和端口。",
    {
        "host": {"type": "string", "description": "目标主机名或 IP 地址"},
        "ports": {"type": "string", "description": "端口范围，如 '1-1000' 或 'common'（常见 100 端口，默认）"},
        "timeout": {"type": "number", "description": "单端口超时秒数（默认 2）"},
    }
)
def port_scan(host: str, ports: str = "common", timeout: float = 2.0) -> str:
    timeout = min(max(timeout, 0.5), 5.0)
    results = []

    if ports == "common":
        port_list = COMMON_PORTS
    elif "-" in ports:
        parts = ports.split("-")
        start, end = int(parts[0]), int(parts[1])
        end = min(end, start + 100)
        port_list = [(p, "unknown") for p in range(start, end + 1)]
    else:
        try:
            port_list = [(int(ports), "unknown")]
        except ValueError:
            return json.dumps({"error": f"无效端口: {ports}"})

    for port, service in port_list:
        if len(results) % 10 == 0 and results:
            time.sleep(0.1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                banner = ""
                try:
                    sock.settimeout(1)
                    sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                    banner = sock.recv(256).decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
                results.append({
                    "port": port, "service": service, "state": "open",
                    "banner": banner[:200] if banner else "",
                })
        except socket.gaierror:
            return json.dumps({"error": f"无法解析主机: {host}"})
        except Exception as e:
            results.append({"port": port, "error": str(e)})
        finally:
            sock.close()

    return json.dumps({
        "host": host, "ports_scanned": len(port_list),
        "open_ports": len([r for r in results if r.get("state") == "open"]),
        "results": results,
    }, ensure_ascii=False)


@register(
    "subdomain_enum",
    "子域名枚举。通过 DNS 解析发现目标的子域名。",
    {
        "domain": {"type": "string", "description": "目标域名，如 example.com"},
        "wordlist": {"type": "string", "description": "字典类型: 'common'（200 词）、'quick'（50 词）"},
    }
)
def subdomain_enum(domain: str, wordlist: str = "common") -> str:
    words = SUBDOMAIN_LIST if wordlist == "common" else SUBDOMAIN_LIST[:50]
    found = []

    for i, sub in enumerate(words):
        if i > 0 and i % 20 == 0:
            time.sleep(0.2)
        hostname = f"{sub}.{domain}"
        try:
            addr = socket.gethostbyname(hostname)
            if addr:
                found.append({"subdomain": hostname, "ip": addr, "type": "A"})
        except socket.gaierror:
            pass

    return json.dumps({
        "domain": domain, "checked": len(words),
        "found": len(found), "results": found,
    }, ensure_ascii=False)


@register(
    "dir_bruteforce",
    "Web 目录/文件爆破。发现目标网站的隐藏路径和敏感文件。",
    {
        "url": {"type": "string", "description": "目标网站 URL，如 https://example.com"},
        "wordlist": {"type": "string", "description": "字典: 'common'（100 路径）、'quick'（40 路径）"},
    }
)
def dir_bruteforce(url: str, wordlist: str = "common") -> str:
    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    base = url.rstrip("/")
    paths = COMMON_PATHS if wordlist == "common" else COMMON_PATHS[:40]
    found = []
    ssl_ctx = ssl.create_default_context()
    try:
        ssl_ctx = ssl._create_unverified_context()
    except Exception:
        pass

    for i, path in enumerate(paths):
        if i > 0 and i % 15 == 0:
            time.sleep(0.3)
        test_url = f"{base}/{path.lstrip('/')}"
        try:
            req = urllib.request.Request(test_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                status = resp.status
                size = len(resp.read() or b"")
                found.append({
                    "url": test_url, "status": status,
                    "size": size if size < 10000 else ">10KB",
                })
        except urllib.error.HTTPError as e:
            if e.code in (200, 301, 302, 403, 401):
                found.append({"url": test_url, "status": e.code, "size": "?"})
        except Exception:
            pass

    return json.dumps({
        "base_url": base, "checked": len(paths),
        "found": len(found), "results": found,
    }, ensure_ascii=False)
