"""Synapse AI - FastAPI + WebSocket 后端服务。"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from brain import SynapseBrain
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, SERVER_HOST, SERVER_PORT

app = FastAPI(title="Synapse AI", description="AI 神经大脑工作室 API")

brain = SynapseBrain(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=DEEPSEEK_MODEL,
)

frontend_path = Path(__file__).resolve().parent.parent / "frontend"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ConfigUpdate(BaseModel):
    api_key: str | None = None
    model: str | None = None


@app.get("/api/health")
async def health():
    return {"status": "ok", "name": "Synapse AI 神经大脑"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """REST 聊天端点（WebSocket 不可用时的回退方案）"""
    try:
        result = await brain.think(req.message, req.history)
        return result
    except Exception as e:
        return {
            "response": f"错误：{str(e)}",
            "thoughts": [],
            "tool_calls_count": 0,
            "timestamp": "",
        }


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket 流式端点 — token 级别实时推送。"""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            req = json.loads(data)
            message = req.get("message", "")
            history = req.get("history", [])

            try:
                async for event in brain.think_stream(message, history):
                    await ws.send_json(event)
            except Exception as e:
                await ws.send_json({"type": "response", "data": {
                    "response": f"错误：{str(e)}",
                    "thoughts": [],
                    "tool_calls_count": 0,
                    "timestamp": "",
                }})
    except WebSocketDisconnect:
        pass


@app.get("/api/tools")
async def list_tools():
    tools_info = []
    for t in brain.tools:
        tools_info.append({
            "name": t.name,
            "description": t.description,
            "parameters": t.params,
        })
    return {"tools": tools_info, "count": len(tools_info)}


@app.post("/api/config")
async def update_config(cfg: ConfigUpdate):
    global brain
    if cfg.api_key:
        brain.api_key = cfg.api_key
    if cfg.model:
        brain.model = cfg.model
    return {"status": "ok", "model": brain.model}


# ==================== 前端静态文件服务 ====================

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (frontend_path / "index.html").read_text(encoding="utf-8")

    @app.get("/favicon.ico")
    async def favicon():
        favicon_file = frontend_path / "favicon.ico"
        if favicon_file.exists():
            from fastapi.responses import FileResponse
            return FileResponse(str(favicon_file))
        from fastapi.responses import Response
        return Response(status_code=204)
else:
    print(f"[WARN] 前端路径未找到: {frontend_path}")


if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] 前端路径: {frontend_path} (存在: {frontend_path.exists()})")
    print(f"[INFO] Synapse AI 启动于 http://{SERVER_HOST}:{SERVER_PORT}")
    print("请访问: http://localhost:8765")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
