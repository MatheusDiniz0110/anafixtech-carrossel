"""Renderiza os slides em JPEG 1080x1350 (o Instagram só aceita JPEG pela API)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from . import config as C

M = 90  # margem


def font(nome: str, tam: int):
    p = C.FONTS_DIR / nome
    if p.exists():
        return ImageFont.truetype(str(p), tam)
    return ImageFont.load_default(size=tam)


def wrap(d, texto, f, largura):
    linhas = []
    for par in texto.split("\n"):
        atual = ""
        for w in par.split():
            t = (atual + " " + w).strip()
            if d.textlength(t, font=f) <= largura:
                atual = t
            else:
                if atual:
                    linhas.append(atual)
                atual = w
        linhas.append(atual)
    return linhas


def caber(d, texto, nome, tam_max, tam_min, largura, altura, espaco=1.3):
    """Maior fonte em que o texto cabe na caixa."""
    for tam in range(tam_max, tam_min - 1, -2):
        f = font(nome, tam)
        linhas = wrap(d, texto, f, largura)
        if len(linhas) * tam * espaco <= altura:
            return f, linhas, tam
    f = font(nome, tam_min)
    return f, wrap(d, texto, f, largura), tam_min


def desenhar(d, linhas, f, tam, x, y, cor, espaco=1.3):
    for ln in linhas:
        d.text((x, y), ln, font=f, fill=cor)
        y += tam * espaco
    return y


def moldura(d, n, total, ultimo):
    d.text((M, 70), C.BRAND, font=font("Inter-Bold.otf", 34), fill=FG_ACC)
    d.text((C.W - M, 70), f"{n:02d}/{total:02d}", font=font("Inter-Regular.otf", 30),
           fill=C.MUTED, anchor="ra")
    d.rectangle([M, C.H - 118, C.W - M, C.H - 116], fill=(30, 38, 54))
    if not ultimo:
        d.text((C.W - M, C.H - 90), "→", font=font("Inter-Bold.otf", 44), fill=C.ACCENT, anchor="ra")
    d.text((M, C.H - 86), f"{C.HANDLE}  ·  {C.CITY}", font=font("Inter-Regular.otf", 28), fill=C.MUTED)


FG_ACC = C.ACCENT


def slide(s: dict, n: int, total: int) -> Image.Image:
    img = Image.new("RGB", (C.W, C.H), C.BG)
    d = ImageDraw.Draw(img)
    tipo = s.get("tipo", "texto")
    moldura(d, n, total, ultimo=(n == total))
    caixa_w = C.W - 2 * M
    topo, base = 190, C.H - 170

    if tipo == "capa":
        f, ln, tam = caber(d, s["titulo"], "Inter-Bold.otf", 112, 64, caixa_w, 620, 1.18)
        h = len(ln) * tam * 1.18
        y = (topo + base) / 2 - h / 2 - 60
        d.rectangle([M, y - 40, M + 90, y - 34], fill=C.ACCENT)
        y = desenhar(d, ln, f, tam, M, y, C.FG, 1.18)
        if s.get("texto"):
            f2, ln2, t2 = caber(d, s["texto"], "Inter-Regular.otf", 42, 30, caixa_w, 260)
            desenhar(d, ln2, f2, t2, M, y + 40, C.MUTED)

    elif tipo == "cta":
        f, ln, tam = caber(d, s["titulo"], "Inter-Bold.otf", 84, 52, caixa_w, 420, 1.2)
        y = desenhar(d, ln, f, tam, M, topo + 60, C.FG, 1.2)
        if s.get("texto"):
            f2, ln2, t2 = caber(d, s["texto"], "Inter-Regular.otf", 42, 30, caixa_w, 300)
            y = desenhar(d, ln2, f2, t2, M, y + 36, C.MUTED)
        d.rounded_rectangle([M, y + 60, C.W - M, y + 200], radius=28, fill=C.ACCENT)
        d.text((C.W / 2, y + 130), f"WhatsApp  {C.WHATSAPP_TEXT}", font=font("Inter-Bold.otf", 48),
               fill=(255, 255, 255), anchor="mm")

    else:  # texto | codigo
        f, ln, tam = caber(d, s["titulo"], "Inter-Bold.otf", 76, 44, caixa_w, 330, 1.2)
        y = desenhar(d, ln, f, tam, M, topo, C.FG, 1.2) + 30
        if tipo == "codigo" and s.get("codigo"):
            cod = s["codigo"].strip("\n")
            n_lin = len(cod.split("\n"))
            ctam = 38
            while ctam > 24 and (max(len(l) for l in cod.split("\n")) * ctam * 0.6 > caixa_w - 70):
                ctam -= 2
            fc = font("DejaVuSansMono.ttf", ctam)
            altura = n_lin * ctam * 1.45 + 60
            d.rounded_rectangle([M, y, C.W - M, y + altura], radius=22, fill=C.CODE_BG)
            cy = y + 30
            for l in cod.split("\n"):
                d.text((M + 35, cy), l, font=fc, fill=(163, 196, 255))
                cy += ctam * 1.45
            y += altura + 36
        if s.get("texto"):
            f2, ln2, t2 = caber(d, s["texto"], "Inter-Regular.otf", 56, 30, caixa_w, base - y)
            desenhar(d, ln2, f2, t2, M, y, (205, 212, 225), 1.4)
    return img


def renderizar(post: dict, pasta: Path) -> list[Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    total = len(post["slides"])
    saidas = []
    for i, s in enumerate(post["slides"], 1):
        p = pasta / f"slide_{i:02d}.jpg"
        slide(s, i, total).save(p, "JPEG", quality=92, subsampling=0)
        saidas.append(p)
    return saidas
