import os
import sys
from typing import Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agent.tools import (
    consultar_processos_e_clientes_sql,
    explorar_rede_societaria_grafo,
    buscar_documentos_juridicos_rag,
)
from agent.guardrails import validar_entrada, auditar_resposta_ia

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
LLM_MODEL = os.getenv("VERTEX_LLM_MODEL", "gemini-3-flash-preview")

SYSTEM_PROMPT = """
Você é o Assistente Jurídico Inteligente do Ecossistema de IA do escritório.
Você possui acesso direto a 3 motores de dados via ferramentas MCP/Function Calling:
1. `consultar_processos_e_clientes_sql(termo_busca)`: consulta no PostgreSQL processos judiciais (número CNJ, parte contrária, valor da causa, risco de perda PROVAVEL/POSSIVEL/REMOTO, prazos, resumo do objeto), clientes, advogados e contratos de honorários.
2. `explorar_rede_societaria_grafo(termo_cliente)`: consulta no FalkorDB (via Cypher) a teia societária, identificando grupos econômicos (empresas que compartilham sócios ou holdings controladoras), partes contrárias recorrentes e vínculos societários.
3. `buscar_documentos_juridicos_rag(consulta)`: executa busca híbrida (Vetorial Denso + Léxico BM25 com fusão RRF) no Qdrant Cloud sobre os documentos PDF e normativos indexados (CLT, Código Civil, CPC, Lei de Incorporações 4.591/64, STJ Tema 779, Lei das S.A. e Políticas Internas CPC-25).

Diretrizes:
- Sempre acione as ferramentas necessárias antes de responder para basear sua análise em dados reais do escritório.
- Quando a pergunta envolver processos, riscos societários ou fundamentação legal, combine os dados do banco (PostgreSQL), as conexões societárias (FalkorDB) e a base documental/legal (Qdrant Cloud), citando os artigos e códigos de referência encontrados.
- Responda de forma clara, estruturada em Markdown e objetiva.
""".strip()


def responder_consulta_juridica(pergunta: str) -> Dict:
    check_input = validar_entrada(pergunta)
    if not check_input["aprovado"]:
        return {"erro": check_input["motivo"]}

    rastro_ferramentas: List[Dict] = []
    trechos_rag: List[str] = []

    def tool_sql(termo_busca: str = "") -> dict:
        """Consulta no PostgreSQL processos judiciais, clientes, advogados, prazos e contratos de honorários."""
        res = consultar_processos_e_clientes_sql(termo_busca)
        rastro_ferramentas.append({
            "ferramenta": "consultar_processos_e_clientes_sql (PostgreSQL MCP)",
            "argumentos": {"termo_busca": termo_busca},
            "resultado": res,
        })
        return res

    def tool_grafo(termo_cliente: str = "") -> dict:
        """Consulta no FalkorDB grupos econômicos, sócios compartilhados entre empresas e partes contrárias."""
        res = explorar_rede_societaria_grafo(termo_cliente)
        rastro_ferramentas.append({
            "ferramenta": "explorar_rede_societaria_grafo (FalkorDB Graph)",
            "argumentos": {"termo_cliente": termo_cliente},
            "resultado": res,
        })
        return res

    def tool_rag(consulta: str) -> list:
        """Executa busca híbrida (Semântica + BM25 com RRF) nos PDFs e documentos jurídicos no Qdrant Cloud."""
        res = buscar_documentos_juridicos_rag(consulta)
        for item in res:
            trechos_rag.append(item.get("texto", ""))
        rastro_ferramentas.append({
            "ferramenta": "buscar_documentos_juridicos_rag (Qdrant Hybrid RAG)",
            "argumentos": {"consulta": consulta},
            "resultado": res,
        })
        return res

    client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)
    chat = client.chats.create(
        model=LLM_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[tool_sql, tool_grafo, tool_rag],
            temperature=0.1,
        ),
    )
    resposta = chat.send_message(pergunta)
    auditoria = auditar_resposta_ia(resposta.text or "", trechos_rag)

    return {
        "resposta_markdown": auditoria["texto_seguro"],
        "auditoria_guardrails": auditoria,
        "rastro_ferramentas": rastro_ferramentas,
    }


if __name__ == "__main__":
    teste = responder_consulta_juridica(
        "Quais empresas fazem parte do grupo econômico da Horizonte Logística, quais processos elas enfrentam e qual o risco legal segundo a CLT e o Código Civil?"
    )
    print(teste["resposta_markdown"])
