import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
FONTS_DIR = ROOT / "assets" / "fonts"
TOPICS_FILE = ROOT / "topics.json"

# Marca
BRAND = "AnaFixTech"
HANDLE = "@anafixtech_informatica15"
CITY = "Anápolis"
WHATSAPP_TEXT = "(62) 99887-7833"

# Visual (1080x1350 = proporção 4:5, ocupa mais tela no feed)
W, H = 1080, 1350
BG = (11, 15, 23)
FG = (232, 236, 244)
MUTED = (140, 151, 170)
ACCENT = (59, 130, 246)
CODE_BG = (22, 29, 42)

AUTO_APPROVE = os.getenv("AUTO_APPROVE", "0") == "1"
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
# Instagram API com Login do Instagram (não exige Página do Facebook).
# Se um dia usar token de Página do Facebook, defina IG_GRAPH=https://graph.facebook.com/v21.0
GRAPH = os.getenv("IG_GRAPH", "https://graph.instagram.com/v21.0")


def public_base_url() -> str:
    url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if url:
        return url
    repo = os.getenv("GITHUB_REPOSITORY")
    branch = os.getenv("GITHUB_REF_NAME", "main")
    if repo:
        return f"https://raw.githubusercontent.com/{repo}/{branch}"
    raise RuntimeError("Defina PUBLIC_BASE_URL no .env")
