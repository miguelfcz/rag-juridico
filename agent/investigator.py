import os
import sys
import json
from typing import Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from database.connection import execute_query
from agent.tools import (
    consultar_dados_bancarios_sql,
    investigar_vinculos_grafo,
    consultar_normas_regulatorias_rag,
)
from agent.guardrails import validar_entrada, auditar_resposta_ia

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
LLM_MODEL = os.getenv("VERTEX_LLM_MODEL", "gemini-3-flash-preview")

SYSTEM_PROMPT = """
Você é um Especialista Sênior de Investigação de Fraudes e Prevenção à Lavagem de Dinheiro (PLD/AML).
Para auditar um caso suspeito, você DEVE obrigatoriamente utilizar suas 3 ferramentas antes de emitir o parecer:
1. Chame `consultar_dados_bancarios_sql` passando o `conta_id` para obter renda, cadastro, dispositivos e extrato PIX/TED.
2. Chame `investigar_vinculos_grafo` passando o `conta_id` para verificar ciclos de triangulação, aparelhos/IPs compartilhados e fluxo do dinheiro no FalkorDB.
3. Chame `consultar_normas_regulatorias_rag` descrevendo os indícios encontrados para buscar na base do Qdrant Cloud os artigos do BACEN e códigos COAF aplicáveis.

Estruture seu Dossiê Técnico (SAR) em Markdown com as seguintes seções:
- **1. Resumo Executivo do Alerta**
- **2. Evidências Transacionais e Cadastrais (PostgreSQL)**
- **3. Análise de Rede e Vínculos Ocultos (FalkorDB GraphRAG)**
- **4. Enquadramento Regulatório BACEN / COAF (Qdrant Hybrid RAG)** (cite expressamente os códigos oficiais recuperados, ex: COAF-TIP-101, REGRA-KYC-01, GOV-ALCADA-01)
- **5. Parecer Recomendatório para Alçada Humana** (lembre que o bloqueio definitivo e reporte ao SISCOAF exigem assinatura do Analista de Compliance conforme GOV-ALCADA-01).
""".strip()


def buscar_alerta_por_id(alerta_id: int) -> Dict:
    rows = execute_query("""
        SELECT a.id, a.conta_alvo_id, a.tipo_alerta, a.score_risco, a.status, a.detalhes,
               cnt.numero_conta, cli.nome AS titular
        FROM alertas_fraude a
        JOIN contas cnt ON cnt.id = a.conta_alvo_id
        JOIN clientes cli ON cli.id = cnt.cliente_id
        WHERE a.id = %s
    """, (alerta_id,))
    return dict(rows[0]) if rows else {}


def investigar_alerta(alerta_id: int, instrucao_extra: str = "") -> Dict:
    if instrucao_extra:
        check_input = validar_entrada(instrucao_extra)
        if not check_input["aprovado"]:
            return {"erro": check_input["motivo"]}

    alerta = buscar_alerta_por_id(alerta_id)
    if not alerta:
        return {"erro": f"Alerta #{alerta_id} não encontrado."}

    rastro_ferramentas: List[Dict] = []
    trechos_rag: List[str] = []

    # Wrappers para registrar o rastro exato de cada ferramenta acionada pelo Gemini
    def tool_sql(conta_id: int) -> dict:
        """Consulta no PostgreSQL os dados cadastrais do titular, dispositivos de acesso e extrato de transações PIX/TED da conta."""
        res = consultar_dados_bancarios_sql(conta_id)
        rastro_ferramentas.append({"ferramenta": "consultar_dados_bancarios_sql", "argumentos": {"conta_id": conta_id}, "resultado": res})
        return res

    def tool_grafo(conta_id: int) -> dict:
        """Consulta no FalkorDB (Cypher) ciclos de triangulação, compartilhamento de aparelho/IP e fluxo de recursos da conta."""
        res = investigar_vinculos_grafo(conta_id)
        rastro_ferramentas.append({"ferramenta": "investigar_vinculos_grafo", "argumentos": {"conta_id": conta_id}, "resultado": res})
        return res

    def tool_rag(consulta: str) -> list:
        """Executa busca híbrida (Semântica + Léxica BM25 com RRF) no Qdrant Cloud para encontrar normas do BACEN e códigos COAF."""
        res = consultar_normas_regulatorias_rag(consulta)
        for item in res:
            trechos_rag.append(item.get("texto", ""))
        rastro_ferramentas.append({"ferramenta": "consultar_normas_regulatorias_rag", "argumentos": {"consulta": consulta}, "resultado": res})
        return res

    prompt_investigacao = (
        f"Audite o Alerta de Fraude #{alerta['id']}:\n"
        f"- Titular: {alerta['titular']}\n"
        f"- Conta ID (para uso nas ferramentas): {alerta['conta_alvo_id']} (Número: {alerta['numero_conta']})\n"
        f"- Tipo de Alerta Inicial: {alerta['tipo_alerta']} (Score de Risco: {alerta['score_risco']}/100)\n"
        f"- Detalhes Preliminares: {json.dumps(alerta['detalhes'], ensure_ascii=False)}\n"
    )
    if instrucao_extra:
        prompt_investigacao += f"\nInstrução adicional do analista: {instrucao_extra}\n"

    client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)
    chat = client.chats.create(
        model=LLM_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[tool_sql, tool_grafo, tool_rag],
            temperature=0.1,
        )
    )
    resposta = chat.send_message(prompt_investigacao)

    auditoria = auditar_resposta_ia(resposta.text or "", trechos_rag)

    return {
        "alerta": alerta,
        "dossie_markdown": auditoria["texto_seguro"],
        "auditoria_guardrails": auditoria,
        "rastro_ferramentas": rastro_ferramentas,
    }


if __name__ == "__main__":
    print("Iniciando investigação do Alerta #4 (Triangulação) via Gemini + MCP Tools...\n")
    resultado = investigar_alerta(4)

    print("Ferramentas acionadas autonomamente pelo Gemini:")
    for idx, t in enumerate(resultado["rastro_ferramentas"], start=1):
        print(f"  {idx}. {t['ferramenta']}({t['argumentos']})")

    print("\nAuditoria Guardrails:", {k: v for k, v in resultado["auditoria_guardrails"].items() if k != "texto_seguro"})
    print("\n" + "=" * 70)
    print(resultado["dossie_markdown"])
