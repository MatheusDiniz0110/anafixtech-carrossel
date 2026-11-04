"""Camada única de LLM. Troque de provedor só mudando LLM_PROVIDER no .env (claude | gemini)."""
import os
import time
import requests

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
# Pode ser mais de um, separados por vírgula. Confira os IDs com cota gratuita em aistudio.google.com
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest,gemini-flash-lite-latest")  # lista: tenta na ordem


def _gemini(system: str, msgs: list[dict], max_tokens: int) -> str:
    key = os.environ["GEMINI_API_KEY"]
    corpo = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in msgs
        ],
        "generationConfig": {"maxOutputTokens": max_tokens, "responseMimeType": "application/json"},
    }
    modelos = [m.strip() for m in GEMINI_MODEL.split(",") if m.strip()]
    ultimo = ""
    # 429 = cota; 500/502/503/504 = servidor do Google sobrecarregado (passa sozinho)
    for espera in (0, 10, 30, 60, 120):
        time.sleep(espera)
        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            r = requests.post(url, json=corpo, headers={"x-goog-api-key": key}, timeout=120)
            if r.status_code in (429, 500, 502, 503, 504):
                ultimo = f"{modelo}: HTTP {r.status_code} {r.text[:200]}"
                print("  Gemini ocupado, tentando de novo...", ultimo)
                continue
            if not r.ok:
                raise RuntimeError(f"Gemini {modelo}: HTTP {r.status_code} {r.text[:400]}")
            cands = r.json().get("candidates") or []
            if not cands:
                ultimo = f"{modelo}: resposta vazia {r.text[:200]}"
                continue
            partes = cands[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in partes)
    raise RuntimeError(f"Gemini indisponível após várias tentativas. Último erro: {ultimo}")


def _claude(system: str, msgs: list[dict], max_tokens: int) -> str:
    from anthropic import Anthropic
    r = Anthropic().messages.create(model=CLAUDE_MODEL, max_tokens=max_tokens, system=system, messages=msgs)
    return "".join(b.text for b in r.content if b.type == "text")


def completar(system: str, msgs: list[dict], max_tokens: int = 3000) -> str:
    return (_gemini if PROVIDER == "gemini" else _claude)(system, msgs, max_tokens)
