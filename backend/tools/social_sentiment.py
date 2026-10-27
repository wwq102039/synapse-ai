"""社会舆情分析器 — 分析社交平台公众舆论、情感倾向、趋势和可信度。

提供工具：social_sentiment, trend_analysis, comment_mining, credibility_check
"""
import json
import urllib.request
import urllib.parse
import re
import html as html_mod
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from . import register
from .web_search import _baidu_search, _ddg_search

SEARCH_TIMEOUT = 5
MAX_THREADS = 5

# 中文情感词典
POSITIVE_WORDS = [
    "好", "优秀", "推荐", "赞", "满意", "喜欢", "很棒", "厉害", "牛", "强",
    "一流", "顶尖", "出色", "不错", "值得", "认可", "肯定", "支持", "好评",
    "良心", "靠谱", "实用", "方便", "便宜", "性价比高", "权威", "专业",
    "安全", "放心", "可靠", "公正", "公平", "透明", "进步", "提升", "改善",
    "火", "热门", "受欢迎", "抢手", "紧缺", "前景好", "高薪", "好就业",
    "美丽", "优质", "舒适", "温馨", "周到", "热情", "便捷", "高效",
]

NEGATIVE_WORDS = [
    "差", "烂", "坑", "骗", "假", "黑", "垃圾", "失望", "后悔", "不建议",
    "差评", "投诉", "举报", "曝光", "维权", "虚假", "欺诈", "陷阱", "套路",
    "贵", "不值", "浪费", "坑人", "忽悠", "骗人", "虚假宣传", "名不副实",
    "难", "困难", "难考", "难进", "竞争激烈", "内卷", "就业难", "失业",
    "脏", "乱", "差劲", "敷衍", "推诿", "扯皮", "不作为", "腐败", "官僚",
    "危险", "不安全", "隐患", "问题", "严重", "恶化", "下降", "退步",
    "差强人意", "糟糕", "离谱", "无语", "恶心", "恶心人",
]

# 各平台搜索关键词
PLATFORM_KEYWORDS = {
    "weixin": ["微信公众号", "微信"],
    "douyin": ["抖音"],
    "xiaohongshu": ["小红书"],
    "weibo": ["微博"],
    "kuaishou": ["快手"],
}


def _search_opinions(topic: str, platform_hint: str = "") -> list[dict]:
    """搜索特定话题的公众讨论"""
    query = f"{topic} {platform_hint} 评价 看法 讨论"
    try:
        results = _baidu_search(query)
    except Exception:
        try:
            results = _ddg_search(query)
        except Exception:
            return []
    for r in results:
        r["platform"] = platform_hint if platform_hint else "综合"
    return results[:6]


def _analyze_sentiment(text: str) -> dict:
    """对文本进行简单的情感分析"""
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)

    if pos_count > neg_count * 1.5:
        sentiment = "正面"
        score = min(0.5 + (pos_count - neg_count) * 0.1, 1.0)
    elif neg_count > pos_count * 1.5:
        sentiment = "负面"
        score = max(0.5 - (neg_count - pos_count) * 0.1, 0.0)
    elif pos_count > neg_count:
        sentiment = "偏正面"
        score = 0.55
    elif neg_count > pos_count:
        sentiment = "偏负面"
        score = 0.45
    else:
        sentiment = "中性"
        score = 0.5

    return {
        "sentiment": sentiment,
        "score": round(score, 2),
        "positive_keywords": [w for w in POSITIVE_WORDS if w in text][:5],
        "negative_keywords": [w for w in NEGATIVE_WORDS if w in text][:5],
    }


@register(
    "social_sentiment",
    "分析社会公众对特定话题的情感倾向。并发搜索多个平台（微信公众号、抖音、小红书、"
    "微博、快手）相关讨论，进行情感分析（正面/负面/中性），提取主要观点和热门话题。"
    "适用于评估某个机构、政策、事件或产品的公众口碑。执行快速（<10秒）。",
    {
        "topic": {"type": "string", "description": "分析主题，如'四川大学口碑'、'2026高考改革看法'"},
        "platform": {"type": "string", "description": "目标平台：all（全部）/ weixin（微信）/ douyin（抖音）/ xiaohongshu（小红书）/ weibo（微博）/ kuaishou（快手），默认 all"},
    }
)
def social_sentiment(topic: str, platform: str = "all") -> str:
    try:
        all_opinions = []
        sentiment_summary = {"正面": 0, "偏正面": 0, "中性": 0, "偏负面": 0, "负面": 0}

        platforms_to_search = (
            list(PLATFORM_KEYWORDS.keys()) if platform == "all" else [platform]
        )

        # 构建并发搜索任务
        search_tasks = []
        for p in platforms_to_search:
            hints = PLATFORM_KEYWORDS.get(p, [p])
            search_tasks.append((topic, hints[0], p))

        def _do_platform_search(topic, hint, platform_name):
            try:
                results = _search_opinions(topic, hint)
                for r in results:
                    analysis = _analyze_sentiment(r["snippet"])
                    r["sentiment_analysis"] = analysis
                return results
            except Exception:
                return []

        executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
        try:
            futures = {executor.submit(_do_platform_search, t, h, p): p for t, h, p in search_tasks}
            done, _ = wait(futures, timeout=SEARCH_TIMEOUT + 4)
            for future in done:
                try:
                    results = future.result(timeout=2)
                    all_opinions.extend(results)
                except Exception:
                    continue
        finally:
            executor.shutdown(wait=False)

        # 统计情感分布
        for o in all_opinions:
            sa = o.get("sentiment_analysis", {})
            sentiment_summary[sa.get("sentiment", "中性")] += 1

        # 提取高频关键词
        all_text = " ".join([o["snippet"] for o in all_opinions])
        keywords = re.findall(r'[一-鿿]{2,4}', all_text)
        keyword_freq = {}
        for kw in keywords:
            if kw not in POSITIVE_WORDS and kw not in NEGATIVE_WORDS:
                keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:15]

        total = sum(sentiment_summary.values()) or 1
        overall = "正面" if sentiment_summary.get("正面", 0) + sentiment_summary.get("偏正面", 0) > total * 0.5 else \
                  "负面" if sentiment_summary.get("负面", 0) + sentiment_summary.get("偏负面", 0) > total * 0.5 else "中性"

        return json.dumps({
            "topic": topic,
            "platform": platform,
            "total_opinions": len(all_opinions),
            "overall_sentiment": overall,
            "sentiment_distribution": {
                k: f"{v}/{total} ({round(v/total*100, 1)}%)"
                for k, v in sentiment_summary.items()
            },
            "hot_keywords": [{"keyword": k, "frequency": v} for k, v in top_keywords],
            "opinions": all_opinions[:12],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"舆情分析失败: {str(e)}"})


@register(
    "trend_analysis",
    "分析某个话题的网络趋势。追踪讨论热度的变化、识别关键传播节点、分析舆论走向。"
    "通过搜索不同时间段的内容，评估话题的热度趋势和未来发展方向。",
    {
        "topic": {"type": "string", "description": "趋势分析主题，如'人工智能专业热度'、'考研人数变化'"},
        "timeframe": {"type": "string", "description": "时间范围：today（今天）/ week（近一周）/ month（近一月），默认 week"},
    }
)
def trend_analysis(topic: str, timeframe: str = "week") -> str:
    try:
        time_hints = {
            "today": "今天 最新",
            "week": "最近一周 2026",
            "month": "2026年 最近"
        }
        time_hint = time_hints.get(timeframe, time_hints["week"])

        results = _search_opinions(f"{topic} {time_hint}")
        sentiment_results = []
        for r in results:
            sentiment = _analyze_sentiment(r["title"] + " " + r["snippet"])
            r["sentiment"] = sentiment
            sentiment_results.append(r)

        hot_indicators = ["热门", "热议", "焦点", "关注", "趋势", "火爆", "爆发", "飙升"]
        hot_count = sum(1 for r in results for hi in hot_indicators if hi in r["title"] + r["snippet"])

        if hot_count >= len(results) * 0.3:
            heat_level = "高热度"
        elif hot_count >= len(results) * 0.1:
            heat_level = "中等热度"
        else:
            heat_level = "一般热度"

        return json.dumps({
            "topic": topic,
            "timeframe": timeframe,
            "heat_level": heat_level,
            "total_discussions": len(results),
            "heat_indicators_count": hot_count,
            "trend_analysis": {
                "direction": "上升" if hot_count >= len(results) * 0.2 else "平稳" if hot_count > 0 else "下降",
                "key_discussions": [
                    {"title": r["title"], "sentiment": r.get("sentiment", {}).get("sentiment", "未知")}
                    for r in sentiment_results[:8]
                ],
            },
            "note": "趋势分析基于可搜索的公开网页内容，实际社交平台数据可能与搜索结果存在差异。",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"趋势分析失败: {str(e)}"})


@register(
    "comment_mining",
    "深度挖掘某个主题的公众评论和反馈。收集多来源的评论、评价和讨论，"
    "提取高频关键词、典型观点、争议焦点、情感分布等深层次信息。",
    {
        "topic": {"type": "string", "description": "评论挖掘主题，如'华为手机用户体验'、'某高校学生评价'"},
        "count": {"type": "integer", "description": "收集信息数量，默认20，最大50"},
    }
)
def comment_mining(topic: str, count: int = 20) -> str:
    try:
        count = min(count, 50)

        search_queries = [
            f"{topic} 评价 体验 感受",
            f"{topic} 优点 缺点 问题",
            f"{topic} 好不好 怎么样 值得吗",
            f"{topic} 吐槽 投诉 表扬 推荐",
        ]

        def _do_comment_search(query):
            try:
                return [r["snippet"] for r in _search_opinions(query)]
            except Exception:
                return []

        executor = ThreadPoolExecutor(max_workers=4)
        try:
            futures = {executor.submit(_do_comment_search, q): q for q in search_queries[:3]}
            all_snippets = []
            done, _ = wait(futures, timeout=SEARCH_TIMEOUT + 4)
            for future in done:
                try:
                    all_snippets.extend(future.result(timeout=2))
                except Exception:
                    continue
        finally:
            executor.shutdown(wait=False)

        analyzed = []
        for snippet in all_snippets[:count]:
            sentiment = _analyze_sentiment(snippet)
            opinions = re.findall(
                r'(?:认为|觉得|感觉|表示|说|指出|评价)[：:]?(.{5,30}?)(?:。|，|但|不过|然而|而且|并且|；|$)',
                snippet
            )
            analyzed.append({
                "text": snippet[:300],
                "sentiment": sentiment["sentiment"],
                "key_opinions": opinions[:3],
            })

        sentiment_counts = {"正面": 0, "偏正面": 0, "中性": 0, "偏负面": 0, "负面": 0}
        for a in analyzed:
            sentiment_counts[a["sentiment"]] = sentiment_counts.get(a["sentiment"], 0) + 1

        all_text = " ".join([a["text"] for a in analyzed])
        controversy_keywords = re.findall(r'(争议|矛盾|分歧|质疑|反对|支持|争论|吐槽|投诉)', all_text)

        return json.dumps({
            "topic": topic,
            "total_analyzed": len(analyzed),
            "sentiment_summary": sentiment_counts,
            "overall_verdict": "好评为主" if sentiment_counts.get("正面", 0) > sentiment_counts.get("负面", 0) * 2
                               else "差评较多" if sentiment_counts.get("负面", 0) > sentiment_counts.get("正面", 0) * 2
                               else "褒贬不一",
            "controversy_signals": list(set(controversy_keywords)),
            "detailed_reviews": analyzed[:15],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"评论挖掘失败: {str(e)}"})


@register(
    "credibility_check",
    "核实信息或声明的真实性。并发交叉验证多个信息来源（官方政府、教育机构、一般辟谣），"
    "区分官方信息与谣言，评估信息的可信度等级。适用于验证'某校今年扩招'、'某政策即将实施'等。",
    {
        "claim": {"type": "string", "description": "待核实的信息或声明，如'四川大学2026年将在四川扩招500人'"},
    }
)
def credibility_check(claim: str) -> str:
    try:
        def _do_search(query_hint):
            try:
                return [{"title": r["title"], "snippet": r["snippet"]}
                        for r in _baidu_search(f"{claim} {query_hint}")]
            except Exception:
                try:
                    return [{"title": r["title"], "snippet": r["snippet"]}
                            for r in _ddg_search(f"{claim} {query_hint}")]
                except Exception:
                    return []

        # 并发执行3个来源的验证搜索
        search_labels = ["官方 公告 site:gov.cn", "site:edu.cn", "真相 辟谣 核实"]
        executor = ThreadPoolExecutor(max_workers=3)
        try:
            futures = {executor.submit(_do_search, label): label for label in search_labels}
            results_map = {}
            done, _ = wait(futures, timeout=SEARCH_TIMEOUT + 4)
            for future in done:
                label = futures.get(future, "")
                try:
                    results_map[label] = future.result(timeout=2)
                except Exception:
                    results_map[label] = []
        finally:
            executor.shutdown(wait=False)

        gov_results = results_map.get(search_labels[0], [])
        edu_results = results_map.get(search_labels[1], [])
        rumor_results = results_map.get(search_labels[2], [])

        official_count = len(gov_results) + len(edu_results)
        rumor_keywords = ["辟谣", "谣言", "不实", "虚假", "澄清", "否认", "假消息", "造谣"]

        is_rumor = any(
            kw in r["title"] + r["snippet"]
            for r in rumor_results for kw in rumor_keywords
        )

        if is_rumor:
            credibility = "低 - 存在辟谣/质疑信息"
            score = 0.2
        elif official_count >= 3:
            credibility = "高 - 多个官方/权威来源支持"
            score = 0.85
        elif official_count >= 1:
            credibility = "中 - 有部分官方来源支持，但需进一步确认"
            score = 0.6
        elif len(rumor_results) > 0:
            credibility = "较低 - 缺乏官方来源，信息未得到充分验证"
            score = 0.35
        else:
            credibility = "无法判断 - 公开信息来源不足"
            score = 0.5

        return json.dumps({
            "claim": claim,
            "credibility": credibility,
            "credibility_score": score,
            "official_sources_found": official_count,
            "government_sources": len(gov_results),
            "education_sources": len(edu_results),
            "is_likely_rumor": is_rumor,
            "official_evidence": [
                {"title": r["title"], "snippet": r["snippet"][:200]}
                for r in (gov_results + edu_results)[:5]
            ],
            "counter_evidence": [
                {"title": r["title"], "snippet": r["snippet"][:200]}
                for r in rumor_results[:3]
            ] if is_rumor else [],
            "verdict": (
                "该信息很可能为虚假/不实信息，请以官方公告为准。"
                if is_rumor else
                "该信息在多个官方来源中得到支持，可信度较高。"
                if official_count >= 3 else
                "该信息有部分官方来源支持，建议进一步核实后使用。"
                if official_count >= 1 else
                "目前公开信息来源不足以验证该声明的真实性，建议持续关注官方发布。"
            ),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"可信度核实失败: {str(e)}"})
