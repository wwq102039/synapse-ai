"""权威来源扫描器 — 定向搜索政府、教育等权威网站，提取结构化信息。

提供工具：authority_search, authority_extract, institution_profile, policy_tracker
"""
import json
import urllib.request
import urllib.parse
import re
import html as html_mod
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, TimeoutError as FutureTimeoutError
from . import register
from .web_search import _is_safe_url, _baidu_search, _ddg_search, SEARCH_TIMEOUT

# 权威域名库（精简版 — 只搜最关键域名）
AUTHORITY_DOMAINS = {
    "government": ["gov.cn"],
    "education": ["edu.cn"],
}

PROVINCE_MAP = {
    "山东": "shandong", "北京": "beijing", "广东": "guangdong", "江苏": "jiangsu",
    "浙江": "zhejiang", "上海": "shanghai", "四川": "sichuan", "湖北": "hubei",
    "湖南": "hunan", "河南": "henan", "河北": "hebei", "福建": "fujian",
    "安徽": "anhui", "辽宁": "liaoning", "陕西": "shaanxi", "重庆": "chongqing",
    "天津": "tianjin", "山西": "shanxi", "吉林": "jilin", "黑龙江": "heilongjiang",
    "江西": "jiangxi", "广西": "guangxi", "海南": "hainan", "贵州": "guizhou",
    "云南": "yunnan", "西藏": "xizang", "甘肃": "gansu", "青海": "qinghai",
    "宁夏": "ningxia", "新疆": "xinjiang", "内蒙古": "neimenggu",
}

MAX_THREADS = 2       # 并发线程数
GLOBAL_SEARCH_TIMEOUT = 10  # 整个搜索的总超时


def _search_single(query: str, site_filter: str = "") -> list[dict]:
    """搜索单个来源 — 百度优先，site被拒则回退普通搜索，最后DDG"""
    full_query = f"{query} site:{site_filter}" if site_filter else query
    # 1. 百度 site: 搜索
    try:
        return _baidu_search(full_query)
    except Exception:
        pass
    # 2. site: 被拒，尝试百度普通搜索
    if site_filter:
        try:
            return _baidu_search(query)
        except Exception:
            pass
    # 3. DDG 最后备用
    try:
        return _ddg_search(full_query)
    except Exception:
        return []


def _concurrent_search(queries: list[tuple[str, str, str]]) -> list[dict]:
    """并发执行多个搜索，带全局超时。超时后不等待卡住的线程。"""
    all_results = []

    def _do_search(query, domain, label):
        try:
            results = _search_single(query, domain)
            for r in results:
                r["source_category"] = label
            return results
        except Exception:
            return []

    executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
    try:
        futures = {executor.submit(_do_search, q, d, l): (q, d, l) for q, d, l in queries}
        done, not_done = wait(futures, timeout=GLOBAL_SEARCH_TIMEOUT)
        for future in done:
            try:
                all_results.extend(future.result(timeout=2))
            except Exception:
                continue
    finally:
        # wait=False: 不等待卡在网络请求里的线程，直接返回
        executor.shutdown(wait=False)

    seen = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique


@register(
    "authority_search",
    "定向搜索权威网站。并发搜索 gov.cn（政府）、edu.cn（教育）等权威域名，"
    "提取官方政策、公告、数据。自动识别查询中的省份并进行省级网站搜索。"
    "适用于查找官方录取线、政策文件、统计数据等权威信息。执行快速（<10秒）。",
    {
        "query": {"type": "string", "description": "搜索关键词，如'2026年山东省春季高考技能拔尖人才人数'"},
        "source_type": {"type": "string", "description": "来源类型：government（政府）/ education（教育）/ all（全部），默认 all"},
    }
)
def authority_search(query: str, source_type: str = "all") -> str:
    try:
        # 构建搜索任务列表
        search_tasks = []

        if source_type in ("government", "all"):
            for domain in AUTHORITY_DOMAINS["government"]:
                search_tasks.append((query, domain, "政府权威来源"))

        if source_type in ("education", "all"):
            for domain in AUTHORITY_DOMAINS["education"]:
                search_tasks.append((query, domain, "教育权威来源"))

        # 检测查询中的省份关键词，针对性地搜索该省政府网站
        for prov_name, prov_pinyin in PROVINCE_MAP.items():
            if prov_name in query or (prov_pinyin and prov_pinyin in query.lower()):
                search_tasks.append((query, f"{prov_pinyin}.gov.cn", f"{prov_name}省级政府来源"))
                break  # 只搜检测到的第一个省份

        # 如果没有检测到具体省份，搜索最核心的 gov.cn
        if not any("省级政府" in t[2] for t in search_tasks) and source_type in ("government", "all"):
            pass  # 已经在上面加了 gov.cn

        # 并发执行所有搜索
        unique = _concurrent_search(search_tasks)

        return json.dumps({
            "query": query,
            "source_type": source_type,
            "total_results": len(unique),
            "results": unique[:12],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"权威来源搜索失败: {str(e)}"})


@register(
    "authority_extract",
    "从权威网页中提取结构化信息。专门解析政府公告、政策文件、招生简章等，"
    "自动识别并提取日期、政策编号、关键条款、联系方式等重要信息。",
    {
        "url": {"type": "string", "description": "权威页面的URL，如政府公告、招生简章链接"},
    }
)
def authority_extract(url: str) -> str:
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

        if len(text) > 8000:
            text = text[:8000]

        dates = re.findall(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?', text)
        extracted_dates = [f"{y}-{m.zfill(2)}-{d.zfill(2)}" for y, m, d in dates[:5]]

        policy_ids = re.findall(r'([一-鿿]+〔\d{4}〕\d+号)', text)
        phones = re.findall(r'(?:电话|咨询电话|联系电话|招生办)[：:]\s*([\d\-+]+)', text)
        emails = re.findall(r'[\w.\-]+@[\w.\-]+\.\w+', text)
        numbers_of_interest = re.findall(
            r'(\d{3,4})\s*(?:分|名|人|万元|元|%|％|个|所|项)', text
        )

        return json.dumps({
            "url": url,
            "content_preview": text[:2000],
            "content_length": len(text),
            "extracted": {
                "dates": extracted_dates,
                "policy_ids": policy_ids,
                "phones": phones[:5],
                "emails": emails[:5],
                "key_numbers": numbers_of_interest[:10],
            }
        }, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": f"安全阻止: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"信息提取失败: {str(e)}"})


@register(
    "institution_profile",
    "获取特定机构的综合画像。并发搜索该机构的多维度信息：官方网站、简介概况、"
    "排名数据、最新动态等，生成结构化的机构画像报告。支持大学、政府部门的综合画像。",
    {
        "name": {"type": "string", "description": "机构名称，如'四川大学'、'广东省教育厅'"},
        "category": {"type": "string", "description": "机构类型：university（大学）/ government（政府机构）/ auto（自动识别），默认 auto"},
    }
)
def institution_profile(name: str, category: str = "auto") -> str:
    try:
        profile = {
            "name": name,
            "category": category,
            "official_website": "",
            "overview": "",
            "rankings": "",
            "news": [],
        }

        def _fetch_search(query_hint):
            from .web_search import _get_baidu_opener, _BAIDU_HEADERS, _unverified_urlopen
            encoded = urllib.parse.quote(f"{name} {query_hint}")
            try:
                opener = _get_baidu_opener()
                req = urllib.request.Request(
                    f"https://www.baidu.com/s?wd={encoded}&rn=10",
                    headers={**_BAIDU_HEADERS, "Referer": "https://www.baidu.com/"}
                )
                resp = opener.open(req, timeout=SEARCH_TIMEOUT)
                return resp.read().decode("utf-8", errors="ignore")
            except Exception:
                try:
                    req = urllib.request.Request(
                        f"https://html.duckduckgo.com/html/?q={encoded}",
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    with _unverified_urlopen(req, timeout=SEARCH_TIMEOUT) as resp:
                        return resp.read().decode("utf-8", errors="ignore")
                except Exception:
                    return ""

        def _extract_snippets(html_text):
            snippets = []
            for match in re.finditer(r'class="result__snippet"[^>]*>(.*?)</a>', html_text, re.DOTALL):
                s = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                s = html_mod.unescape(s)
                snippets.append(s)
            # 百度 c-abstract fallback
            if not snippets:
                for match in re.finditer(r'class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>', html_text, re.DOTALL):
                    s = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    s = html_mod.unescape(s)
                    snippets.append(s)
            return snippets

        def _extract_links(html_text):
            links = []
            # 百度 h3.t
            for match in re.finditer(
                r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                html_text, re.DOTALL
            ):
                title = html_mod.unescape(re.sub(r'<[^>]+>', '', match.group(2)).strip())
                links.append({"title": title, "url": match.group(1)})
            # DDG fallback
            if not links:
                for match in re.finditer(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                    html_text, re.DOTALL
                ):
                    title = html_mod.unescape(re.sub(r'<[^>]+>', '', match.group(2)).strip())
                    link = urllib.parse.unquote(match.group(1))
                    links.append({"title": title, "url": link})
            return links

        # 并发执行4个搜索（带全局超时，不等待卡住的线程）
        search_labels = ["官方网站", "简介 概况", "排名 评级", "最新动态 新闻"]
        executor = ThreadPoolExecutor(max_workers=4)
        results_map = {}
        try:
            futures = {executor.submit(_fetch_search, label): label for label in search_labels}
            done, _ = wait(futures, timeout=GLOBAL_SEARCH_TIMEOUT)
            for future in done:
                label = futures.get(future, "")
                try:
                    results_map[label] = future.result(timeout=2)
                except Exception:
                    results_map[label] = ""
        finally:
            executor.shutdown(wait=False)

        # 处理官网
        html_official = results_map.get("官方网站", "")
        links = re.findall(r'href="(https?://[^"]*)"[^>]*>(.*?)</a>', html_official)
        for href, link_text in links:
            clean_text = re.sub(r'<[^>]+>', '', link_text).strip()
            if not profile["official_website"] and (name in clean_text or "官网" in clean_text):
                profile["official_website"] = href

        # 处理概况
        html_overview = results_map.get("简介 概况", "")
        overview_snippets = _extract_snippets(html_overview)
        if overview_snippets:
            profile["overview"] = " | ".join(overview_snippets[:3])

        # 处理排名
        html_ranking = results_map.get("排名 评级", "")
        rank_snippets = _extract_snippets(html_ranking)
        if rank_snippets:
            profile["rankings"] = " | ".join(rank_snippets[:3])

        # 处理新闻
        html_news = results_map.get("最新动态 新闻", "")
        profile["news"] = _extract_links(html_news)[:6]

        return json.dumps(profile, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"机构画像生成失败: {str(e)}"})


@register(
    "policy_tracker",
    "追踪特定领域的政策变化。搜索并对比不同时期的政策文件，分析政策趋势、变化方向和影响。"
    "支持按地区和领域筛选，适用于教育政策、招生政策、就业政策等各领域。",
    {
        "topic": {"type": "string", "description": "政策领域，如'研究生招生政策'、'高考改革'、'就业创业扶持'"},
        "region": {"type": "string", "description": "地区限定，如'全国'、'四川省'、'北京市'，默认全国"},
    }
)
def policy_tracker(topic: str, region: str = "全国") -> str:
    try:
        all_results = []

        gov_domains = ["moe.gov.cn", "gov.cn"]
        for domain in gov_domains:
            try:
                results = _search_single(f"{topic} 政策文件 {region}", domain)
                for r in results:
                    r["source"] = domain
                all_results.extend(results)
            except Exception:
                continue

        if region != "全国":
            prov_pinyin = PROVINCE_MAP.get(region)
            if prov_pinyin:
                try:
                    results = _search_single(f"{topic} 政策 {region}", f"{prov_pinyin}.gov.cn")
                    for r in results:
                        r["source"] = f"{prov_pinyin}.gov.cn"
                    all_results.extend(results)
                except Exception:
                    pass

        seen = set()
        unique = []
        for r in all_results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)

        policy_keywords = {
            "招生": ["录取", "分数线", "名额", "计划", "报名", "考试"],
            "教育": ["改革", "新课标", "素质教育", "双��", "教学质量"],
            "就业": ["创业", "补贴", "扶持", "培训", "招聘", "岗位"],
            "考试": ["高考", "中考", "考研", "国考", "省考", "报名时间"],
        }

        matched_category = "general"
        for cat, keywords in policy_keywords.items():
            for kw in keywords:
                if kw in topic:
                    matched_category = cat
                    break

        return json.dumps({
            "topic": topic,
            "region": region,
            "policy_category": matched_category,
            "total_documents": len(unique),
            "documents": unique[:12],
            "analysis_note": (
                f"共找到 {len(unique)} 条与'{topic}'相关的政策文件。"
                f"政策类别: {matched_category}。"
                "请根据搜索结果中的具体信息进行进一步的趋势分析。"
            ),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"政策追踪失败: {str(e)}"})
