"""Transforma um carrossel já gerado em vídeo vertical 1080x1920 (Reels/TikTok/Shorts) com narração.
Tudo gratuito: texto pelo modelo de IA (opcional), voz pelo edge-tts (sem chave), montagem com ffmpeg."""
import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path
import imageio_ffmpeg
from PIL import Image
from . import config as C

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOZ = "pt-BR-AntonioNeural"  # alternativas: pt-BR-FranciscaNeural, pt-BR-ThalitaMultilingualNeural
VW, VH = 1080, 1920

PROMPT_FALAS = """Você narra um vídeo curto de Instagram/TikTok da {marca}. Abaixo estão os slides de um carrossel.
Escreva a FALA de cada slide, em português do Brasil, como um técnico explicando em voz alta para um conhecido.
Regras: 1 a 2 frases por slide (máx. 28 palavras), frases curtas, sem travessão, sem emoji, sem "não é X, é Y",
sem "neste vídeo", sem "você sabia". Escreva números por extenso quando atrapalharem a leitura. Para comandos, diga
"digite" e leia o comando com naturalidade. No último slide, convide a chamar no WhatsApp, sem pressão.
Responda só com JSON: {{"falas": ["...", ...]}} com exatamente {n} falas, na ordem.

SLIDES:
{slides}"""


def falas_com_llm(slides: list[dict]) -> list[str]:
    from .llm import completar
    txt = "\n".join(f"{i}. [{s['tipo']}] {s.get('titulo','')} | {s.get('texto','')} | {s.get('codigo','')}"
                    for i, s in enumerate(slides, 1))
    bruto = completar("Você escreve falas naturais para vídeos curtos.",
                      [{"role": "user", "content": PROMPT_FALAS.format(marca=C.BRAND, n=len(slides), slides=txt)}], 2000)
    falas = json.loads(re.search(r"\{.*\}", bruto, re.S).group(0))["falas"]
    if len(falas) != len(slides):
        raise ValueError("número de falas diferente do de slides")
    return falas


def falas_simples(slides: list[dict]) -> list[str]:
    """Sem IA: lê título e texto de cada slide."""
    return [". ".join(x for x in (s.get("titulo", ""), s.get("texto", "")) if x) for s in slides]


def _tts_edge(texto: str, destino: Path):
    import edge_tts
    asyncio.run(edge_tts.Communicate(texto, VOZ, rate="+5%").save(str(destino)))
    if not destino.exists() or destino.stat().st_size < 1000:
        raise RuntimeError("edge-tts não devolveu áudio")


def _tts_offline(texto: str, destino: Path):
    """Plano B sem internet: espeak-ng (Linux/Mac) ou voz do sistema via pyttsx3 (Windows: voz Maria pt-BR)."""
    import shutil
    wav = destino.with_suffix(".wav")
    if shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "155", "-w", str(wav), texto], check=True)
    else:
        import pyttsx3
        eng = pyttsx3.init()
        for v in eng.getProperty("voices"):
            if "portug" in (v.name + str(getattr(v, "languages", ""))).lower() or "pt-br" in v.id.lower():
                eng.setProperty("voice", v.id)
                break
        eng.save_to_file(texto, str(wav))
        eng.runAndWait()
    rodar(["-i", str(wav), str(destino)])


def tts(texto: str, destino: Path):
    try:
        _tts_edge(texto, destino)
    except Exception as e:
        print(f"  AVISO: edge-tts falhou ({type(e).__name__}: {e}). Tentando voz offline...")
        try:
            _tts_offline(texto, destino)
        except Exception as e2:
            raise RuntimeError(
                "Nenhuma voz funcionou. Verifique a internet (edge-tts) ou rode: pip install pyttsx3 "
                f"(Windows) / instale o espeak-ng (Linux/Mac). Detalhe: {e2}") from e2


def duracao(arquivo: Path) -> float:
    r = subprocess.run([FFMPEG, "-i", str(arquivo)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def quadro(jpg: Path, destino: Path):
    """Coloca o slide 4:5 no centro de uma tela 9:16."""
    tela = Image.new("RGB", (VW, VH), C.BG)
    img = Image.open(jpg).convert("RGB")
    tela.paste(img, (0, (VH - img.height) // 2 - 40))
    tela.save(destino, "JPEG", quality=92)


def rodar(args: list[str]):
    r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])


def montar(pasta: Path, usar_llm=True, _tts=tts) -> Path:
    meta = json.loads((pasta / "post.json").read_text("utf-8"))
    slides = meta["slides"]
    try:
        falas = falas_com_llm(slides) if usar_llm else falas_simples(slides)
    except Exception as e:
        print(f"  falas por IA falharam ({e}); usando texto dos slides")
        falas = falas_simples(slides)
    meta["falas"] = falas
    (pasta / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        segs = []
        for i, fala in enumerate(falas, 1):
            jpg = pasta / f"slide_{i:02d}.jpg"
            q, mp3, seg = tmp / f"q{i}.jpg", tmp / f"a{i}.mp3", tmp / f"s{i}.mp4"
            quadro(jpg, q)
            _tts(fala, mp3)
            dur = duracao(mp3) + 0.5
            rodar(["-loop", "1", "-framerate", "30", "-i", str(q), "-i", str(mp3),
                   "-t", f"{dur:.2f}", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                   "-r", "30", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-af", "apad", str(seg)])
            segs.append(seg)
            print(f"  slide {i}/{len(falas)} ok ({dur:.1f}s)")
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), "utf-8")
        saida = pasta / "video.mp4"
        rodar(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(saida)])
    return saida
