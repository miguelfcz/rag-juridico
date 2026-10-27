from datetime import date, datetime
from decimal import Decimal

from database.connection import execute_query
from graph import queries as graph_queries
from rag.search import busca_hibrida


def _serializar(obj):
    if isinstance(obj, list):
        return [_serializar(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serializar(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


def consultar_processos_e_clientes_sql(termo_busca: str = "") -> dict:
    """
    Consulta no banco PostgreSQL do escritório os processos judiciais, clientes (PF/PJ),
    advogados responsáveis, valores de causa, risco de perda (PROVAVEL, POSSIVEL, REMOTO),
    próximos prazos e contratos de honorários. Se `termo_busca` for vazio, retorna o panorama geral.
    """
    termo = f"%{termo_busca.strip()}%" if termo_busca and termo_busca.strip() else "%"

    processos = execute_query("""
        SELECT p.numero_cnj, c.nome AS cliente, c.documento AS doc_cliente, c.segmento,
               a.nome AS advogado_responsavel, a.oab, p.parte_contraria,
               p.area_direito, p.tribunal, p.valor_causa, p.risco_perda,
               p.status, p.proximo_prazo, p.resumo_objeto
        FROM processos p
        JOIN clientes c ON c.id = p.cliente_id
        JOIN advogados a ON a.id = p.advogado_id
        WHERE c.nome ILIKE %s
           OR p.numero_cnj ILIKE %s
           OR p.parte_contraria ILIKE %s
           OR p.area_direito ILIKE %s
           OR a.nome ILIKE %s
           OR p.resumo_objeto ILIKE %s
        ORDER BY p.valor_causa DESC
    """, (termo, termo, termo, termo, termo, termo))

    contratos = execute_query("""
        SELECT ch.codigo_contrato, c.nome AS cliente, ch.tipo_contrato,
               ch.valor_mensal, ch.percentual_exito, ch.status_pagamento,
               ch.data_assinatura, ch.data_vencimento
        FROM contratos_honorarios ch
        JOIN clientes c ON c.id = ch.cliente_id
        WHERE c.nome ILIKE %s OR ch.codigo_contrato ILIKE %s OR ch.status_pagamento ILIKE %s
        ORDER BY ch.valor_mensal DESC
    """, (termo, termo, termo))

    advogados = execute_query("SELECT nome, oab, especialidade, email FROM advogados ORDER BY nome")

    return _serializar({
        "processos_encontrados": [dict(p) for p in processos],
        "contratos_honorarios": [dict(c) for c in contratos],
        "equipe_advogados": [dict(a) for a in advogados],
    })


def explorar_rede_societaria_grafo(termo_cliente: str = "") -> dict:
    """
    Consulta no banco de grafos FalkorDB (via Cypher) as conexões societárias, processuais
    e de documentos enviados: grupos econômicos, partes contrárias recorrentes, teia de vínculos
    de um cliente específico e relações de grafo extraídas de PDFs enviados.
    """
    termo = termo_cliente.strip() if termo_cliente else ""
    resultado = {
        "grupos_economicos_detectados": graph_queries.detectar_grupos_economicos(),
        "partes_contrarias_recorrentes": graph_queries.partes_contrarias_recorrentes(),
        "grafo_extraido_documentos": graph_queries.obter_grafo_de_documento(termo_busca=termo),
    }
    if termo:
        resultado["rede_especifica_cliente"] = graph_queries.mapear_rede_cliente(termo)
    return _serializar(resultado)


def buscar_documentos_juridicos_rag(consulta: str) -> list:
    """
    Executa busca híbrida (Semântica Vetorial Vertex AI + Léxica BM25 com fusão RRF) no Qdrant Cloud
    sobre os documentos jurídicos, PDFs enviados, legislação (CLT, Código Civil, CPC, Lei 4.591/64,
    Tema 779 STJ) e políticas de contratos e contingências (CPC 25) do escritório.
    """
    return busca_hibrida(consulta, top_k=4)


FERRAMENTAS_AGENTE = [
    consultar_processos_e_clientes_sql,
    explorar_rede_societaria_grafo,
    buscar_documentos_juridicos_rag,
]
