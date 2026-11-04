"""Publicação de carrossel via Instagram Graph API (conta Business/Creator ligada a uma Página)."""
import time
import requests
from . import config as C


def _post(path: str, **dados) -> dict:
    dados["access_token"] = C.IG_ACCESS_TOKEN
    r = requests.post(f"{C.GRAPH}/{path}", data=dados, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Instagram {r.status_code}: {r.text}")
    return r.json()


def _esperar(container_id: str, limite=120):
    t0 = time.time()
    while time.time() - t0 < limite:
        r = requests.get(f"{C.GRAPH}/{container_id}",
                         params={"fields": "status_code", "access_token": C.IG_ACCESS_TOKEN}, timeout=30)
        st = r.json().get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} falhou: {r.text}")
        time.sleep(4)
    raise TimeoutError("Instagram não terminou de processar o carrossel")


def publicar_carrossel(urls: list[str], legenda: str) -> str:
    if not 2 <= len(urls) <= 10:
        raise ValueError("Carrossel precisa de 2 a 10 imagens")
    filhos = []
    for u in urls:
        filhos.append(_post(f"{C.IG_USER_ID}/media", image_url=u, is_carousel_item="true")["id"])
    for f in filhos:
        _esperar(f)
    pai = _post(f"{C.IG_USER_ID}/media", media_type="CAROUSEL", children=",".join(filhos), caption=legenda)["id"]
    _esperar(pai)
    return _post(f"{C.IG_USER_ID}/media_publish", creation_id=pai)["id"]
