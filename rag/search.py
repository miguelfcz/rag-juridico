import os
import sys
from typing import List, Dict

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

from rag.ingest import gerar_vetores_densos, texto_para_vetor_esparso

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "normas_bacen_coaf")


def _get_qdrant() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def _formatar_pontos(pontos) -> List[Dict]:
    return [
        {
            "chunk_id": p.payload.get("chunk_id"),
            "documento": p.payload.get("documento"),
            "secao": p.payload.get("secao"),
            "texto": p.payload.get("texto"),
            "score": round(float(p.score), 4)
        }
        for p in pontos
    ]


def busca_semantica(pergunta: str, top_k: int = 3) -> List[Dict]:
    qdrant = _get_qdrant()
    vetor_denso = gerar_vetores_densos([pergunta])[0]

    resposta = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vetor_denso,
        using="dense",
        limit=top_k
    )
    return _formatar_pontos(resposta.points)


def busca_lexica(pergunta: str, top_k: int = 3) -> List[Dict]:
    qdrant = _get_qdrant()
    vetor_esparso = texto_para_vetor_esparso(pergunta)

    if not vetor_esparso.indices:
        return []

    resposta = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vetor_esparso,
        using="lexical",
        limit=top_k
    )
    return _formatar_pontos(resposta.points)


def busca_hibrida(pergunta: str, top_k: int = 3) -> List[Dict]:
    qdrant = _get_qdrant()
    vetor_denso = gerar_vetores_densos([pergunta])[0]
    vetor_esparso = texto_para_vetor_esparso(pergunta)

    resposta = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=vetor_denso,
                using="dense",
                limit=top_k * 2
            ),
            models.Prefetch(
                query=vetor_esparso,
                using="lexical",
                limit=top_k * 2
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k
    )
    return _formatar_pontos(resposta.points)


if __name__ == "__main__":
    consulta_teste = "Qual a regra para código COAF-TIP-104 e lavagem em circuito fechado?"
    print(f"Consulta: '{consulta_teste}'\n")

    print("--- Busca Léxica (BM25 Esparso) ---")
    for r in busca_lexica(consulta_teste, top_k=2):
        print(f"  [Score: {r['score']}] {r['secao']}")

    print("\n--- Busca Semântica (Vetor Denso Vertex AI) ---")
    for r in busca_semantica(consulta_teste, top_k=2):
        print(f"  [Score: {r['score']}] {r['secao']}")

    print("\n--- Busca Híbrida (Fusão RRF) ---")
    for r in busca_hibrida(consulta_teste, top_k=2):
        print(f"  [Score RRF: {r['score']}] {r['secao']}")
