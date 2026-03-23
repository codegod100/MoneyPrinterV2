import requests
import time

from config import (
    get_llm_provider,
    get_ollama_base_url,
    get_zai_api_base_url,
    get_zai_api_key,
    get_zai_model,
)

_selected_model: str | None = None


def _provider() -> str:
    return str(get_llm_provider() or "local_ollama").lower()


def _ollama_client():
    import ollama

    return ollama.Client(host=get_ollama_base_url())


def _zai_chat_url() -> str:
    return get_zai_api_base_url().rstrip("/") + "/chat/completions"


def list_models() -> list[str]:
    """
    Lists available models for the configured LLM provider.

    Returns:
        models (list[str]): Sorted list of model names.
    """
    provider = _provider()

    if provider == "local_ollama":
        response = _ollama_client().list()
        return sorted(m.model for m in response.models)

    if provider == "zai_glm":
        return [get_zai_model()]

    raise RuntimeError(f"Unsupported llm_provider: {provider}")


def select_model(model: str) -> None:
    """
    Sets the model to use for all subsequent generate_text calls.

    Args:
        model (str): A provider-specific model name.
    """
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    """
    Returns the currently selected model, or None if none has been selected.
    """
    return _selected_model


def _generate_text_ollama(prompt: str, model: str) -> str:
    response = _ollama_client().chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


def _generate_text_zai(prompt: str, model: str) -> str:
    api_key = get_zai_api_key()
    if not api_key:
        raise RuntimeError("ZAI_API_KEY is not configured.")

    last_error = None
    for attempt in range(2):
        try:
            response = requests.post(
                _zai_chat_url(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=(30, 300),
            )
            response.raise_for_status()

            payload = response.json()
            try:
                return payload["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Unexpected Z.ai response payload: {payload}") from exc
        except requests.exceptions.ReadTimeout as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2)
                continue
            raise RuntimeError(
                "Z.ai request timed out while waiting for the model response. "
                "Try again; the prompt may have been unusually slow."
            ) from exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("Z.ai request failed without a response.")


def generate_text(prompt: str, model_name: str = None) -> str:
    """
    Generates text using the configured LLM provider.

    Args:
        prompt (str): User prompt
        model_name (str): Optional model name override

    Returns:
        response (str): Generated text
    """
    provider = _provider()
    model = model_name or _selected_model
    if not model:
        raise RuntimeError(
            "No model selected. Call select_model() first or pass model_name."
        )

    if provider == "local_ollama":
        return _generate_text_ollama(prompt, model)

    if provider == "zai_glm":
        return _generate_text_zai(prompt, model)

    raise RuntimeError(f"Unsupported llm_provider: {provider}")
