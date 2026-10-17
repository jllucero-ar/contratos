"""Tests de truncamiento y tokens por proveedor. Sin llamadas reales: los SDK se mockean."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core import ia_client


def test_anthropic_truncada(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    resp = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"a":')],
        stop_reason="max_tokens",
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )
    with patch("anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = resp
        r = ia_client._llamar_anthropic("p", "s", 100)
    assert r["truncada"] is True
    assert r["tokens"] == {"entrada": 10, "salida": 20}


def test_anthropic_completa(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    resp = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="{}")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=1, output_tokens=2),
    )
    with patch("anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = resp
        r = ia_client._llamar_anthropic("p", "s", 100)
    assert r["truncada"] is False


def test_openai_truncada(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="{"), finish_reason="length")],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=6),
    )
    with patch("openai.OpenAI") as cls:
        cls.return_value.chat.completions.create.return_value = resp
        r = ia_client._llamar_openai("p", "s", 100)
    assert r["truncada"] is True
    assert r["tokens"] == {"entrada": 5, "salida": 6}


def test_gemini_truncada(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    resp = SimpleNamespace(
        text="{",
        candidates=[SimpleNamespace(finish_reason="FinishReason.MAX_TOKENS")],
        usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=4),
    )
    with patch("google.genai.Client") as cls:
        cls.return_value.models.generate_content.return_value = resp
        r = ia_client._llamar_gemini("p", "s", 100)
    assert r["truncada"] is True
    assert r["tokens"] == {"entrada": 3, "salida": 4}


def test_max_tokens_desde_env(monkeypatch):
    monkeypatch.setenv("IA_MAX_TOKENS", "1234")
    assert ia_client._max_tokens_env() == 1234
    monkeypatch.setenv("IA_MAX_TOKENS", "basura")
    assert ia_client._max_tokens_env() == ia_client.MAX_TOKENS_DEFAULT
