"""Web Crawler — BFS 爬取同域名页面，提取链接和正文。复用 SSRF 防护。"""
import json
import time
import re
import ssl
import html as html_mod
import urllib.request
import urllib.parse
from urllib.parse import urljoin, urlparse
from . import register
from .web_search import _is_safe_url

# Windows 环境 SSL 证书兼容
_SSL_CONTEXT = ssl.create_default_context()
try:
    _SSL_CONTEXT = ssl._create_unverified_context() if not _SSL_CONTEXT.cert_store_stats().get('x509_ca') else _SSL_CONTEXT
except Exception:
    _SSL_CONTEXT = ssl._create_unverified_context()


def _extract_links(html_text: str, base_url: str) -> list[dict]:
    """从 HTML 中提取所有链接，解析相对路径"""
    links = []
    seen = set()
    for match in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.I | re.DOTALL):
        href = match.group(1).strip()
        anchor = re.sub(r'<[^>]+>', '', match.group(2) or '').strip()
        anchor = html_mod.unescape(anchor) or href
        # 跳过锚点、mailto、javascript
        if href.startswith(('#', 'mailto:', 'javascript:', 'tel:')):
            continue
        full_url = urljoin(base_url, href)
        if full_url not in seen:
            seen.add(full_url)
            links.append({"url": full_url, "text": anchor[:120]})
    return links


def _fetch_page(url: str) -> dict | None:
    """抓取单页 HTML，返回页面数据或 None"""
    try:
        _is_safe_url(url)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
            # 只处理 HTML 内容
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type and "text" not in content_type:
                return None
            raw = resp.read().decode("utf-8", errors="ignore")
            final_url = resp.geturl()

        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', raw, re.I | re.DOTALL)
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip()) if title_match else "(无标题)"

        # 提取正文文本
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL | re.I)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = html_mod.unescape(text)
        if len(text) > 3000:
            text = text[:3000] + "..."

        links = _extract_links(raw, final_url)
        domain = urlparse(final_url).netloc

        return {
            "url": final_url,
            "title": title,
            "domain": domain,
            "text_preview": text,
            "links": [l["url"] for l in links[:30]],
        }
    except Exception:
        return None


@register(
    "web_crawl",
    "爬取网站：从起始 URL 出发，BFS 逐层抓取同一域名下的页面，提取所有链接和正文摘要。用于研究某个网站的结构和内容。",
    {
        "url": {"type": "string", "description": "起始爬取 URL"},
        "max_depth": {"type": "integer", "description": "最大爬取深度（默认 2，1=只爬当前页）"},
        "max_pages": {"type": "integer", "description": "最多爬取页面数（默认 10，最大 20）"},
    }
)
def web_crawl(url: str, max_depth: int = 2, max_pages: int = 10) -> str:
    # 参数安全限制
    max_depth = min(max(max_depth, 1), 3)
    max_pages = min(max(max_pages, 1), 20)

    try:
        _is_safe_url(url)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {e}"}, ensure_ascii=False)

    start_domain = urlparse(url).netloc
    visited: set[str] = set()
    all_links: set[str] = set()
    pages: list[dict] = []

    # BFS 队列: (url, depth)
    queue: list[tuple[str, int]] = [(url, 0)]

    try:
        while queue and len(pages) < max_pages:
            current_url, depth = queue.pop(0)

            if current_url in visited:
                continue
            visited.add(current_url)

            # 礼貌延迟
            if pages:
                time.sleep(1)

            page_data = _fetch_page(current_url)
            if page_data is None:
                continue

            pages.append(page_data)

            # 收集链接，只加入同域名且未访问的
            if depth < max_depth:
                for link_url in page_data["links"]:
                    all_links.add(link_url)
                    if link_url not in visited and urlparse(link_url).netloc == start_domain:
                        queue.append((link_url, depth + 1))

        return json.dumps({
            "start_url": url,
            "domain": start_domain,
            "pages_crawled": len(pages),
            "links_found": len(all_links),
            "pages": pages,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "error": f"爬取异常: {e}",
            "pages_crawled": len(pages),
            "pages": pages,
        }, ensure_ascii=False)
