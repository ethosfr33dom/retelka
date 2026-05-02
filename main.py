import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from groq import Groq

app = FastAPI()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """
Ты голосовой агент. Отвечай только живой разговорной речью на русском.
Коротко, естественно, без списков, без markdown, без ремарок.
Твоя цель — звучать естественно и кратко.
"""

@app.get("/")
async def root():
    return {"ok": True}

@app.websocket("/llm-websocket")
async def llm_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            req = await ws.receive_json()
            interaction_type = req.get("interaction_type")
            if interaction_type == "update_only":
                continue

            transcript = req.get("transcript", [])
            response_id = req.get("response_id", 0)

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for turn in transcript:
                role = "assistant" if turn.get("role") == "agent" else "user"
                messages.append({"role": role, "content": turn.get("content", "")})

            completion = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=messages,
                temperature=0.4,
                max_tokens=180,
            )

            text = completion.choices[0].message.content.strip()

            await ws.send_json({
                "response_id": response_id,
                "content": text,
                "content_complete": True,
                "end_call": False
            })
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await ws.send_json({
                "response_id": 0,
                "content": "Извините, связь прервалась. Давайте попробуем позже.",
                "content_complete": True,
                "end_call": True
            })
        except Exception:
            pass