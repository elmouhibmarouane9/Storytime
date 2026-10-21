import sys
from types import ModuleType, SimpleNamespace

import pytest

from mim import local_ai


def test_rewrite_uses_model_locally_and_preserves_language(monkeypatch):
    calls = {}

    class FakeTokenizer:
        eos_token_id = 2

        @classmethod
        def from_pretrained(cls, model_id, token):
            calls["model_id"] = model_id
            calls["token"] = token
            return cls()

        def apply_chat_template(self, messages, **kwargs):
            calls["messages"] = messages
            return "local prompt"

        def __call__(self, prompt, return_tensors):
            return {"input_ids": FakeTensor([1, 2])}

        def decode(self, generated, skip_special_tokens):
            return "  Una versión más directa.\n"

    class FakeTensor(list):
        def to(self, device):
            return self

        @property
        def shape(self):
            return (1, len(self))

        def __getitem__(self, key):
            if isinstance(key, tuple):
                return FakeTensor(super().__getitem__(key[1]))
            return super().__getitem__(key)

    class FakeModel:
        def to(self, device):
            calls["device"] = device
            return self

        def eval(self):
            pass

        def parameters(self):
            return iter([SimpleNamespace(device="cpu")])

        def generate(self, **inputs):
            return [FakeTensor([1, 2, 3])]

    def load_model(model_id, token, use_safetensors):
        calls["model_token"] = token
        calls["use_safetensors"] = use_safetensors
        return FakeModel()

    fake_torch = ModuleType("torch")
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)
    fake_torch.inference_mode = lambda: __import__("contextlib").nullcontext()
    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoTokenizer = FakeTokenizer
    fake_transformers.AutoModelForCausalLM = SimpleNamespace(
        from_pretrained=load_model
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    local_ai._MODELS.clear()

    result = local_ai.rewrite_body("Texto original", "ES", "public/model")

    assert result == "Una versión más directa."
    assert calls["model_id"] == "public/model"
    assert calls["token"] is False
    assert calls["model_token"] is False
    assert calls["use_safetensors"] is True
    assert calls["messages"][0]["content"].endswith("Spanish. Keep the meaning, names, figures, dates, promises, and next step unchanged. Use a confident, cinematic, direct voice. Do not invent facts. Return only the revised message body.")
    assert calls["messages"][1]["content"] == "Texto original"
    assert calls["device"] == "cpu"
    local_ai._MODELS.clear()


def test_rewrite_reports_missing_optional_dependencies(monkeypatch):
    local_ai._MODELS.clear()
    monkeypatch.setitem(sys.modules, "torch", None)

    with pytest.raises(local_ai.LocalModelError, match="requirements-ai.txt"):
        local_ai.rewrite_body("Draft", "EN")
