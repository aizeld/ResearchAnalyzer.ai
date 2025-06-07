import os
import time
import json
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
import httpx

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY env-var required")

HEADERS = {"Authorization": f"Bearer {OPENAI_KEY}"}

app = FastAPI(title="Ollama-style proxy for ChatGPT")

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def ollama_tags_from_openai(models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Преобразуем /v1/models → /api/tags формат Ollama."""
    return {
        "models": [
            {
                "name": m["id"],
                "model": m["id"],
                "modified_at": iso_now(),
                "size": None,
                "digest": None,
                "details": {
                    "parent_model": "",
                    "format": "openai",
                    "family": "openai",
                    "families": ["openai"],
                    "parameter_size": "n/a",
                    "quantization_level": "n/a",
                },
            }
            for m in models
        ]
    }

async def openai(
    path: str,
    *,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    stream: bool = False,
) -> Union[httpx.Response, httpx.AsyncByteStream]:
    """
    Если stream=True, возвращает AsyncByteStream от httpx.AsyncClient.stream().
    Иначе – httpx.Response.
    """
    async with httpx.AsyncClient(timeout=90, base_url=OPENAI_BASE, headers=HEADERS) as cli:
        if method == "GET":
            resp = await cli.get(path)
        elif stream:
            return cli.stream("POST", path, json=payload)
        else:
            resp = await cli.post(path, json=payload)

    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)

    return resp

# ------------------------------------------------------------------
# HEALTHCHECK "/"
# ------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse("Ollama proxy is running", status_code=200)

# ------------------------------------------------------------------
# INFERENCE: /api/generate
# ------------------------------------------------------------------
@app.post("/api/generate")
async def api_generate(request: Request):
    data = await request.json()
    payload = {
        "model": data["model"],
        "prompt": data["prompt"],
        "max_tokens": data.get("options", {}).get("num_predict"),
        "temperature": data.get("options", {}).get("temperature"),
        "stream": bool(data.get("stream")),
    }

    if payload["stream"]:
        stream = await openai("/completions", method="POST", payload=payload, stream=True)

        async def event_stream():
            async with stream as resp_stream:
                async for chunk in resp_stream.aiter_bytes():
                    yield chunk

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    resp_json = (await openai("/completions", method="POST", payload=payload)).json()
    return JSONResponse(
        {
            "model": resp_json["model"],
            "created_at": iso_now(),
            "response": resp_json["choices"][0]["text"],
            "done": True,
        }
    )

@app.post("/v1/completions")
async def v1_completions(request: Request):
    """
    LlamaIndex/Ollama-клиент по умолчанию делает запросы именно на /v1/completions.
    Здесь мы просто «проксируем» его в ту же функцию api_chat().
    """
    # Передаём весь Request дальше в api_chat() без модификаций
    return await api_chat(request)


# ------------------------------------------------------------------
# INFERENCE: /api/cha
@app.post("/api/chat")
async def api_chat(request: Request):
    data = await request.json()
    messages = data.get("messages")
    model = "gpt-4o-mini"  # или любая другая разрешённая модель

    if messages is None:
        raise HTTPException(400, "Field 'messages' is required")

    client_wants_stream = bool(data.get("stream"))

    # ─── 1) STREAM-ВЕТКА ─────────────────────────────────────────────
    if client_wants_stream:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        stream = await openai("/chat/completions", method="POST", payload=payload, stream=True)

        async def event_stream():
            async with stream as resp_stream:
                async for raw_line in resp_stream.aiter_lines():
                    if not raw_line:
                        continue

                    # Каждая линия — в формате SSE: "data: {...}" или "data: [DONE]"
                    if raw_line.startswith("data:"):
                        content = raw_line[len("data:"):].strip()
                        if content == "[DONE]":
                            # Прописываем финальную метку, а потом выходим
                            yield "[DONE]\n"
                            break

                        # Отдаём «чистый» JSON (NDJSON: одна строка = один JSON)
                        # LlamaIndex/Ollama-клиент разберёт его как JSON, 
                        # найдёт внутри поле "choices/.delta/content" 
                        # и правильно соберёт ответ по токенам.
                        yield content + "\n"
                # По выходу из цикла — ничего больше не шлём

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    # ─── 2) NON-STREAM-ВЕТКА ─────────────────────────────────────────
    # Запрос без stream→True к OpenAI
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    resp = await openai("/chat/completions", method="POST", payload=payload)
    resp_json = resp.json()

    # Извлекаем «assistant message»
    assistant_choice = resp_json.get("choices", [])
    if not assistant_choice:
        raise HTTPException(500, "OpenAI response missing 'choices'")

    # Например, OpenAI возвращает:
    # {
    #   "id": "...",
    #   "object": "chat.completion",
    #   "created": 1710000000,
    #   "model": "gpt-4o-mini",
    #   "choices": [
    #     {
    #       "message": {
    #         "role": "assistant",
    #         "content": "Привет, как дела?"
    #       },
    #       "finish_reason": "stop",
    #       "index": 0
    #     }
    #   ]
    # }
    #
    # Но LlamaIndex/Ollama-клиент ожидает, чтобы мы вернули JSON вида:
    # {
    #   "message": { "role":"assistant", "content":"Привет, как дела?" },
    #   "tool_calls": []
    # }
    #
    # Поэтому достаём именно поле `message` из первой choice.

    assistant_message = assistant_choice[0].get("message")
    if assistant_message is None:
        raise HTTPException(500, "OpenAI response missing 'message' in choices[0]")

    # Возвращаем «обёрнутый» ответ, который поймёт LlamaIndex
    return JSONResponse({
        "message": assistant_message,
        "tool_calls": []
    })


# ------------------------------------------------------------------
# INFERENCE: /api/embeddings  (и /api/embed алиас)
# ------------------------------------------------------------------
@app.post("/api/embed", include_in_schema=False)
@app.post("/api/embeddings", include_in_schema=False)
async def api_embed(request: Request):
    data = await request.json()

    # Поддерживаем OpenAI-стиль и Ollama-стиль:
    if "input" in data:
        text_list = data["input"]
    elif "inputs" in data:
        text_list = data["inputs"]
    elif "prompt" in data:
        text_list = [data["prompt"]]
    elif "prompts" in data:
        text_list = data["prompts"]
    else:
        raise HTTPException(400, "Missing 'input' or 'prompt' field")

    # Если строка — оборачиваем в список
    if isinstance(text_list, str):
        text_list = [text_list]

    # ЗАСТАВЛЯЕМ ВСЕГДА text-embedding-3-small → 768-мерные эмбеддинги
    model_openai = "text-embedding-3-small"

    payload = {"model": model_openai, "input": text_list, "dimensions": 768}
    resp = await openai("/embeddings", method="POST", payload=payload)
    resp_json = resp.json()

    # Если один текст — возвращаем {"embedding": [...]}
    if len(text_list) == 1:
        embedding_vector = resp_json["data"][0]["embedding"]
        return JSONResponse({"model": resp_json["model"], "embedding": embedding_vector})

    # Если несколько — возвращаем [{"embedding": [...]}, …]
    out = []
    for item in resp_json["data"]:
        out.append({"embedding": item["embedding"]})
    return JSONResponse({"model": resp_json["model"], "embeddings": out})

# ------------------------------------------------------------------
# MODEL INFO
# ------------------------------------------------------------------
@app.get("/api/tags")
async def api_tags():
    data = {"models":[{"name":"llama3.2:3b","model":"llama3.2:3b","modified_at":"2025-06-03T16:22:53.8203312Z","size":2019393189,"digest":"a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"3.2B","quantization_level":"Q4_K_M"}},{"name":"nomic-embed-text:latest","model":"nomic-embed-text:latest","modified_at":"2024-10-24T17:55:24.103472Z","size":274302450,"digest":"0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f","details":{"parent_model":"","format":"gguf","family":"nomic-bert","families":["nomic-bert"],"parameter_size":"137M","quantization_level":"F16"}},{"name":"llama3.1:latest","model":"llama3.1:latest","modified_at":"2024-10-24T17:53:31.7416903Z","size":4661230766,"digest":"42182419e9508c30c4b1fe55015f06b65f4ca4b9e28a744be55008d21998a093","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"8.0B","quantization_level":"Q4_0"}}]}
    return data

@app.post("/api/show")
async def api_show(request: Request):
    model_name = (await request.json()).get("model")
    if not model_name:
        raise HTTPException(400, "model field required")
    return (await openai(f"/models/{model_name}")).json()

# ------------------------------------------------------------------
# STUBS (операции управления моделями, которых нет в OpenAI)
# ------------------------------------------------------------------
@app.post("/api/pull")
@app.post("/api/create")
@app.post("/api/copy")
@app.delete("/api/delete")
@app.post("/api/stop")
@app.get("/api/ps")
async def not_implemented():
    return PlainTextResponse("Not implemented in OpenAI proxy.", status_code=501)
