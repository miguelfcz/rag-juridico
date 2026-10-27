import os
import re
import sys
import zlib
from collections import Counter
from typing import List, Dict

import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient, models

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
EMBED_MODEL = os.getenv("VERTEX_EMBED_MODEL", "text-embedding-004")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "acervo_juridico")

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
    documento_atual = "Acervo Jurídico"
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


def extrair_chunks_de_bytes(nome_arquivo: str, conteudo_bytes: bytes, chunk_size: int = 900, overlap: int = 150) -> List[Dict]:
    """Extrai texto de arquivos PDF, MD ou TXT enviados via upload e divide em chunks."""
    ext = nome_arquivo.lower().split(".")[-1]
    chunks = []

    if ext == "pdf":
        doc = fitz.open(stream=conteudo_bytes, filetype="pdf")
        for num_pag, pagina in enumerate(doc, start=1):
            texto_pag = pagina.get_text("text").strip()
            if not texto_pag:
                continue
            inicio = 0
            parte = 1
            while inicio < len(texto_pag):
                trecho = texto_pag[inicio:inicio + chunk_size].strip()
                if len(trecho) > 40:
                    chunks.append({
                        "documento": nome_arquivo,
                        "secao": f"Página {num_pag} (Parte {parte})",
                        "texto": f"[{nome_arquivo} | Pág. {num_pag}]\n{trecho}"
                    })
                    parte += 1
                inicio += max(1, chunk_size - overlap)
    else:
        texto_completo = conteudo_bytes.decode("utf-8", errors="ignore")
        inicio = 0
        parte = 1
        while inicio < len(texto_completo):
            trecho = texto_completo[inicio:inicio + chunk_size].strip()
            if len(trecho) > 40:
                chunks.append({
                    "documento": nome_arquivo,
                    "secao": f"Seção {parte}",
                    "texto": f"[{nome_arquivo} | Seção {parte}]\n{trecho}"
                })
                parte += 1
            inicio += max(1, chunk_size - overlap)

    return chunks


def texto_para_vetor_esparso(texto: str, k1: float = 1.5, b: float = 0.75, tamanho_medio_doc: float = 80.0) -> models.SparseVector:
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
    vetores = []
    # Processa em lotes de até 50 textos por chamada para suportar PDFs grandes
    for i in range(0, len(textos), 50):
        lote = textos[i:i + 50]
        resposta = client.models.embed_content(
            model=EMBED_MODEL,
            contents=lote
        )
        vetores.extend([emb.values for emb in resposta.embeddings])
    return vetores


def garantir_colecao_qdrant(qdrant: QdrantClient, recriar: bool = False):
    existe = qdrant.collection_exists(COLLECTION_NAME)
    if existe and recriar:
        qdrant.delete_collection(COLLECTION_NAME)
        existe = False

    if not existe:
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


def indexar_chunks_no_qdrant(chunks: List[Dict], recriar_colecao: bool = False) -> int:
    """Gera embeddings densos (Vertex AI) + esparsos (BM25) para uma lista de chunks e grava no Qdrant Cloud."""
    if not chunks:
        return 0

    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    garantir_colecao_qdrant(qdrant, recriar=recriar_colecao)

    info_col = qdrant.get_collection(COLLECTION_NAME)
    id_inicial = (info_col.points_count or 0) + 1

    textos = [c["texto"] for c in chunks]
    vetores_densos = gerar_vetores_densos(textos)

    pontos = []
    for offset, (chunk, vetor_denso) in enumerate(zip(chunks, vetores_densos)):
        ponto_id = id_inicial + offset
        vetor_esparso = texto_para_vetor_esparso(chunk["texto"])

        pontos.append(
            models.PointStruct(
                id=ponto_id,
                vector={
                    "dense": vetor_denso,
                    "lexical": vetor_esparso
                },
                payload={
                    "chunk_id": ponto_id,
                    "documento": chunk["documento"],
                    "secao": chunk["secao"],
                    "texto": chunk["texto"]
                }
            )
        )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=pontos)
    return len(pontos)


def status_colecao_qdrant() -> Dict:
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    if not qdrant.collection_exists(COLLECTION_NAME):
        return {"existe": False, "total_chunks": 0, "documentos": []}

    info = qdrant.get_collection(COLLECTION_NAME)
    scroll_pts, _ = qdrant.scroll(collection_name=COLLECTION_NAME, limit=200, with_payload=True, with_vectors=False)
    docs_unicos = sorted(list({p.payload.get("documento", "Desconhecido") for p in scroll_pts}))
    return {
        "existe": True,
        "total_chunks": info.points_count or len(scroll_pts),
        "documentos": docs_unicos,
        "amostra_chunks": [p.payload for p in scroll_pts[:30]],
    }


def ingerir_no_qdrant():
    caminho_md = os.path.join(os.path.dirname(__file__), "..", "data", "acervo_juridico.md")
    chunks = carregar_e_dividir_normas(caminho_md)
    total = indexar_chunks_no_qdrant(chunks, recriar_colecao=True)
    print(f"Ingestão concluída: {total} pontos híbridos salvos em '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    ingerir_no_qdrant()
