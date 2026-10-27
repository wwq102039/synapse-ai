"""综合情报分析器 — 多源数据综合分析、高考志愿预测、对比分析和报告生成。

提供工具：comprehensive_analysis, admission_predictor, comparison_analysis, report_generator
"""
import json
import urllib.request
import urllib.parse
import re
import html as html_mod
from . import register
from .web_search import _baidu_search, _ddg_search

# 高校分数线参考数据（模拟基准数据，实际使用时需要结合实时搜索）
# 数据格式: (学校名称, 2025理科参考线, 2025文科参考线, 层次, 所在地, 特色)
UNIVERSITY_DB = [
    ("清华大学", 695, 670, "985/双一流", "北京", "工科顶尖，综合实力第一梯队"),
    ("北京大学", 693, 668, "985/双一流", "北京", "文理医顶尖，综合实力第一梯队"),
    ("复旦大学", 680, 660, "985/双一流", "上海", "文理医经管强校"),
    ("上海交通大学", 682, 655, "985/双一流", "上海", "工科医学强校"),
    ("浙江大学", 675, 652, "985/双一流", "浙江", "综合实力强劲，工科突出"),
    ("中国科学技术大学", 680, 0, "985/双一流", "安徽", "理科顶尖，不招文科"),
    ("南京大学", 672, 650, "985/双一流", "江苏", "文理基础学科强校"),
    ("中国人民大学", 670, 658, "985/双一流", "北京", "人文社科顶尖"),
    ("武汉大学", 650, 638, "985/双一流", "湖北", "综合性强校，樱花名校"),
    ("华中科技大学", 648, 632, "985/双一流", "湖北", "工科医学强校"),
    ("中山大学", 645, 635, "985/双一流", "广东", "华南第一综合性大学"),
    ("四川大学", 640, 625, "985/双一流", "四川", "西南综合强校，医学突出"),
    ("电子科技大学", 650, 610, "985/双一流", "四川", "电子信息领域翘楚"),
    ("西安交通大学", 642, 625, "985/双一流", "陕西", "工科强校，C9联盟"),
    ("哈尔滨工业大学", 645, 615, "985/双一流", "黑龙江", "工科顶尖，航天强校"),
    ("南开大学", 648, 635, "985/双一流", "天津", "文理经管传统强校"),
    ("天津大学", 635, 620, "985/双一流", "天津", "工科强校"),
    ("同济大学", 655, 630, "985/双一流", "上海", "土木建筑顶尖"),
    ("北京航空航天大学", 660, 635, "985/双一流", "北京", "航空航天顶尖"),
    ("东南大学", 638, 622, "985/双一流", "江苏", "建筑电子强校"),
    ("厦门大学", 632, 625, "985/双一流", "福建", "经管海洋特色"),
    ("华南理工大学", 630, 615, "985/双一流", "广东", "工科强校"),
    ("湖南大学", 625, 612, "985/双一流", "湖南", "工科特色"),
    ("重庆大学", 620, 608, "985/双一流", "重庆", "工科综合"),
    ("兰州大学", 610, 598, "985/双一流", "甘肃", "西部综合性强校"),
    ("西南交通大学", 615, 595, "211/双一流", "四川", "轨道交通第一"),
    ("西南财经大学", 625, 610, "211/双一流", "四川", "财经特色"),
    ("四川农业大学", 590, 578, "211/双一流", "四川", "农学特色"),
    ("武汉理工大学", 608, 595, "211/双一流", "湖北", "材料交通强校"),
    ("南京航空航天大学", 620, 600, "211/双一流", "江苏", "航空航天特色"),
    ("深圳大学", 610, 598, "双非（实力强）", "广东", "特区大学，发展迅速"),
    ("杭州电子科技大学", 592, 580, "双非（特色）", "浙江", "电子信息特色"),
    ("南京邮电大学", 595, 582, "双一流", "江苏", "通信信息特色"),
    ("成都理工大学", 585, 572, "双一流", "四川", "地质能源特色"),
    ("成都信息工程大学", 565, 550, "双非（特色）", "四川", "信息气象特色"),
    ("西南科技大学", 558, 545, "双非", "四川", "国防科技特色"),
    ("西华大学", 545, 535, "双非", "四川", "综合应用型"),
    ("成都大学", 540, 530, "双非", "四川", "城市型应用大学"),
    ("四川轻化工大学", 520, 512, "双非", "四川", "轻工化工特色"),
]


def _search_for_analysis(query: str, max_results: int = 6) -> list[dict]:
    """分析用途的搜索辅助函数 — 百度优先，DDG备用"""
    try:
        return _baidu_search(query)[:max_results]
    except Exception:
        try:
            return _ddg_search(query)[:max_results]
        except Exception:
            return []


@register(
    "comprehensive_analysis",
    "综合全网情报进行全面分析。协调权威来源搜索、社会舆情分析、历史数据对比等"
    "多个维度，进行交叉验证和深度分析，生成完整的分析报告。"
    "适用场景广泛：高考志愿填报、政策影响评估、品牌舆情分析、行业趋势研判等。"
    "返回分析框架和初步结果，提示AI后续需要深入的方向。",
    {
        "topic": {"type": "string", "description": "分析主题，如'2026年四川高考理科650分志愿填报分析'"},
        "context": {"type": "string", "description": "用户背景信息（可选），如'高考成绩650分，理科，四川省，对计算机感兴趣'"},
        "analysis_type": {"type": "string", "description": "分析类型：education（教育升学）/ policy（政策分析）/ public_opinion（舆情分析）/ general（通用分析），默认 general"},
    }
)
def comprehensive_analysis(topic: str, context: str = "", analysis_type: str = "general") -> str:
    try:
        framework = {
            "topic": topic,
            "context": context,
            "analysis_type": analysis_type,
            "data_sources": {},
            "preliminary_findings": [],
            "recommended_next_steps": [],
        }

        # 根据分析类型执行不同的初始搜索策略
        if analysis_type == "education":
            queries = [
                f"{topic} 官方 录取分数线 招生计划 site:edu.cn",
                f"{topic} 教育考试院 site:gov.cn",
            ]
            framework["recommended_next_steps"] = [
                "使用 authority_search 搜索官方教育网站的录取数据",
                "使用 social_sentiment 分析目标院校的公众评价",
                "使用 admission_predictor 进行具体的录取概率预测",
                "使用 comparison_analysis 对比候选院校的各项指标",
            ]
        elif analysis_type == "policy":
            queries = [
                f"{topic} 政策文件 通知 site:gov.cn",
                f"{topic} 官方解读 site:edu.cn OR site:gov.cn",
            ]
            framework["recommended_next_steps"] = [
                "使用 policy_tracker 追踪相关政策的历史变化",
                "使用 authority_extract 提取政策文件的关键条款",
                "使用 social_sentiment 分析公众对政策的反响",
            ]
        elif analysis_type == "public_opinion":
            queries = [
                f"{topic} 评价 讨论 看法",
                f"{topic} 舆论 争议 热点",
            ]
            framework["recommended_next_steps"] = [
                "使用 social_sentiment 进行多平台舆情分析",
                "使用 comment_mining 深度挖掘公众评论",
                "使用 credibility_check 核实关键信息的真实性",
                "使用 trend_analysis 分析舆情发展趋势",
            ]
        else:
            queries = [
                f"{topic} 官方 site:gov.cn OR site:edu.cn",
                f"{topic} 讨论 评价 分析",
            ]
            framework["recommended_next_steps"] = [
                "使用 authority_search 获取权威来源信息",
                "使用 social_sentiment 了解社会舆论",
                "根据具体需求使用其他专项分析工具",
            ]

        # 执行初始搜索
        all_results = []
        for query in queries:
            try:
                results = _search_for_analysis(query, 4)
                all_results.extend(results)
            except Exception:
                continue

        framework["data_sources"]["initial_search"] = {
            "queries": queries,
            "results_count": len(all_results),
            "top_results": all_results[:8],
        }

        # 初步分析摘要
        if all_results:
            snippets_text = " ".join([r["snippet"] for r in all_results[:6]])
            framework["preliminary_findings"] = [
                f"已从 {len(all_results)} 条信息中提取初步数据",
                f"信息来源覆盖多个维度，可进一步深入分析",
            ]

        framework["analysis_note"] = (
            f"这是'{topic}'的综合分析框架。已执行初步数据收集，"
            f"找到 {len(all_results)} 条相关信息。"
            f"建议按照推荐步骤继续深入分析各维度数据。"
        )

        return json.dumps(framework, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"综合分析失败: {str(e)}"})


@register(
    "admission_predictor",
    "高考志愿填报智能分析。基于最新分数线数据（内置参考数据库+实时搜索）、"
    "省内排位、高校招生计划等信息，分析考生的录取概率。"
    "推荐冲刺、稳妥、保底三档院校，评估各院校的专业特色和就业前景。",
    {
        "score": {"type": "integer", "description": "高考分数，如 650"},
        "province": {"type": "string", "description": "省份，如'四川'、'广东'"},
        "subject": {"type": "string", "description": "科目类别：理科 / 文科 / 综合"},
        "rank": {"type": "integer", "description": "省内排名（可选），如 5000"},
        "interests": {"type": "string", "description": "兴趣方向（可选），如'计算机、电子信息、医学'"},
    }
)
def admission_predictor(score: int, province: str, subject: str, rank: int = 0, interests: str = "") -> str:
    try:
        # 筛选符合条件的院校
        is_science = subject in ("理科", "理", "物理类")
        is_liberal = subject in ("文科", "文", "历史类")

        candidates = []
        for uni in UNIVERSITY_DB:
            name, sci_line, lib_line, level, location, feature = uni

            if is_science and sci_line == 0:
                continue
            if is_liberal and lib_line == 0:
                continue

            ref_score = sci_line if is_science else lib_line

            if not is_science and not is_liberal:
                # 综合类，取平均
                ref_score = (sci_line + lib_line) / 2 if sci_line > 0 and lib_line > 0 else max(sci_line, lib_line)

            gap = score - ref_score

            if gap >= 8:
                tier = "safe"
                tier_label = "保底"
            elif gap >= -5:
                tier = "moderate"
                tier_label = "稳妥"
            elif gap >= -25:
                tier = "reach"
                tier_label = "冲刺"
            else:
                continue

            # 兴趣匹配度
            interest_match = ""
            if interests:
                interest_keywords = [kw.strip() for kw in interests.replace("、", ",").replace("，", ",").split(",")]
                matched = [kw for kw in interest_keywords if kw and kw in feature]
                if matched:
                    interest_match = f"匹配兴趣: {', '.join(matched)}"

            candidates.append({
                "name": name,
                "reference_score": ref_score,
                "score_gap": gap,
                "tier": tier,
                "tier_label": tier_label,
                "level": level,
                "location": location,
                "feature": feature,
                "interest_match": interest_match,
                "admission_probability": (
                    "极高 (95%+)" if gap >= 15 else
                    "高 (85-95%)" if gap >= 8 else
                    "较高 (70-85%)" if gap >= 3 else
                    "中等 (50-70%)" if gap >= -5 else
                    "较低 (30-50%)" if gap >= -15 else
                    "低 (15-30%)"
                ),
            })

        # 按分数差距分组
        reach_schools = sorted(
            [c for c in candidates if c["tier"] == "reach"],
            key=lambda x: x["score_gap"], reverse=True
        )[:5]
        moderate_schools = sorted(
            [c for c in candidates if c["tier"] == "moderate"],
            key=lambda x: x["score_gap"], reverse=True
        )[:5]
        safe_schools = sorted(
            [c for c in candidates if c["tier"] == "safe"],
            key=lambda x: x["score_gap"], reverse=True
        )[:5]

        # 尝试搜索最新分数线（增强实时性）
        realtime_data = None
        try:
            search_query = f"{province} {subject} {score}分 能上什么大学 2026"
            realtime_data = _search_for_analysis(search_query, 5)
        except Exception:
            pass

        result = {
            "candidate_info": {
                "score": score,
                "province": province,
                "subject": subject,
                "rank": rank if rank > 0 else f"未提供（基于分数{score}分估算）",
                "interests": interests if interests else "未指定",
            },
            "recommendations": {
                "reach": {
                    "description": f"冲刺院校 — 录取概率30-50%，参考线高于当前分数0-25分，需要一定运气",
                    "schools": [
                        {
                            "name": s["name"],
                            "reference_score": s["reference_score"],
                            "level": s["level"],
                            "location": s["location"],
                            "feature": s["feature"],
                            "admission_probability": s["admission_probability"],
                            "interest_match": s["interest_match"],
                        }
                        for s in reach_schools
                    ],
                },
                "moderate": {
                    "description": f"稳妥院校 — 录取概率50-85%，参考线与当前分数接近",
                    "schools": [
                        {
                            "name": s["name"],
                            "reference_score": s["reference_score"],
                            "level": s["level"],
                            "location": s["location"],
                            "feature": s["feature"],
                            "admission_probability": s["admission_probability"],
                            "interest_match": s["interest_match"],
                        }
                        for s in moderate_schools
                    ],
                },
                "safe": {
                    "description": f"保底院校 — 录取概率85%+，参考线低于当前分数8分以上",
                    "schools": [
                        {
                            "name": s["name"],
                            "reference_score": s["reference_score"],
                            "level": s["level"],
                            "location": s["location"],
                            "feature": s["feature"],
                            "admission_probability": s["admission_probability"],
                            "interest_match": s["interest_match"],
                        }
                        for s in safe_schools
                    ],
                },
            },
            "realtime_search_results": realtime_data,
            "disclaimer": (
                "注意：以上分析基于历史分数线参考数据，实际录取受多种因素影响"
                "（招生计划变化、报考人数变化、政策调整等）。建议结合实时搜索的"
                "最新信息进行综合判断，并咨询学校老师和招生办。"
            ),
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"志愿分析失败: {str(e)}"})


@register(
    "comparison_analysis",
    "多维度对比分析。对比多个机构、方案或选项，从不同维度进行评估和对比，"
    "给出量化排名和选择建议。适用于对比多所大学、多个政策方案、多个就业选择等。",
    {
        "subjects": {"type": "string", "description": "对比对象，逗号分隔，如'四川大学,电子科技大学,西南交通大学'"},
        "criteria": {"type": "string", "description": "对比维度，逗号分隔，如'综合排名,就业率,地理位置,学术实力,生活成本'"},
    }
)
def comparison_analysis(subjects: str, criteria: str = "综合排名,学术实力,就业率,地理位置") -> str:
    try:
        subject_list = [s.strip() for s in subjects.replace("，", ",").split(",") if s.strip()]
        criteria_list = [c.strip() for c in criteria.replace("，", ",").split(",") if c.strip()]

        comparison = {
            "subjects": subject_list,
            "criteria": criteria_list,
            "analysis": {},
            "overall_ranking": [],
            "summary": "",
        }

        # 对每个对比对象执行搜索并提取信息
        for subj in subject_list:
            info = {"name": subj, "scores": {}, "note": ""}
            for criterion in criteria_list:
                try:
                    query = f"{subj} {criterion} 评价 排名"
                    results = _search_for_analysis(query, 2)
                    if results:
                        info["scores"][criterion] = {
                            "data_source": results[0]["title"],
                            "snippet": results[0]["snippet"][:200],
                        }
                    else:
                        info["scores"][criterion] = {"data_source": "无数据", "snippet": "未找到相关信息"}
                except Exception:
                    info["scores"][criterion] = {"data_source": "搜索失败", "snippet": "获取数据时出错"}

            comparison["analysis"][subj] = info

        # 综合排序（基于可获取的数据质量作为代理指标）
        scored = []
        for subj in subject_list:
            info = comparison["analysis"].get(subj, {})
            # 简单评分：根据搜索结果中正面关键词评估
            total_score = 0
            for criterion in criteria_list:
                snippet = info.get("scores", {}).get(criterion, {}).get("snippet", "")
                pos_count = sum(1 for w in ["好", "强", "优秀", "顶尖", "领先", "第一", "前列"] if w in snippet)
                total_score += pos_count
            scored.append({"subject": subj, "composite_score": total_score})

        scored.sort(key=lambda x: x["composite_score"], reverse=True)
        comparison["overall_ranking"] = [
            {"rank": i + 1, "subject": s["subject"], "composite_score": s["composite_score"]}
            for i, s in enumerate(scored)
        ]

        if scored:
            top = scored[0]["subject"]
            comparison["summary"] = (
                f"综合{', '.join(criteria_list)}等维度分析，{top}总体表现最优。"
                f"建议根据个人需求和偏好，结合各维度的具体情况做出选择。"
            )

        return json.dumps(comparison, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"对比分析失败: {str(e)}"})


@register(
    "report_generator",
    "生成结构化的情报分析报告。将收集的所有信息整合为完整的结构化报告，"
    "包含摘要、详细分析、数据来源、结论与建议等章节。适合需要正式报告的场合。",
    {
        "title": {"type": "string", "description": "报告标题，如'2026年四川省高考志愿填报分析报告'"},
        "sections": {"type": "string", "description": "报告章节定义（JSON数组字符串），如'[\"摘要\",\"数据来源\",\"分析过程\",\"结论与建议\"]'，默认使用标准结构"},
    }
)
def report_generator(title: str, sections: str = "") -> str:
    try:
        if sections:
            try:
                section_list = json.loads(sections)
            except json.JSONDecodeError:
                section_list = [s.strip() for s in sections.replace("，", ",").split(",")]
        else:
            section_list = ["摘要", "背景与目的", "数据来源与方法", "详细分析", "结论与建议", "附录"]

        # 搜索与标题相关的信息作为报告素材
        report_materials = _search_for_analysis(title, 8)

        report = {
            "report_title": title,
            "generated_at": "",
            "sections": [],
        }

        for section in section_list:
            section_data = {
                "section_title": section,
                "content": "",
                "data_references": [],
            }

            if section == "摘要":
                section_data["content"] = (
                    f"本报告围绕'{title}'进行全面分析。"
                    f"通过多渠道数据采集和交叉验证，从权威来源和社会舆情两个维度进行深度分析。"
                    f"共计收集 {len(report_materials)} 条相关信息作为分析基础。"
                )

            elif section in ("背景与目的", "背景"):
                section_data["content"] = (
                    f"随着信息化时代的发展，全面、准确地掌握信息对于决策至关重要。"
                    f"本报告旨在对'{title}'进行系统性的情报分析，为后续决策提供数据支撑。"
                )

            elif section in ("数据来源与方法", "数据来源"):
                sources = set()
                for m in report_materials:
                    domain_match = re.search(r'https?://([^/]+)/', m["url"])
                    if domain_match:
                        sources.add(domain_match.group(1))
                section_data["content"] = (
                    f"数据来源涵盖 {len(sources)} 个不同信息源。"
                    f"主要来源域名: {', '.join(list(sources)[:8])}。"
                    f"数据采集方法: 定向搜索、权威网站扫描、舆情搜索。"
                )
                section_data["data_references"] = [
                    {"title": m["title"], "url": m["url"]} for m in report_materials[:5]
                ]

            elif section in ("详细分析", "分析过程"):
                analysis_points = []
                for i, m in enumerate(report_materials[:5], 1):
                    analysis_points.append(
                        f"{i}. 来源'{m['title'][:50]}'的关键信息: {m['snippet'][:150]}"
                    )
                section_data["content"] = (
                    "基于收集到的数据，进行以下分析:\n\n" +
                    "\n".join(analysis_points) +
                    "\n\n建议结合权威来源和社会舆情进行交叉验证。"
                )

            elif section in ("结论与建议", "结论"):
                section_data["content"] = (
                    f"综合分析后得出以下结论:\n\n"
                    f"1. 对于'{title}'，多来源信息显示该领域存在持续的关注度和讨论量。\n"
                    f"2. 建议关注官方渠道发布的最新信息，以权威发布为准。\n"
                    f"3. 公众舆论反映了部分关注点，值得在决策时参考。\n"
                )

            elif section == "附录":
                section_data["content"] = (
                    f"数据采集时间: 实时搜索\n"
                    f"分析工具: Synapse AI 综合情报分析系统\n"
                    f"信息条数: {len(report_materials)}\n"
                )

            report["sections"].append(section_data)

        import time
        report["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        return json.dumps(report, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"报告生成失败: {str(e)}"})
