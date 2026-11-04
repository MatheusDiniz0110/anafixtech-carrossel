"""Camada única de LLM. Troque de provedor só mudando LLM_PROVIDER no .env (claude | gemini)."""
import os
import time
import requests

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
# Copie o ID exato do modelo Flash/Flash-Lite com cota gratuita em aistudio.google.com
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def _gemini(system: str, msgs: list[dict], max_tokens: int) -> str:
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    corpo = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in msgs
        ],
        "generationConfig": {"maxOutputTokens": max_tokens, "responseMimeType": "application/json"},
    }
    for espera in (0, 15, 45, 90):  # backoff para 429 do plano gratuito
        time.sleep(espera)
        r = requests.post(url, json=corpo, headers={"x-goog-api-key": key}, timeout=120)
        if r.status_code == 429:
            continue
        r.raise_for_status()
        partes = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in partes)
    raise RuntimeError("Gemini: limite gratuito atingido (429). Tente mais tarde ou use menos posts por semana.")


def _claude(system: str, msgs: list[dict], max_tokens: int) -> str:
    from anthropic import Anthropic
    r = Anthropic().messages.create(model=CLAUDE_MODEL, max_tokens=max_tokens, system=system, messages=msgs)
    return "".join(b.text for b in r.content if b.type == "text")


def completar(system: str, msgs: list[dict], max_tokens: int = 3000) -> str:
    return (_gemini if PROVIDER == "gemini" else _claude)(system, msgs, max_tokens)
