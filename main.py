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

Setup:
    1. pip install fastapi uvicorn openai python-dotenv
    2. Create a .env file next to this script with:
         OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
    3. Run:  uvicorn main:app --reload
    4. Open the index.html file in your browser
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from openai.types.chat import ChatCompletion
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

TEXT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

# Free-tier OpenRouter models occasionally hit upstream worker/rate limits
# (e.g. "ResourceExhausted: Worker local total request limit reached").
# These are almost always transient, so we retry a few times with backoff
# before giving up and telling the user plainly what happened.
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 1.5

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


def extract_upstream_error(completion: ChatCompletion) -> Optional[str]:
    """OpenRouter sometimes returns HTTP 200 with every normal field empty
    and the real problem smuggled into an 'error' field instead of raising.
    That's the case that used to leak straight into the frontend as a raw
    ChatCompletion repr. Catch it here instead."""
    err = getattr(completion, "error", None)
    if not err:
        return None
    if isinstance(err, dict):
        return err.get("message") or str(err)
    return str(err)


def is_transient_error(error_text: str) -> bool:
    text = error_text.lower()
    return any(
        marker in text
        for marker in [
            "resourceexhausted",
            "resource exhausted",
            "rate limit",
            "rate_limit",
            "worker local total request limit",
            "502",
            "503",
            "overloaded",
            "timeout",
            "timed out",
        ]
    )


def call_model_with_retry(kwargs: Dict[str, Any]) -> Tuple[Optional[ChatCompletion], Optional[str]]:
    """Calls the model, retrying transient upstream failures with backoff.
    Returns (completion, error_message). error_message is None on success."""
    last_error: Optional[str] = None
    completion: Optional[ChatCompletion] = None

    for attempt in range(MAX_RETRIES):
        try:
            completion = client.chat.completions.create(**kwargs)
        except Exception as exc:  # network errors, timeouts, etc.
            last_error = str(exc)
            if attempt < MAX_RETRIES - 1 and is_transient_error(last_error):
                time.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** attempt))
                continue
            return None, last_error

        upstream_error = extract_upstream_error(completion)
        if upstream_error is None and completion.choices:
            return completion, None  # success

        last_error = upstream_error or "The model returned no answer."
        if attempt < MAX_RETRIES - 1 and is_transient_error(last_error):
            time.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** attempt))
            continue
        return completion, last_error

    return completion, last_error


@app.post("/ask")
def ask(payload: AskRequest):
    messages = payload.messages
    conversation_has_images = any(message_has_image(m) for m in messages)
    model = VISION_MODEL if conversation_has_images else TEXT_MODEL

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    kwargs: Dict[str, Any] = dict(
        model=model,
        messages=full_messages,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    if model == TEXT_MODEL:
        kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": True},
            "reasoning_budget": REASONING_BUDGET,
        }

    completion, error = call_model_with_retry(kwargs)
    print("RAW COMPLETION:", completion, "| ERROR:", error)  # debug: remove once things work

    if error:
        if is_transient_error(error):
            friendly = (
                "The free-tier model is temporarily overloaded on OpenRouter's "
                "side (too many requests hitting it at once). This usually "
                "clears up within a few seconds — please try asking again."
            )
        else:
            friendly = f"The model returned an error and couldn't answer: {error}"
        return {"answer": friendly, "model_used": model, "error": error}

    return {"answer": completion.choices[0].message.content, "model_used": model}


@app.get("/health")
def health():
    return {"status": "ok"}