"""
Ollama service — JSON generation with robust error handling.

Thread safety: each thread gets its own ollama.Client() via threading.local()
so parallel chunk processing does not share a connection pool.
"""

import json
import re
import threading

import ollama

_JSON_CODE_BLOCK_PATTERN = re.compile(r"```json|```")
_TRAILING_COMMA_PATTERN = re.compile(r",\s*(\]|\})")

# Thread-local storage so each worker thread gets its own Ollama client
_thread_local = threading.local()

_OLLAMA_TIMEOUT = 300  # seconds — prevents indefinite hangs on slow hardware


def _get_client() -> ollama.Client:
    """Return a per-thread Ollama client, creating one if needed."""
    if not hasattr(_thread_local, "client"):
        _thread_local.client = ollama.Client(timeout=_OLLAMA_TIMEOUT)
    return _thread_local.client


def _extract_json(raw: str) -> str:
    """Extract the first complete JSON object from a string."""
    start = raw.find("{")
    if start == -1:
        return raw

    stack = []
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        c = raw[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            stack.append("}")
        elif c == "[":
            stack.append("]")
        elif c in ("}", "]"):
            if stack and stack[-1] == c:
                stack.pop()
                if not stack:
                    return raw[start:i + 1]
            else:
                continue

    return raw[start:] + "".join(reversed(stack))


def _balance_json(raw: str) -> str:
    """Close any unclosed brackets/braces to salvage truncated JSON."""
    open_braces = raw.count("{") - raw.count("}")
    open_brackets = raw.count("[") - raw.count("]")
    if open_brackets > 0:
        raw += "]" * open_brackets
    if open_braces > 0:
        raw += "}" * open_braces
    return raw


def generate(prompt: str, model: str = "llama3.2", system_prompt: str = None,
             num_ctx: int = 4096, num_predict: int = 2048,
             temperature: float = 0.0) -> str:
    """
    Call Ollama chat with explicit, parameterised options.

    Uses a thread-local Client instance so this function is safe to call
    from multiple threads concurrently (e.g. parallel chunk processing).
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    client = _get_client()
    response = client.chat(
        model=model,
        messages=messages,
        format="json",
        options={
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
        },
    )
    return response["message"]["content"]


def generate_json(prompt: str, model: str = "llama3.2", system_prompt: str = None,
                  num_ctx: int = 4096, num_predict: int = 1024,
                  temperature: float = 0.0,
                  max_retries: int = 1) -> dict:
    """
    Generate a JSON response from Ollama with automatic repair and retry.

    On every failure the prompt is amended with the error and re-sent once.
    If all retries are exhausted, returns {} rather than raising so callers
    can degrade gracefully instead of producing a 500 error.
    """
    full_prompt = prompt + "\n\nRespond only with valid JSON. No markdown."

    last_error: str | None = None

    for attempt in range(1 + max_retries):
        if attempt == 0:
            current_prompt = full_prompt
        else:
            current_prompt = (
                f"Your previous response was not valid JSON. The error was:\n"
                f"{last_error}\n\n"
                f"Please respond again with ONLY valid JSON. No markdown, no explanations.\n\n"
                f"Original request:\n{full_prompt}"
            )

        try:
            raw = generate(
                current_prompt, model, system_prompt,
                num_ctx=num_ctx, num_predict=num_predict,
                temperature=temperature,
            ).strip()
        except Exception as exc:
            print(f"[Ollama] Network/timeout error on attempt {attempt + 1}: {exc}")
            last_error = str(exc)
            if attempt >= max_retries:
                print("[Ollama] All retries exhausted — returning empty dict.")
                return {}
            continue

        raw = _JSON_CODE_BLOCK_PATTERN.sub("", raw).strip()
        raw = _extract_json(raw)
        raw = _TRAILING_COMMA_PATTERN.sub(r"\1", raw)

        print(f"\n========== RAW RESPONSE (attempt {attempt + 1}) ==========")
        print(raw[:2000] + ("..." if len(raw) > 2000 else ""))
        print("==================================\n")

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"\n========== JSON ERROR (attempt {attempt + 1}) ==========")
            print(e)
            print("================================\n")
            last_error = str(e)

            fixed = _balance_json(raw)
            if fixed != raw:
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError as e2:
                    last_error = str(e2)

    # All retries exhausted — return empty dict so agents can apply defaults
    print("[Ollama] JSON parsing failed after all retries — returning empty dict.")
    return {}