# Agente de carrosséis AnaFixTech

Fluxo semanal, sem você abrir nada (depois do setup):

1. **Domingo**: o agente pega 3 temas da fila (`topics.json`), pede ao Claude o carrossel, passa num detector de "cara de IA"
   (`agent/slop.py`), reescreve até limpar, renderiza os slides em JPEG 1080x1350 e salva em `posts/`.
2. **Você revisa** (2 min por post): abra `posts/<data>-<tema>/post.json` no GitHub e troque `"status": "pendente"` por
   `"aprovado"`. Posts com `"precisa_revisao": true` têm afirmações técnicas que o próprio Claude marcou como incertas
   (`incertezas`). Confira essas antes de aprovar.
3. **Seg/qua/sex 11h**: o agente publica o post aprovado mais antigo.

Quando você confiar no resultado, crie a variável `AUTO_APPROVE=1` no GitHub e ele publica sozinho tudo que não tiver alerta.

## Setup (uma vez)

**1. Repositório.** Crie um repositório **público** no GitHub e suba esta pasta. (O Instagram baixa as imagens por URL pública;
o agente usa `raw.githubusercontent.com`, de graça.)

**2. IA (gratuita).** Entre em aistudio.google.com com sua conta Google, crie uma chave da Gemini API (não pede cartão) e salve
como secret `GEMINI_API_KEY` (Settings > Secrets and variables > Actions). Em AI Studio, confira o ID de um modelo Flash ou
Flash-Lite com cota gratuita e, se for diferente de `gemini-flash-latest`, ponha em `GEMINI_MODEL`. Para usar o Claude
no lugar, defina `LLM_PROVIDER=claude` e `ANTHROPIC_API_KEY` (pago).

**3. Instagram.** A conta `@anafixtech_informatica15` precisa ser **Profissional** (Comercial ou Criador) e estar ligada a uma
**Página do Facebook**. Depois:
- Crie um app em developers.facebook.com (tipo Business) e adicione o produto **Instagram Graph API**.
- Gere um token com as permissões `instagram_basic`, `instagram_content_publish` e `pages_show_list`.
- Troque por token de longa duração e depois pegue o **token da Página**, que não expira.
- Descubra o `IG_USER_ID` (`GET /me/accounts` e depois `GET /{page-id}?fields=instagram_business_account`).
- Salve `IG_USER_ID` e `IG_ACCESS_TOKEN` como secrets. Enquanto o app estiver em modo desenvolvimento, funciona para
  contas que são suas.

**4. Teste local** (antes de ligar o agendamento):
```bash
pip install -r requirements.txt
cp .env.example .env        # preencha
python -m agent.main ideias --n 15
python -m agent.main gerar --n 1
python -m agent.main listar
```
Abra os JPEGs em `posts/`, aprove um e rode `python -m agent.main publicar`.

## Ajustes que mais importam
- **Voz e regras**: `SYSTEM` em `agent/generate.py`.
- **Palavras banidas**: `FRASES_PROIBIDAS` em `agent/slop.py`. Sempre que um post sair com algo que soe artificial,
  adicione a frase ali; a próxima geração já respeita.
- **Visual e contato**: `agent/config.py` (cores, @, WhatsApp).
- **Limite da API**: no máximo 25 posts publicados por dia pela Graph API; o agente usa 3 por semana.
