"""Synapse AI 工具注册中心 — AI 大脑的感知器官。

通过 @register 装饰器注册工具，自动生成 OpenAI Function Calling 兼容的 schema。
"""
import json
from typing import Any, Callable


class Tool:
    """工具封装类：名称、描述、参数schema、执行函数"""

    def __init__(self, name: str, description: str, func: Callable, params: dict):
        self.name = name            # 工具名称（英文，用于函数调用匹配）
        self.description = description  # 工具描述（中文）
        self.func = func            # 实际执行函数
        self.params = params        # 参数schema：{参数名: {type, description}}

    def to_openai_schema(self) -> dict:
        """生成 OpenAI Function Calling 兼容的 JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.params,
                    "required": list(self.params.keys()),
                }
            }
        }

    async def execute(self, **kwargs) -> str:
        """异步执行工具函数，返回JSON字符串"""
        result = self.func(**kwargs)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, indent=2)


# 全局工具注册表
_tools: dict[str, Tool] = {}


def register(name: str, description: str, params: dict):
    """装饰器：将函数注册为AI可用工具

    Args:
        name: 工具名称（如 'weather', 'web_search'）
        description: 工具描述（中文，供AI理解工具用途）
        params: 参数定义字典
    """
    def decorator(func: Callable):
        _tools[name] = Tool(name, description, func, params)
        return func
    return decorator


def get_all_tools() -> list[Tool]:
    """获取所有已注册的工具"""
    return list(_tools.values())


def get_tool(name: str) -> Tool | None:
    """根据名称查找工具"""
    return _tools.get(name)


def get_tool_schemas() -> list[dict]:
    """获取所有工具的 OpenAI Function Calling schema 列表"""
    return [t.to_openai_schema() for t in _tools.values()]


# 导入所有工具模块，触发 @register 装饰器注册
from . import filesystem     # 文件操作：读/写/列表/搜索
from . import web_search     # 网页工具：搜索/抓取
from . import code_executor  # 代码执行：Python沙箱
from . import calculator     # 数学计算
from . import system_info    # 系统信息：CPU/内存/磁盘
from . import database_query # 数据库：SQLite查询 + 键值记忆
from . import text_processor # 文本处理：分析/转换
from . import weather        # 天气查询
from . import web_crawler    # 网页爬虫
from . import authority_scanner    # 权威来源扫描器
from . import social_sentiment     # 社会舆情分析器
from . import intelligence_analyzer  # 综合情报分析器
from .security import scanner, web_vuln, info_gather, hash_crack  # 安全工具集
