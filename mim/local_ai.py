"""Optional local-only rewriting for communication drafts."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
INSTALL_HINT = "Install local AI support with `pip install -r requirements-ai.txt`."

_MODELS: dict[str, tuple[Any, Any, Any]] = {}


class LocalModelError(RuntimeError):
    """A local model could not be loaded or used."""


def rewrite_body(body: str, language: str, model_id: str | None = None) -> str:
    """Polish a draft body on this machine; never sends its contents to a service."""
    model_id = (model_id or os.environ.get("MIM_LOCAL_MODEL") or DEFAULT_MODEL).strip()
    if not model_id:
        raise LocalModelError("Set MIM_LOCAL_MODEL to a Hugging Face model ID.")

    if model_id not in _MODELS:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise LocalModelError(INSTALL_HINT) from exc

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, token=False)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                token=False,
                use_safetensors=True,
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            model.eval()
        except Exception as exc:
            raise LocalModelError(f"Could not load local model '{model_id}': {exc}") from exc
        _MODELS[model_id] = (torch, tokenizer, model)

    torch, tokenizer, model = _MODELS[model_id]
    language_name = "Spanish" if language.upper().startswith("ES") else "English"
    messages = [
        {
            "role": "system",
            "content": (
                f"Polish the provided client message in {language_name}. Keep the meaning, "
                "names, figures, dates, promises, and next step unchanged. Use a confident, "
                "cinematic, direct voice. Do not invent facts. Return only the revised message body."
            ),
        },
        {"role": "user", "content": body},
    ]

    try:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output[0][inputs["input_ids"].shape[-1]:]
        result = tokenizer.decode(generated, skip_special_tokens=True).strip()
    except Exception as exc:
        raise LocalModelError(f"Local draft rewrite failed: {exc}") from exc

    if not result:
        raise LocalModelError("The local model returned an empty draft. The original is unchanged.")
    return result
