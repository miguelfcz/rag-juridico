import json
import os
import re
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from graph.connection import get_graph

load_dotenv()

VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
LLM_MODEL = os.getenv("VERTEX_LLM_MODEL", "gemini-3-flash-preview")

EXTRACTION_PROMPT = """
Você é um especialista em GraphRAG Jurídico.
Analise o texto do documento jurídico enviado e extraia as conexões principais para construir um Grafo de Conhecimento visual no FalkorDB.
Extraia tanto relações societárias/processuais (se houver) quanto relações conceituais do documento (Partes, Empresas, Leis/Artigos, Cláusulas, Obrigações, Penalidades, Órgãos/Tribunais, Riscos).

Retorne EXCLUSIVAMENTE um JSON válido com a estrutura:
{
  "relacoes_documento": [
    {
      "origem": "Nome curto da entidade de origem (ex: Art. 50 do CC, Construtora Vanguarda, Cláusula de Multa)",
      "tipo_origem": "EMPRESA | PESSOA | LEI_ARTIGO | CLAUSULA | PROCESSO | ORGAO | CONCEITO",
      "relacao": "VERBO_DA_CONEXAO (ex: EXIGE, CONTROLA, APLICA_MULTA, SUSPENDE, RESPONSABILIZA)",
      "destino": "Nome curto da entidade de destino (ex: Confusão Patrimonial, Prazo de 15 Dias, Grupo Econômico)",
      "tipo_destino": "EMPRESA | PESSOA | LEI_ARTIGO | CLAUSULA | PROCESSO | ORGAO | CONCEITO"
    }
  ]
}
Extraia entre 8 e 25 relações ricas e bem conectadas que resumam toda a estrutura lógica e jurídica do documento.
""".strip()


def extrair_e_gravar_grafo_de_documento(nome_arquivo: str, texto_documento: str) -> Dict:
    if not texto_documento or len(texto_documento.strip()) < 20:
        return {"relacoes_criadas": 0}

    client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)
    resposta = client.models.generate_content(
        model=LLM_MODEL,
        contents=f"Documento: {nome_arquivo}\n\nTexto:\n{texto_documento[:25000]}",
        config=types.GenerateContentConfig(
            system_instruction=EXTRACTION_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    texto_json = (resposta.text or "{}").strip()
    texto_json = re.sub(r"^```(?:json)?|```$", "", texto_json, flags=re.MULTILINE).strip()

    try:
        dados = json.loads(texto_json)
    except Exception:
        return {"relacoes_criadas": 0}

    relacoes = dados.get("relacoes_documento", []) or []
    g = get_graph()
    total = 0

    for item in relacoes:
        orig = (item.get("origem") or "").strip()
        dest = (item.get("destino") or "").strip()
        rel = (item.get("relacao") or "CONECTA_COM").strip().upper().replace(" ", "_")
        t_orig = (item.get("tipo_origem") or "CONCEITO").strip().upper()
        t_dest = (item.get("tipo_destino") or "CONCEITO").strip().upper()

        if not orig or not dest:
            continue

        g.query("""
            MERGE (d:DocumentoGrafo {nome: $doc})
            MERGE (o:EntidadeDoc {nome: $orig, documento: $doc})
            ON CREATE SET o.tipo = $t_orig
            MERGE (dst:EntidadeDoc {nome: $dest, documento: $doc})
            ON CREATE SET dst.tipo = $t_dest
            MERGE (d)-[:CONTEM_ENTIDADE]->(o)
            MERGE (o)-[r:RELACAO_DOC {tipo: $rel, documento: $doc}]->(dst)
        """, {
            "doc": nome_arquivo,
            "orig": orig,
            "t_orig": t_orig,
            "dest": dest,
            "t_dest": t_dest,
            "rel": rel,
        })
        total += 1

    return {"relacoes_criadas": total}
