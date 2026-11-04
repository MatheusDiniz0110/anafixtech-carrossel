"""Gera o carrossel com Claude, passa no detector de 'cara de IA' e reescreve até limpar."""
import json
import re
from . import config as C
from .slop import lint
from .llm import completar

SYSTEM = f"""Você escreve carrosséis de Instagram para a {C.BRAND}, empresa de informática de {C.CITY} (GO) que presta
assistência técnica, manutenção de hardware, instalação e correção de software, recuperação e backup de dados,
redes e suporte de TI para pessoas e pequenas empresas. O objetivo do perfil é mostrar que quem escreve entende de
verdade do assunto, para que o leitor chame no WhatsApp quando precisar.

VOZ
- Técnico experiente explicando para um vizinho inteligente que não é da área. Português do Brasil, direto, "a gente".
- Frases curtas. Verbo logo no começo. Zero enrolação, zero tom de palestra motivacional.
- Prefira o específico ao genérico: nome do componente, comando real, número real, sintoma real que o leitor já viu.
- Pode ter uma opinião firme quando ela é tecnicamente defensável.

ESTRUTURA (6 a 8 slides)
1. capa: uma afirmação ou situação concreta que o leitor reconhece. Não é título de blog. Máx. 12 palavras.
2 a N-1. um slide = uma ideia. Cada um entrega algo que o leitor não sabia ou não sabia explicar. Máx. 30 palavras
   no texto. Use o tipo "codigo" quando um comando, caminho ou configuração real ajuda (no máximo 2 slides, até 6 linhas
   de até 34 caracteres cada).
N. cta: uma frase simples ligando o tema a um caso em que vale chamar um técnico. Sem pressão, sem promessa.

PROIBIDO (o texto é rejeitado automaticamente)
- Travessão (— ou –). Use ponto ou vírgula.
- A construção "não é X, é Y" e qualquer variação.
- Aberturas e fechos de IA: "no mundo de hoje", "você sabia", "vamos explorar", "em resumo", "é fundamental",
  "desbloqueie", "jornada", "potencialize", "guia completo/definitivo", "segredo", "incrível".
- Emoji nos slides (máx. 2 na legenda), exclamação em excesso, listas de três itens só por ritmo.
- Inventar estatística, estudo, depoimento, preço ou fato sobre a {C.BRAND}. Se um número ou afirmação técnica não for
  certeza absoluta, escreva sem o número e registre a dúvida em "incertezas".
- Instruções que possam causar perda de dados sem um aviso claro de backup antes.

SAÍDA: somente JSON válido, sem markdown, neste formato:
{{
  "titulo": "nome interno curto do post",
  "slides": [
    {{"tipo": "capa", "titulo": "...", "texto": "subtítulo opcional curto"}},
    {{"tipo": "texto", "titulo": "...", "texto": "..."}},
    {{"tipo": "codigo", "titulo": "...", "codigo": "linha1\\nlinha2", "texto": "..."}},
    {{"tipo": "cta", "titulo": "...", "texto": "..."}}
  ],
  "legenda": "até 90 palavras, começa com a ideia principal, termina com uma pergunta real ou convite simples",
  "hashtags": ["até 5, específicas, sem #"],
  "incertezas": ["afirmações técnicas das quais você não tem 100% de certeza, ou lista vazia"]
}}"""


def _chamar(_client, mensagens, max_tokens=3000) -> str:
    return completar(SYSTEM, mensagens, max_tokens)


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("Resposta sem JSON")
    return json.loads(m.group(0))


def gerar_post(tema: str, angulo: str = "", tentativas: int = 4) -> tuple[dict, list[str]]:
    """Retorna (post, problemas_restantes)."""
    client = None
    pedido = f"Tema: {tema}\n"
    if angulo:
        pedido += f"Ângulo: {angulo}\n"
    pedido += "Escreva o carrossel."
    msgs = [{"role": "user", "content": pedido}]

    post, probs = {}, ["não gerou"]
    for _ in range(tentativas):
        bruto = _chamar(client, msgs)
        try:
            post = _json(bruto)
        except Exception as e:  # JSON quebrado
            probs = [f"JSON inválido: {e}"]
        else:
            probs = lint(post)
            if not probs:
                return post, []
        msgs += [
            {"role": "assistant", "content": bruto},
            {"role": "user", "content": "Reescreva corrigindo exatamente estes problemas, mantendo o que já estava bom:\n- "
             + "\n- ".join(probs) + "\nResponda só com o JSON."},
        ]
    return post, probs


def novas_ideias(qtd: int, ja_usados: list[str]) -> list[dict]:
    client = None
    pedido = (
        f"Liste {qtd} temas de informática para carrosséis, que atraiam pessoas e pequenos negócios de {C.CITY} com "
        "problemas reais de computador, celular, rede, dados e segurança. Misture hardware, software, dados e dia a dia "
        "de escritório. Cada tema precisa ter um ângulo específico (um erro comum, um sintoma, uma comparação). "
        f"Não repita: {', '.join(ja_usados[-40:]) or 'nada ainda'}.\n"
        'Responda só com JSON: {"ideias": [{"tema": "...", "angulo": "..."}]}'
    )
    return _json(_chamar(client, [{"role": "user", "content": pedido}], 2500))["ideias"]
