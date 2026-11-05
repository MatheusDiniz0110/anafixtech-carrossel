# Agente de carrosséis AnaFixTech

Fluxo semanal, sem você abrir nada (depois do setup):

1. **Domingo**: o agente pega 3 temas da fila (`topics.json`), pede o carrossel ao modelo de IA, passa num detector de "cara de IA"
   (`agent/slop.py`), reescreve até limpar, renderiza os slides em JPEG 1080x1350 e salva em `posts/`.
2. **Você revisa** (2 min por post): abra `posts/<data>-<tema>/post.json` no GitHub e troque `"status": "pendente"` por
   `"aprovado"`. Posts com `"precisa_revisao": true` têm afirmações técnicas que o próprio Claude marcou como incertas
   (`incertezas`). Confira essas antes de aprovar.
3. **Seg/qua/sex 11h**: o agente publica o post aprovado mais antigo.

Quando você confiar no resultado, crie a variável `AUTO_APPROVE=1` no GitHub e ele publica sozinho tudo que não tiver alerta.

## Setup (uma vez)

**1. Repositório.** Crie um repositório **público** no GitHub e suba esta pasta. (O Instagram baixa as imagens por URL pública;
o agente usa `raw.githubusercontent.com`, de graça.)

**2. IA (gratuita).** Crie uma conta em openrouter.ai, gere uma chave em *Keys* e salve como secret
`OPENROUTER_API_KEY` (Settings > Secrets and variables > Actions). O padrão usa modelos com `:free`, que custam zero:
`google/gemma-4-31b-it:free`, `nvidia/nemotron-3-ultra-550b-a55b:free` e `cohere/north-mini-code:free`, nesta ordem.
Se um deles estiver rate-limited, o agente passa para o próximo sozinho. Para trocar, edite `OPENROUTER_MODEL` no `.env`
(ou crie a variável no GitHub Actions). Alternativas: `LLM_PROVIDER=gemini` com `GEMINI_API_KEY` do aistudio.google.com,
ou `LLM_PROVIDER=claude` com `ANTHROPIC_API_KEY` (pago).

**3. Instagram.** Conta Profissional (Comercial ou Criador). Crie um app em developers.facebook.com com o caso de uso
"Manage messaging & content on Instagram", abra *API setup with Instagram login*, adicione a conta como testador, gere o token
e copie o ID da conta. Salve `IG_USER_ID` e `IG_ACCESS_TOKEN` como secrets. O token dura 60 dias: rode
`python -m agent.main renovar` a cada ~50 dias e atualize o secret.

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
