"""Vídeo explicativo ANIMADO (9:16, 24 fps): texto revelado palavra a palavra, código digitado, botão que 'pula',
fundo em movimento e barra de progresso. Tudo desenhado com Pillow e enviado direto ao ffmpeg. Sem chave, sem custo."""
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from . import config as C
from .render import font, wrap, caber
from .video import FFMPEG, VW, VH, falas_com_llm, falas_simples, tts, duracao, rodar

FPS = 24
M = 80
CT, CB = 300, 1440            # área de conteúdo (evita a interface do Reels no topo e embaixo)
LARG = VW - 2 * M
TRILHA = (30, 38, 54)
CORPO = (205, 212, 225)
CODIGO = (163, 196, 255)


def ease(t):  # desaceleração suave
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pop(t):  # "pulinho" com leve exagero
    t = max(0.0, min(1.0, t))
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def mix(cor, a):
    return tuple(int(C.BG[i] + (cor[i] - C.BG[i]) * max(0.0, min(1.0, a))) for i in range(3))


def fundo_base() -> Image.Image:
    img = Image.new("RGB", (VW, VH), C.BG)
    brilho = ImageOps.invert(Image.radial_gradient("L")).point(lambda v: int(max(0, v - 80) * 255 / 175 * 0.22)).resize((1500, 1500))
    img.paste(Image.new("RGB", (1500, 1500), C.ACCENT), (VW - 1000, -450), brilho)
    return img


PONTOS = [((i * 197) % VW, (i * 331) % VH, 14 + (i * 7) % 22, 4 + (i % 3) * 2) for i in range(16)]


def _palavras(d, texto, f, tam, y0, espaco):
    """Posiciona cada palavra: [(palavra, x, y)]."""
    linhas = wrap(d, texto, f, LARG)
    out, y = [], y0
    for ln in linhas:
        x = M
        for w in ln.split():
            out.append((w, x, y))
            x += d.textlength(w + " ", font=f)
        y += tam * espaco
    return out, y


class Cena:
    def __init__(self, s: dict, dur: float):
        self.s, self.dur = s, dur
        self.tipo = s.get("tipo", "texto")
        d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        t = self.tipo
        self.itens = []  # (kind, dados)
        if t == "capa":
            f, ln, tam = caber(d, s["titulo"], "Inter-Bold.otf", 120, 70, LARG, 760, 1.15)
            h_t = len(ln) * tam * 1.15
            fs, lns, ts = caber(d, s.get("texto", " "), "Inter-Regular.otf", 48, 32, LARG, 300)
            h = h_t + 70 + (len(lns) * ts * 1.3 if s.get("texto") else 0)
            y = CT + (CB - CT - h) / 2 - 40
            self.barra_y = y - 50
            self.tit, y2 = _palavras(d, s["titulo"], f, tam, y, 1.15)
            self.ft = f
            self.sub, _ = _palavras(d, s["texto"], fs, ts, y2 + 50, 1.3) if s.get("texto") else ([], 0)
            self.fs = fs
            self.cor_tit, self.cor_sub = C.FG, C.MUTED
        else:
            f, ln, tam = caber(d, s["titulo"], "Inter-Bold.otf", 84, 50, LARG, 380, 1.2)
            h_t = len(ln) * tam * 1.2
            self.ft = f
            corpo_h = CB - CT - h_t - 60
            if t == "codigo" and s.get("codigo"):
                cod = s["codigo"].strip("\n").split("\n")
                ctam = 44
                while ctam > 24 and max(len(l) for l in cod) * ctam * 0.6 > LARG - 80:
                    ctam -= 2
                self.fc, self.cod, self.ctam = font("DejaVuSansMono.ttf", ctam), cod, ctam
                alt_cod = len(cod) * ctam * 1.5 + 70
                fs, lns, ts = caber(d, s.get("texto", " "), "Inter-Regular.otf", 52, 32, LARG, max(150, corpo_h - alt_cod - 40))
                h_tx = len(lns) * ts * 1.4 if s.get("texto") else 0
                h = h_t + 40 + alt_cod + 40 + h_tx
                y = CT + max(0, (CB - CT - h) / 2) - 30
                self.tit, y2 = _palavras(d, s["titulo"], f, tam, y, 1.2)
                self.cod_y, self.cod_h = y2 + 40, alt_cod
                self.sub, _ = _palavras(d, s["texto"], fs, ts, self.cod_y + alt_cod + 40, 1.4) if s.get("texto") else ([], 0)
                self.fs = fs
            else:
                fs, lns, ts = caber(d, s.get("texto", " "), "Inter-Regular.otf", 60, 34, LARG, max(300, corpo_h))
                h_tx = len(lns) * ts * 1.4 if s.get("texto") else 0
                extra = 200 if t == "cta" else 0
                h = h_t + 50 + h_tx + extra
                y = CT + max(0, (CB - CT - h) / 2) - 40
                self.tit, y2 = _palavras(d, s["titulo"], f, tam, y, 1.2)
                self.sub, y3 = _palavras(d, s["texto"], fs, ts, y2 + 50, 1.4) if s.get("texto") else ([], y2)
                self.fs = fs
                self.btn_y = y3 + 70
            self.cor_tit, self.cor_sub = C.FG, CORPO

    def _revelar(self, d, palavras, fonte, cor, t, ini, span, g):
        n = max(1, len(palavras))
        for k, (w, x, y) in enumerate(palavras):
            a = ease((t - (ini + span * k / n)) / 0.28) * g
            if a > 0.01:
                d.text((x, y + 16 * (1 - ease((t - (ini + span * k / n)) / 0.28))), w, font=fonte, fill=mix(cor, a))

    def desenhar(self, d: ImageDraw.ImageDraw, t: float):
        g = ease(t / 0.3)
        dur = self.dur
        if self.tipo == "capa":
            d.rectangle([M, self.barra_y, M + 120 * ease(t / 0.6), self.barra_y + 8], fill=mix(C.ACCENT, g))
            self._revelar(d, self.tit, self.ft, self.cor_tit, t, 0.1, min(1.4, dur * 0.45), g)
            self._revelar(d, self.sub, self.fs, self.cor_sub, t, min(1.6, dur * 0.55), min(1.2, dur * 0.3), g)
            return
        self._revelar(d, self.tit, self.ft, self.cor_tit, t, 0.1, min(0.8, dur * 0.25), g)
        if self.tipo == "codigo" and getattr(self, "cod", None):
            ini = 0.7
            span = max(1.0, dur * 0.55)
            total = sum(len(l) for l in self.cod)
            mostrar = int(total * max(0.0, min(1.0, (t - ini) / span)))
            a = ease((t - 0.5) / 0.4) * g
            d.rounded_rectangle([M, self.cod_y, VW - M, self.cod_y + self.cod_h], radius=26, fill=mix(C.CODE_BG, a) if a < 1 else C.CODE_BG)
            y, usados = self.cod_y + 35, 0
            for l in self.cod:
                vis = l[: max(0, mostrar - usados)]
                if vis:
                    d.text((M + 40, y), vis, font=self.fc, fill=CODIGO)
                if 0 < mostrar - usados <= len(l) or (usados == 0 and mostrar == 0):
                    cx = M + 40 + d.textlength(vis, font=self.fc)
                    if int(t * 2) % 2 == 0:
                        d.rectangle([cx + 2, y + 4, cx + self.ctam * 0.5, y + self.ctam * 1.15], fill=CODIGO)
                usados += len(l)
                y += self.ctam * 1.5
            self._revelar(d, self.sub, self.fs, self.cor_sub, t, dur * 0.60, min(1.2, dur * 0.3), g)
            return
        self._revelar(d, self.sub, self.fs, self.cor_sub, t, 0.7, max(0.8, dur * 0.65), g)
        if self.tipo == "cta":
            p = pop((t - dur * 0.45) / 0.5)
            if p > 0:
                w, h = LARG * p, 150 * p
                cx, cy = VW / 2, self.btn_y + 75
                d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=30, fill=C.ACCENT)
                if p > 0.9:
                    d.text((cx, cy), f"WhatsApp  {C.WHATSAPP_TEXT}", font=font("Inter-Bold.otf", 50),
                           fill=(255, 255, 255), anchor="mm")


def quadro(base, cena: Cena, t: float, idx: int, total: int, prog: float) -> bytes:
    img = base.copy()
    d = ImageDraw.Draw(img)
    for i, (x, y, r, v) in enumerate(PONTOS):  # pontos que sobem devagar
        yy = (y - (prog * 0 + (idx * 1000 + t * 24) * v / 6)) % VH
        d.ellipse([x - r / 2, yy - r / 2, x + r / 2, yy + r / 2], fill=mix(C.ACCENT, 0.10))
    d.text((M, 120), C.BRAND, font=font("Inter-Bold.otf", 42), fill=C.ACCENT)
    d.text((VW - M, 124), f"{idx + 1:02d}/{total:02d}", font=font("Inter-Regular.otf", 34), fill=C.MUTED, anchor="ra")
    d.rectangle([M, 200, VW - M, 208], fill=TRILHA)
    d.rectangle([M, 200, M + (VW - 2 * M) * prog, 208], fill=C.ACCENT)
    cena.desenhar(d, t)
    d.text((M, 1520), f"{C.HANDLE}  ·  {C.CITY}", font=font("Inter-Regular.otf", 32), fill=C.MUTED)
    return img.tobytes()


def montar_animado(pasta: Path, usar_llm=True, _tts=tts, falas=None) -> Path:
    meta = json.loads((pasta / "post.json").read_text("utf-8"))
    slides = meta["slides"]
    if falas is None:
        try:
            falas = falas_com_llm(slides) if usar_llm else falas_simples(slides)
        except Exception as e:
            print(f"  falas por IA falharam ({e}); usando texto dos slides")
            falas = falas_simples(slides)
    meta["falas"] = falas
    (pasta / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        durs, wavs = [], []
        for i, fala in enumerate(falas, 1):
            mp3 = tmp / f"a{i}.mp3"
            _tts(fala, mp3)
            dur = math.ceil((duracao(mp3) + 0.6) * FPS) / FPS
            w = tmp / f"a{i}.wav"
            rodar(["-i", str(mp3), "-ar", "44100", "-ac", "2", "-af", "apad", "-t", f"{dur:.4f}", str(w)])
            durs.append(dur); wavs.append(w)
            print(f"  voz {i}/{len(falas)} ok ({dur:.1f}s)")
        audio = tmp / "audio.wav"
        with wave.open(str(audio), "wb") as out:
            for k, w in enumerate(wavs):
                with wave.open(str(w), "rb") as r:
                    if k == 0:
                        out.setparams(r.getparams())
                    out.writeframes(r.readframes(r.getnframes()))

        saida = pasta / "video.mp4"
        log = open(tmp / "ffmpeg.log", "w")
        p = subprocess.Popen(
            [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
             "-i", str(audio), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(saida)],
            stdin=subprocess.PIPE, stderr=log)
        base = fundo_base()
        total_t, feito = sum(durs), 0.0
        for i, (s, dur) in enumerate(zip(slides, durs)):
            cena = Cena(s, dur)
            n = round(dur * FPS)
            for f in range(n):
                t = f / FPS
                p.stdin.write(quadro(base, cena, t, i, len(slides), (feito + t) / total_t))
            feito += dur
            print(f"  cena {i + 1}/{len(slides)} animada")
        p.stdin.close()
        if p.wait():
            raise RuntimeError(open(tmp / "ffmpeg.log").read()[-800:])
    return saida
