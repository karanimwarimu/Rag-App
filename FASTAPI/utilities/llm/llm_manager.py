import logging
from litellm import acompletion
from utilities.llm.config_loader import get_llm_config

logger = logging.getLogger("llm_manager")


def _build_messages(prompt: str, context: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the provided context to answer "
                "the user's question accurately and concisely. If the context does "
                "not contain the answer, say so."
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {prompt}",
        },
    ]


async def generate_answer(
    prompt: str, context: str, model_override: str | None = None
) -> str:
    """Non-streaming answer generation. Raises on failure after fallback."""
    cfg = get_llm_config()
    model = model_override or cfg["selected_model"]
    fallback = cfg.get("fallback_model")
    messages = _build_messages(prompt, context)

    try:
        resp = await acompletion(
            model=model,
            messages=messages,
            max_tokens=cfg.get("max_tokens", 1024),
            temperature=cfg.get("temperature", 0.2),
            timeout=cfg.get("timeout_seconds", 30),
            stream=False,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Primary model {model} failed: {e}")
        if fallback:
            try:
                resp = await acompletion(
                    model=fallback,
                    messages=messages,
                    max_tokens=cfg.get("max_tokens", 1024),
                    temperature=cfg.get("temperature", 0.2),
                    timeout=cfg.get("timeout_seconds", 30),
                    stream=False,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e2:
                logger.error(f"Fallback model {fallback} failed: {e2}")
        raise


async def generate_answer_stream(
    prompt: str, context: str, model_override: str | None = None
):
    """Yields answer tokens one at a time (for SSE streaming)."""
    cfg = get_llm_config()
    model = model_override or cfg["selected_model"]
    fallback = cfg.get("fallback_model")
    messages = _build_messages(prompt, context)

    try:
        response = await acompletion(
            model=model,
            messages=messages,
            max_tokens=cfg.get("max_tokens", 1024),
            temperature=cfg.get("temperature", 0.2),
            timeout=cfg.get("timeout_seconds", 30),
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
        return
    except Exception as e:
        logger.warning(f"Primary stream model {model} failed: {e}")
        if fallback:
            try:
                response = await acompletion(
                    model=fallback,
                    messages=messages,
                    max_tokens=cfg.get("max_tokens", 1024),
                    temperature=cfg.get("temperature", 0.2),
                    timeout=cfg.get("timeout_seconds", 30),
                    stream=True,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta
                return
            except Exception as e2:
                logger.error(f"Fallback stream model {fallback} failed: {e2}")
        raise
