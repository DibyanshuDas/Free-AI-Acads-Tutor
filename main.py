"""
Personal AI Question Answerer
-----------------------------
Single endpoint:
  POST /ask  -> takes the full conversation (messages array, OpenAI/OpenRouter
                format) and returns the next assistant reply.

The frontend is responsible for building each message's content:
  - plain text turn:  content = "some text"
  - image/PDF turn:   content = [{"type": "text", "text": "..."},
                                  {"type": "image_url", "image_url": {"url": "data:...base64..."}}, ...]

The backend inspects the conversation: if ANY message (past or current)
contains an image, it routes the whole request to the vision-capable model
so image context is never lost on later text-only follow-ups (e.g. "go to
the next slide"). Otherwise it uses the cheaper text-only model.

Each route (text / vision) now has a fallback CHAIN instead of a single
model. If the primary model's provider returns an error (e.g. NVIDIA
marking a function "DEGRADED", rate limits, timeouts), we automatically
retry the same request on the next model in the chain instead of failing
the whole /ask call.

Setup:
    1. pip install fastapi uvicorn openai python-dotenv
    2. Create a .env file next to this script with:
         OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
    3. Run:  uvicorn main:app --reload
    4. Open the index.html file in your browser
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Personal AI Q&A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# Cap reasoning so a single question can't silently burn thousands of tokens.
MAX_OUTPUT_TOKENS = 1500
REASONING_BUDGET = 2000

# --- Model fallback chains -------------------------------------------------
# First entry in each list is the primary model, used unless it errors out.
# If a request fails (provider error, degraded function, timeout, etc.) we
# move to the next model in the same chain and retry the identical request.
#
# Verified live against https://openrouter.ai/api/v1/models on 2026-07-09.
# Free-tier availability rotates over time (models get added/retired without
# much notice) — if you start seeing 404 "no longer free" errors again,
# re-check that endpoint and swap in whatever's current.

TEXT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "tencent/hy3:free",
]

VISION_MODELS = [
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
]

# Only the nemotron text model understands these extra reasoning params.
# Fallback models get a plain request without this extra_body.
NEMOTRON_TEXT_MODEL = TEXT_MODELS[0]

SYSTEM_PROMPT = (
    "You are a careful tutor answering inside a chat interface. Write in "
    "plain conversational prose, like a message in a chat app — NOT a "
    "formatted document. Do not use markdown headings (no #, ##, ###). "
    "You may use **bold** for a key term and short bullet lists where they "
    "genuinely help, but default to short paragraphs. "
    "Show the key reasoning steps concisely, then give a clear final answer. "
    "If the question is ambiguous, state your assumption briefly and "
    "proceed. For any math, use LaTeX delimiters: $...$ for inline "
    "expressions and $$...$$ for standalone equations, so they render "
    "correctly — never use plain-text approximations like x^2 or unicode "
    "math symbols instead of LaTeX. "
    "If earlier images (e.g. slides or pages) were shared in this "
    "conversation, they remain visible to you in every later turn — treat "
    "them as still in front of you even if the newest message is plain text."
)


class AskRequest(BaseModel):
    messages: List[Dict[str, Any]]  # full conversation, no system prompt


def message_has_image(msg: Dict[str, Any]) -> bool:
    content = msg.get("content")
    if isinstance(content, list):
        return any(part.get("type") == "image_url" for part in content)
    return False


def build_kwargs(model: str, full_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = dict(
        model=model,
        messages=full_messages,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    # Only the primary nemotron text model gets the extra reasoning params —
    # other providers/models don't recognize this extra_body shape.
    if model == NEMOTRON_TEXT_MODEL:
        kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": True},
            "reasoning_budget": REASONING_BUDGET,
        }
    return kwargs


def call_with_fallback(model_chain: List[str], full_messages: List[Dict[str, Any]]):
    """Try each model in model_chain in order, returning the first success.
    Raises the last error if every model in the chain fails."""
    last_error: Optional[Exception] = None
    for model in model_chain:
        try:
            kwargs = build_kwargs(model, full_messages)
            completion = client.chat.completions.create(**kwargs)
            return completion, model
        except Exception as e:
            print(f"[fallback] model '{model}' failed: {e}")
            last_error = e
            continue
    raise last_error


@app.post("/ask")
def ask(payload: AskRequest):
    messages = payload.messages
    conversation_has_images = any(message_has_image(m) for m in messages)
    model_chain = VISION_MODELS if conversation_has_images else TEXT_MODELS

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    try:
        completion, model_used = call_with_fallback(model_chain, full_messages)
    except Exception as e:
        return {"answer": f"(All models in the fallback chain failed. Last error: {e})"}

    print("RAW COMPLETION:", completion)  # debug: remove once things work
    if not completion.choices:
        return {"answer": f"(No answer returned. Raw response: {completion})", "model_used": model_used}
    return {"answer": completion.choices[0].message.content, "model_used": model_used}


@app.get("/health")
def health():
    return {"status": "ok"}
