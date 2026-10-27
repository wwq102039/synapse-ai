"""Synapse AI 大脑 - 基于 DeepSeek 的智能决策核心。"""
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
import httpx
from tools import get_all_tools, get_tool_schemas, get_tool

SYSTEM_PROMPT = """你是 **Synapse AI**，一个知识渊博的 AI 助手。你拥有广泛的训练知识，可以回答大多数问题。

## 核心原则：先用知识，再用工具

1. **默认直接回答。** 对于分析、预测、建议、解释、知识类问题，直接用你的训练知识回答。
   例如："预测今年人数" → 直接分析趋势和数据模式，给出合理推测。
2. **仅在必须验证实时事实时才用工具。** 例如：今天的股价、某校官网的确切公告链接。
3. **工具失败 = 立即放弃工具。** 如果 web_search 返回空或报错，说明目标数据未公开索引。
   不要反复换词重试。直接说"官方未公开发布该数据，以下是我的分析推测"然后回答。

## 关键规则：

- **绝不连续调用 web_search 超过 1 次。**
- **web_fetch 只用于抓取已知确切 URL。** 不要猜测 NewsID 参数。
- 完成后，用清晰有帮助的方式总结回复。
- **默认用中文回复**。
- 像一个聪明的助手一样自然回复，不要让用户等待。

## 可用工具：
{tool_descriptions}
"""


@dataclass
class Thought:
    type: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class SynapseBrain:

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
        self.thoughts: list[Thought] = []
        self.tools = get_all_tools()
        self.tool_schemas = get_tool_schemas()
        self._cached_tool_descriptions: str | None = None

    def _build_tool_descriptions(self) -> str:
        if self._cached_tool_descriptions is None:
            lines = []
            for t in self.tools:
                params_desc = ", ".join(
                    f"{k} ({v.get('description', v.get('type', 'str'))})"
                    for k, v in t.params.items()
                )
                lines.append(f"- **{t.name}**({params_desc}): {t.description}")
            self._cached_tool_descriptions = "\n".join(lines)
        return self._cached_tool_descriptions

    def _thought_to_dict(self, t: Thought) -> dict:
        return {
            "type": t.type, "content": t.content,
            "timestamp": t.timestamp, "metadata": t.metadata,
        }

    def _build_result(self, content: str) -> dict:
        return {
            "response": content,
            "thoughts": [self._thought_to_dict(t) for t in self.thoughts],
            "tool_calls_count": sum(1 for t in self.thoughts if t.type == "tool_call"),
            "timestamp": datetime.now().isoformat(),
        }

    def _build_messages(self, user_message: str, history: list[dict] | None) -> list[dict]:
        messages = [{
            "role": "system",
            "content": SYSTEM_PROMPT.format(tool_descriptions=self._build_tool_descriptions())
        }]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _is_tool_failure(self, result: str) -> bool:
        """判断工具结果是否失败/空"""
        try:
            data = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return False
        # error 字段
        if data.get("error"):
            return True
        # authority_search: total_results=0
        if "total_results" in data and data.get("total_results", 0) == 0:
            return True
        # web_search: results=[]（空列表）
        if isinstance(data.get("results"), list) and len(data.get("results", [])) == 0:
            # 但有 content 的不算（web_fetch 有 content 无 results）
            if not data.get("content"):
                return True
        return False

    async def think(self, user_message: str, history: list[dict] = None) -> dict:
        """非流式处理（REST API fallback 用）"""
        self.thoughts = []
        self._add_thought("thinking", f"用户提问: {user_message[:100]}")

        messages = self._build_messages(user_message, history)
        response = await self._call_deepseek(messages, tools=self.tool_schemas)

        max_turns = 3
        web_search_count = 0
        total_failures = 0
        for turn in range(max_turns):
            choice = response.get("choices", [{}])[0]
            msg = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "stop")

            # 强制收手: 连续失败太多，最后一次无工具调用
            if total_failures >= 2 and finish_reason == "tool_calls":
                messages.append({
                    "role": "user",
                    "content": "请现在基于你已有的知识和搜索结果，直接给出完整回答。不要调用任何工具。"
                })
                response = await self._call_deepseek(messages, tools=[])
                final_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                self._add_thought("response", final_content[:200])
                return self._build_result(final_content)

            if finish_reason == "tool_calls":
                tool_calls = msg.get("tool_calls", [])
                messages.append(msg)

                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    tool_args = json.loads(tc["function"]["arguments"])
                    self._add_thought("tool_call", f"调用工具: {tool_name}",
                                      {"name": tool_name, "args": tool_args})

                    # 硬限制: web_search 最多调用1次
                    if tool_name == "web_search":
                        web_search_count += 1
                        if web_search_count > 1:
                            result = json.dumps({
                                "error": "搜索不可用。请改用 web_fetch 抓取已知官网或直接回答用户。",
                                "results": []
                            }, ensure_ascii=False)
                            total_failures += 1
                            self._add_thought("tool_result", result[:500],
                                              {"name": tool_name, "full_length": len(result)})
                            messages.append({
                                "role": "tool", "tool_call_id": tc["id"], "content": result,
                            })
                            continue

                    tool = get_tool(tool_name)
                    if tool:
                        result = await tool.execute(**tool_args)
                    else:
                        result = json.dumps({"error": f"未知工具: {tool_name}"})

                    if self._is_tool_failure(result):
                        total_failures += 1

                    self._add_thought("tool_result", result[:500],
                                      {"name": tool_name, "full_length": len(result)})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                response = await self._call_deepseek(messages)

            elif finish_reason == "stop":
                final_content = msg.get("content", "")
                self._add_thought("response", final_content[:200])
                return self._build_result(final_content)

            else:
                break

        # 循环耗尽：强制一次无工具最终调用
        messages.append({
            "role": "user",
            "content": "请现在基于你已有的知识和搜索结果，直接给出完整回答。不要调用任何工具。"
        })
        response = await self._call_deepseek(messages, tools=[])
        final_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        self._add_thought("response", final_content[:200])
        return self._build_result(final_content)

    async def think_stream(self, user_message: str, history: list[dict] = None):
        """流式处理 — 异步生成器，实时产出事件。

        Yield 事件类型:
          {"type": "thought", "data": {...}}
          {"type": "token", "content": "..."}
          {"type": "done", "data": {...}}
        """
        self.thoughts = []
        self._add_thought("thinking", f"用户提问: {user_message[:100]}")
        yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}

        messages = self._build_messages(user_message, history)

        max_turns = 3
        web_search_count = 0
        total_failures = 0
        for turn in range(max_turns):
            collected_content = ""
            collected_tool_calls: list[dict] = []
            finish_reason = None

            async for chunk in self._call_deepseek_stream(messages):
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")

                if "content" in delta and delta["content"]:
                    collected_content += delta["content"]
                    yield {"type": "token", "content": delta["content"]}

                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        while len(collected_tool_calls) <= idx:
                            collected_tool_calls.append({
                                "id": "", "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        if "id" in tc and tc["id"]:
                            collected_tool_calls[idx]["id"] = tc["id"]
                        if "function" in tc:
                            if "name" in tc["function"] and tc["function"]["name"]:
                                collected_tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                            if "arguments" in tc["function"]:
                                collected_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

            # 强制收手: 连续失败太多，最后一次无工具调用确保产出回复
            if total_failures >= 2 and finish_reason == "tool_calls":
                messages.append({
                    "role": "user",
                    "content": "请现在基于你已有的知识和搜索结果，直接给出完整回答。不要调用任何工具。"
                })
                async for chunk in self._call_deepseek_stream(messages, tools=[]):
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        collected_content += delta["content"]
                        yield {"type": "token", "content": delta["content"]}
                self._add_thought("response", collected_content[:200])
                yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}
                yield {"type": "done", "data": self._build_result(collected_content)}
                return

            if finish_reason == "tool_calls" and collected_tool_calls:
                assistant_msg = {
                    "role": "assistant",
                    "content": collected_content or None,
                    "tool_calls": collected_tool_calls,
                }
                messages.append(assistant_msg)

                for tc in collected_tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        tool_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}

                    self._add_thought("tool_call", f"调用工具: {tool_name}",
                                      {"name": tool_name, "args": tool_args})
                    yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}

                    # 硬限制: web_search 最多调用1次
                    if tool_name == "web_search":
                        web_search_count += 1
                        if web_search_count > 1:
                            result = json.dumps({
                                "error": "已多次搜索均未找到相关信息。"
                                         "请改用 web_fetch 直接访问 sdzk.cn、gov.cn 等已知官方网站，"
                                         "或基于你的知识直接回答用户。不要再调用 web_search。",
                                "results": []
                            }, ensure_ascii=False)
                            total_failures += 1
                            self._add_thought("tool_result", result[:500],
                                              {"name": tool_name, "full_length": len(result)})
                            yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result,
                            })
                            continue

                    tool = get_tool(tool_name)
                    if tool:
                        result = await tool.execute(**tool_args)
                    else:
                        result = json.dumps({"error": f"未知工具: {tool_name}"})

                    if self._is_tool_failure(result):
                        total_failures += 1

                    self._add_thought("tool_result", result[:500],
                                      {"name": tool_name, "full_length": len(result)})
                    yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

            elif finish_reason == "stop":
                self._add_thought("response", collected_content[:200])
                yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}
                yield {"type": "done", "data": self._build_result(collected_content)}
                return
            else:
                break

        # 循环耗尽：强制一次无工具最终调用
        messages.append({
            "role": "user",
            "content": "请现在基于你已有的知识和搜索结果，直接给出完整回答。不要调用任何工具。"
        })
        final_content = ""
        async for chunk in self._call_deepseek_stream(messages, tools=[]):
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if "content" in delta and delta["content"]:
                final_content += delta["content"]
                yield {"type": "token", "content": delta["content"]}
        self._add_thought("response", final_content[:200])
        yield {"type": "thought", "data": self._thought_to_dict(self.thoughts[-1])}
        yield {"type": "done", "data": self._build_result(final_content)}

    async def _call_deepseek(self, messages: list[dict], tools: list | None = None) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if tools is not None:
            payload["tools"] = tools
        resp = await self.client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            error_text = resp.text[:500]
            raise Exception(f"DeepSeek API 错误 {resp.status_code}: {error_text}")
        return resp.json()

    async def _call_deepseek_stream(self, messages: list[dict], tools: list | None = None):
        """流式调用 DeepSeek API，逐块 yield JSON。tools=None 时禁用工具。"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": True,
        }
        if tools is not None:
            payload["tools"] = tools
        async with self.client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                error_text = (await resp.aread()).decode()[:500]
                raise Exception(f"DeepSeek API 错误 {resp.status_code}: {error_text}")
            async for line in resp.aiter_lines():
                line = line.strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    def _add_thought(self, typ: str, content: str, metadata: dict = None):
        self.thoughts.append(Thought(
            type=typ, content=content,
            metadata=metadata or {}
        ))
