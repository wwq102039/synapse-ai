import json
import urllib.request
import urllib.parse
import re
import html as html_mod
import ipaddress
import http.cookiejar
import ssl
from urllib.parse import urlparse
from . import register


# 禁止访问的 IP 范围（内网、回环、链路本地、云元数据等）
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


# 禁止访问的域名（本地/内网主机名）
BLOCKED_HOSTNAMES = {
    "localhost", "localhost.localdomain",
    "0.0.0.0", "127.0.0.1", "[::1]",
}

SEARCH_TIMEOUT = 5  # 搜索超时（秒）

_baidu_opener = None
_baidu_ready = False


def _init_baidu_session():
    """初始化百度 opener — 只执行一次"""
    global _baidu_opener, _baidu_ready
    if _baidu_ready:
        return
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    cj = http.cookiejar.CookieJar()
    _baidu_opener = urllib.request.build_opener(
        https_handler,
        urllib.request.HTTPCookieProcessor(cj)
    )
    _baidu_ready = True


def _get_baidu_opener():
    """获取百度 opener（自动初始化）"""
    _init_baidu_session()
    return _baidu_opener


def _unverified_urlopen(url, timeout=5, **kwargs):
    """跳过 SSL 验证的 urlopen 快捷方式"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, **kwargs) if isinstance(url, str) else url
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _is_safe_url(url: str) -> bool:
    """验证 URL 是否安全（防止 SSRF）"""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"禁止的协议: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("无法解析主机名")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"禁止访问内部地址: {hostname}")

    if hostname.lower().endswith(".local"):
        raise ValueError(f"禁止访问内网域名: {hostname}")

    try:
        addr = ipaddress.ip_address(hostname)
        for net in BLOCKED_NETWORKS:
            if addr in net:
                raise ValueError(f"禁止访问内网地址: {hostname}")
    except ValueError as e:
        if "禁止访问" in str(e):
            raise
        pass

    return True


_BAIDU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _ddg_search(query: str) -> list[dict]:
    """DuckDuckGo 搜索，失败抛异常"""
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with _unverified_urlopen(req, timeout=SEARCH_TIMEOUT) as resp:
        html_content = resp.read().decode("utf-8", errors="ignore")

    results = []
    for match in re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html_content, re.DOTALL
    ):
        snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()
        snippet = html_mod.unescape(snippet)
        results.append({
            "title": html_mod.unescape(re.sub(r'<[^>]+>', '', match.group(2)).strip()),
            "url": urllib.parse.unquote(match.group(1)),
            "snippet": snippet
        })
    return results[:8]


def _baidu_search(query: str) -> list[dict]:
    """百度搜索 — 自动初始化会话，失败抛异常"""
    opener = _get_baidu_opener()
    encoded = urllib.parse.quote(query)
    url = f"https://www.baidu.com/s?wd={encoded}&rn=10"
    req = urllib.request.Request(url, headers={
        **_BAIDU_HEADERS,
        "Referer": "https://www.baidu.com/",
    })
    resp = opener.open(req, timeout=SEARCH_TIMEOUT)
    html_content = resp.read().decode("utf-8", errors="ignore")

    # 检测安全验证页
    if len(html_content) < 3000 and ("安全验证" in html_content or "timeout" in html_content):
        raise Exception("百度安全验证拦截")

    results = []

    # 提取 h3 标题（含 t 类名或任意 h3）+ 链接
    for match in re.finditer(
        r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        html_content, re.DOTALL
    ):
        link = match.group(1)
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', match.group(2)).strip())
        if len(title) < 6:
            continue
        results.append({
            "title": title[:120],
            "url": link,
            "snippet": ""
        })

    # 提取 c-abstract 摘要
    abstracts = re.findall(
        r'<(?:span|div)[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</(?:span|div)>',
        html_content, re.DOTALL
    )
    all_abstracts = []
    for a in abstracts:
        clean = html_mod.unescape(re.sub(r'<[^>]+>', '', a).strip())
        if len(clean) > 10:
            all_abstracts.append(clean[:200])

    for i, result in enumerate(results):
        if i < len(all_abstracts):
            result["snippet"] = all_abstracts[i]

    # 如果 h3 解析不到，宽松提取外部链接
    if not results:
        for match in re.finditer(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]{10,100})</a>',
            html_content
        ):
            link = match.group(1)
            title = html_mod.unescape(re.sub(r'<[^>]+>', '', match.group(2)).strip())
            skip_terms = ("baidu.com/link", "ICP", "许可证", "公网安备", "copyright", "登录", "注册")
            if any(t in link.lower() or t in title for t in skip_terms):
                continue
            if len(title) > 8:
                results.append({
                    "title": title[:120],
                    "url": urllib.parse.unquote(link),
                    "snippet": ""
                })
            if len(results) >= 8:
                break

    return results[:8]


def _bing_search(query: str) -> list[dict]:
    """Bing 搜索备用 — 已弃用，委托给 _baidu_search"""
    return _baidu_search(query)


@register(
    "web_search",
    "搜索互联网信息。境内百度优先，失败后切 DuckDuckGo。用于查找最新新闻、事实或任何实时信息。",
    {"query": {"type": "string", "description": "搜索关键词"}}
)
def web_search(query: str) -> str:
    try:
        try:
            results = _baidu_search(query)
            engine = "baidu"
        except Exception:
            try:
                results = _ddg_search(query)
                engine = "duckduckgo"
            except Exception as e:
                return json.dumps({
                    "error": f"搜索暂时不可用（百度、DuckDuckGo 均超时）。"
                             f"请尝试使用 web_fetch 直接访问已知的相关网站（如 sdzk.cn、gov.cn 等），"
                             f"或基于已知信息回答用户问题。错误: {str(e)[:100]}",
                    "results": []
                }, ensure_ascii=False)

        return json.dumps({"query": query, "engine": engine, "results": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}", "results": []})


@register(
    "web_fetch",
    "抓取并阅读网页内容。用于阅读文章、文档或任何网页。",
    {"url": {"type": "string", "description": "要抓取和阅读的网址（仅限 http/https）"}}
)
def web_fetch(url: str) -> str:
    try:
        _is_safe_url(url)

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=SEARCH_TIMEOUT) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.I)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = html_mod.unescape(text)

        if len(text) > 6000:
            text = text[:6000] + "\n... [truncated]"

        return json.dumps({"url": url, "content": text}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Fetch failed: {str(e)}"})
