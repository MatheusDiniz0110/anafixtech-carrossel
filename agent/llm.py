"""Camada única de LLM. Troque de provedor só mudando LLM_PROVIDER no .env (openrouter | gemini | claude)."""
import os
import time
import requests

from . import config as _config  # noqa: F401  (garante que o .env foi carregado)

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
# Pode ser mais de um, separados por vírgula. Confira os IDs com cota gratuita em aistudio.google.com
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest,gemini-flash-lite-latest")  # lista: tenta na ordem
# Pode ser mais de um, separados por vírgula. Todos com preço zero em openrouter.ai/models?max_price=0
# Ordem: qualidade primeiro, velocidade depois. Modelos que devolvem só "reasoning" são pulados automaticamente.
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemma-4-31b-it:free,"
    "nvidia/nemotron-3-ultra-550b-a55b:free,"
    "cohere/north-mini-code:free",
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _provedor() -> str:
    """LLM_PROVIDER explícito; se vazio, escolhe pelo que tem chave configurada."""
    escolhido = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if escolhido:
        return escolhido
    return "openrouter" if os.getenv("OPENROUTER_API_KEY") else "gemini"


PROVIDER = _provedor()


def _openrouter(system: str, msgs: list[dict], max_tokens: int) -> str:
    key = os.environ["OPENROUTER_API_KEY"]
    modelos = [m.strip() for m in OPENROUTER_MODEL.split(",") if m.strip()]
    corpo = {
        "messages": [{"role": "system", "content": system}] + msgs,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anafixtech",
        "X-Title": "AnaFix Carrosseis",
    }
    ultimo = ""
    # 429 = cota; 500/502/503/504 = provedor sobrecarregado (passa sozinho)
    for espera in (0, 15, 45, 90):
        time.sleep(espera)
        for modelo in modelos:
            r = requests.post(OPENROUTER_URL, json={**corpo, "model": modelo}, headers=headers, timeout=300)
            if r.status_code in (429, 500, 502, 503, 504):
                ultimo = f"{modelo}: HTTP {r.status_code} {r.text[:200]}"
                print("  OpenRouter ocupado, tentando de novo...", ultimo)
                continue
            if not r.ok:
                raise RuntimeError(f"OpenRouter {modelo}: HTTP {r.status_code} {r.text[:400]}")
            candidatos = r.json().get("choices") or []
            if not candidatos:
                ultimo = f"{modelo}: resposta vazia {r.text[:200]}"
                continue
            texto = (candidatos[0].get("message") or {}).get("content") or ""
            if not texto.strip():
                # Modelos de raciocínio gastam a cota em "reasoning" e devolvem content vazio.
                ultimo = f"{modelo}: sem conteúdo (só raciocínio)"
                print(f"  {modelo} não devolveu texto, indo para o próximo modelo...")
                continue
            return texto
    raise RuntimeError(f"OpenRouter indisponível após várias tentativas. Último erro: {ultimo}")


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


_PROVEDORES = {"openrouter": _openrouter, "gemini": _gemini, "claude": _claude}


def completar(system: str, msgs: list[dict], max_tokens: int = 3000) -> str:
    try:
        provedor = _PROVEDORES[PROVIDER]
    except KeyError:
        raise RuntimeError(f"LLM_PROVIDER inválido: {PROVIDER!r}. Use openrouter, gemini ou claude.") from None
    return provedor(system, msgs, max_tokens)
