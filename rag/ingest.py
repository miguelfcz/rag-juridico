import os
import re
import sys
import zlib
from collections import Counter
from typing import List, Dict

from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient, models

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
EMBED_MODEL = os.getenv("VERTEX_EMBED_MODEL", "text-embedding-004")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "normas_bacen_coaf")

STOPWORDS_PT = {
    "a", "o", "as", "os", "de", "do", "da", "dos", "das", "em", "no", "na",
    "nos", "nas", "por", "para", "com", "sem", "sob", "ou", "e", "que", "se",
    "um", "uma", "ao", "aos", "pelo", "pela", "como", "mais", "sua", "seu",
    "ser", "são", "foi", "está", "este", "esta", "isso", "entre", "até"
}


def carregar_e_dividir_normas(caminho_arquivo: str) -> List[Dict]:
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = f.read()

    chunks = []
    documento_atual = "Normativa Geral PLD"
    linhas = conteudo.splitlines()
    titulo_secao = ""
    buffer_linhas = []

    def salvar_buffer():
        texto_limpo = "\n".join(buffer_linhas).strip()
        if len(texto_limpo) > 80:
            chunks.append({
                "documento": documento_atual,
                "secao": titulo_secao or documento_atual,
                "texto": f"[{documento_atual} | {titulo_secao}]\n{texto_limpo}"
            })

    for linha in linhas:
        if linha.startswith("## "):
            salvar_buffer()
            buffer_linhas = []
            documento_atual = linha.replace("## ", "").strip()
            titulo_secao = "Visão Geral"
        elif linha.startswith("### "):
            salvar_buffer()
            buffer_linhas = []
            titulo_secao = linha.replace("### ", "").strip()
        elif not linha.startswith("# ") and linha.strip() != "---":
            buffer_linhas.append(linha)

    salvar_buffer()
    return chunks


def texto_para_vetor_esparso(texto: str, k1: float = 1.5, b: float = 0.75, tamanho_medio_doc: float = 80.0) -> models.SparseVector:
    # Preserva hífens, pontos e barras internos para manter códigos regulatórios intactos
    tokens_brutos = re.findall(r"[a-zA-ZÀ-ÿ0-9]+(?:[-./][a-zA-ZÀ-ÿ0-9]+)*", texto.lower())
    tokens = [t for t in tokens_brutos if t not in STOPWORDS_PT and len(t) > 1]

    if not tokens:
        return models.SparseVector(indices=[], values=[])

    contagem = Counter(tokens)
    tamanho_doc = len(tokens)

    indices = []
    valores = []

    for termo, freq in contagem.items():
        indice_termo = zlib.crc32(termo.encode("utf-8")) & 0x7FFFFFFF
        peso_bm25_tf = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (tamanho_doc / tamanho_medio_doc)))
        indices.append(indice_termo)
        valores.append(float(peso_bm25_tf))

    return models.SparseVector(indices=indices, values=valores)


def gerar_vetores_densos(textos: List[str]) -> List[List[float]]:
    client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)
    resposta = client.models.embed_content(
        model=EMBED_MODEL,
        contents=textos
    )
    return [emb.values for emb in resposta.embeddings]


def ingerir_no_qdrant():
    caminho_md = os.path.join(os.path.dirname(__file__), "..", "data", "normas_bacen_coaf.md")
    chunks = carregar_e_dividir_normas(caminho_md)

    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    if qdrant.collection_exists(COLLECTION_NAME):
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=768,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "lexical": models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        }
    )

    textos = [c["texto"] for c in chunks]
    vetores_densos = gerar_vetores_densos(textos)

    pontos = []
    for idx, (chunk, vetor_denso) in enumerate(zip(chunks, vetores_densos), start=1):
        vetor_esparso = texto_para_vetor_esparso(chunk["texto"])

        pontos.append(
            models.PointStruct(
                id=idx,
                vector={
                    "dense": vetor_denso,
                    "lexical": vetor_esparso
                },
                payload={
                    "chunk_id": idx,
                    "documento": chunk["documento"],
                    "secao": chunk["secao"],
                    "texto": chunk["texto"]
                }
            )
        )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=pontos)
    print(f"Ingestão concluída: {len(pontos)} pontos híbridos salvos em '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    ingerir_no_qdrant()
