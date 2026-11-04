"""
Uso:
  python -m agent.main ideias [--n 20]       # pede temas novos ao Claude e coloca na fila (topics.json)
  python -m agent.main gerar  [--n 3]        # gera N posts da fila, renderiza e deixa em posts/ (status: pendente)
  python -m agent.main publicar              # publica o post mais antigo aprovado
  python -m agent.main listar                # mostra o estado de cada post
"""
import argparse
import json
import re
import unicodedata
from datetime import date
from . import config as C
from .render import renderizar


def slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48]


def ler_fila() -> list[dict]:
    return json.loads(C.TOPICS_FILE.read_text("utf-8")) if C.TOPICS_FILE.exists() else []


def salvar_fila(f):
    C.TOPICS_FILE.write_text(json.dumps(f, ensure_ascii=False, indent=2), "utf-8")


def legenda_final(p: dict) -> str:
    tags = " ".join("#" + h.lstrip("#") for h in p.get("hashtags", []))
    return f"{p['legenda'].strip()}\n\n{tags}".strip()


def cmd_ideias(n: int):
    from .generate import novas_ideias
    fila = ler_fila()
    novas = novas_ideias(n, [t["tema"] for t in fila])
    fila += [{**i, "usado": False} for i in novas]
    salvar_fila(fila)
    print(f"{len(novas)} temas adicionados.")


def cmd_gerar(n: int):
    from .generate import gerar_post
    fila = ler_fila()
    feitos = 0
    for item in fila:
        if feitos >= n:
            break
        if item.get("usado"):
            continue
        print(f"Gerando: {item['tema']}")
        post, probs = gerar_post(item["tema"], item.get("angulo", ""))
        if not post.get("slides"):
            print("  falhou, pulando"); continue
        pasta = C.POSTS_DIR / f"{date.today():%Y%m%d}-{slug(item['tema'])}"
        renderizar(post, pasta)
        revisar = bool(probs or post.get("incertezas"))
        meta = {
            "tema": item["tema"], "status": "pendente", "precisa_revisao": revisar,
            "problemas_restantes": probs, "incertezas": post.get("incertezas", []),
            "legenda": legenda_final(post), "slides": post["slides"], "instagram_id": None,
        }
        (pasta / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")
        item["usado"] = True
        feitos += 1
        print("  pronto" + (" (precisa revisão humana)" if revisar else ""))
    salvar_fila(fila)


def _posts():
    return sorted(p for p in C.POSTS_DIR.glob("*/post.json"))


def cmd_listar():
    for p in _posts():
        m = json.loads(p.read_text("utf-8"))
        rev = " [REVISAR]" if m["precisa_revisao"] else ""
        print(f"{p.parent.name:55} {m['status']}{rev}")


def cmd_publicar():
    from .instagram import publicar_carrossel
    for p in _posts():
        m = json.loads(p.read_text("utf-8"))
        liberado = m["status"] == "aprovado" or (
            C.AUTO_APPROVE and m["status"] == "pendente" and not m["precisa_revisao"])
        if not liberado:
            continue
        base = C.public_base_url()
        rel = p.parent.relative_to(C.ROOT).as_posix()
        urls = [f"{base}/{rel}/{i.name}" for i in sorted(p.parent.glob("slide_*.jpg"))]
        print(f"Publicando {p.parent.name} ({len(urls)} slides)")
        m["instagram_id"] = publicar_carrossel(urls, m["legenda"])
        m["status"] = "publicado"
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), "utf-8")
        return
    print("Nenhum post liberado para publicar.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ideias", "gerar", "publicar", "listar"])
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    {"ideias": lambda: cmd_ideias(a.n), "gerar": lambda: cmd_gerar(a.n),
     "publicar": cmd_publicar, "listar": cmd_listar}[a.cmd]()
