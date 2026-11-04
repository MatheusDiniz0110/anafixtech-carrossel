"""Detector de 'cara de IA'. Barato, determinístico, roda antes de qualquer post sair."""
import re

FRASES_PROIBIDAS = [
    "no mundo digital", "no mundo de hoje", "nos dias de hoje", "no cenário atual",
    "revolucion", "desbloqueie", "desbloqueia", "mergulhe", "mergulhar", "jornada",
    "potencialize", "descubra o poder", "você sabia", "voce sabia", "vamos explorar",
    "vamos desvendar", "desvendando", "desvende", "é fundamental", "é essencial",
    "é crucial", "game changer", "level up", "segredo", "incrível", "poderos",
    "ecossistema", "robust", "de forma eficaz", "em resumo", "em conclusão",
    "vale ressaltar", "vale destacar", "é importante destacar", "é importante lembrar",
    "tapeçaria", "transforme", "eleve", "otimize sua", "seamless", "alavanc",
    "o futuro é", "não perca", "imperdível", "dicas valiosas", "guia definitivo",
    "guia completo", "sem mais delongas", "neste carrossel",
    "arraste para o lado", "arrasta pro lado", "salve este post", "salva esse post",
]

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2705\u274C]")
CONTRASTE = re.compile(r"\bn[ãa]o [eé]\b[^.\n]{1,50}[,;:]?\s+(?:[eé]|mas)\b", re.I)


def _palavras(s: str) -> int:
    return len(s.split())


def lint(post: dict) -> list[str]:
    """Retorna lista de problemas. Lista vazia = passou."""
    probs: list[str] = []
    slides = post.get("slides", [])
    if not 6 <= len(slides) <= 9:
        probs.append(f"Número de slides = {len(slides)}; precisa ficar entre 6 e 9.")

    blocos = []
    for i, s in enumerate(slides, 1):
        blocos.append((f"slide {i} titulo", s.get("titulo", "")))
        blocos.append((f"slide {i} texto", s.get("texto", "")))
        if s.get("tipo") == "codigo" and not s.get("codigo"):
            probs.append(f"slide {i} é do tipo codigo mas está sem código.")
        if _palavras(s.get("texto", "")) > 32:
            probs.append(f"slide {i}: texto com mais de 32 palavras; corte.")
        if _palavras(s.get("titulo", "")) > 14:
            probs.append(f"slide {i}: título com mais de 14 palavras.")
        if EMOJI.search(s.get("titulo", "") + s.get("texto", "")):
            probs.append(f"slide {i}: sem emoji nos slides.")
    blocos.append(("legenda", post.get("legenda", "")))

    for onde, txt in blocos:
        low = txt.lower()
        for f in FRASES_PROIBIDAS:
            if f in low:
                probs.append(f"{onde}: frase de IA '{f}'.")
        if "—" in txt or "–" in txt:
            probs.append(f"{onde}: travessão. Use ponto ou vírgula.")
        if CONTRASTE.search(txt):
            probs.append(f"{onde}: construção 'não é X, é Y'. Diga direto o que é.")
        if txt.count("!") > 1:
            probs.append(f"{onde}: exclamação demais.")

    leg = post.get("legenda", "")
    if _palavras(leg) > 110:
        probs.append("legenda com mais de 110 palavras.")
    if len(EMOJI.findall(leg)) > 2:
        probs.append("legenda com mais de 2 emojis.")
    if len(post.get("hashtags", [])) > 6:
        probs.append("mais de 6 hashtags.")
    if slides and slides[-1].get("tipo") != "cta":
        probs.append("o último slide precisa ser do tipo cta.")
    if slides and slides[0].get("tipo") != "capa":
        probs.append("o primeiro slide precisa ser do tipo capa.")
    return probs
