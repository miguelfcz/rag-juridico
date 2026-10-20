# ========================================================
# 🛡️ SENTINEL AI - CONEXÃO COM O FALKORDB (BANCO DE GRAFO)
# ========================================================

import os
from dotenv import load_dotenv
from falkordb import FalkorDB, Graph

load_dotenv()

FALKOR_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKOR_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("FALKORDB_GRAPH_NAME", "rede_fraude_sentinel")


def get_graph() -> Graph:
    """Retorna o grafo de investigação do FalkorDB."""
    db = FalkorDB(host=FALKOR_HOST, port=FALKOR_PORT)
    return db.select_graph(GRAPH_NAME)
