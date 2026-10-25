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


def consultar_dados_bancarios_sql(conta_id: int) -> dict:
    """
    Consulta no PostgreSQL os dados cadastrais do titular (renda declarada, ocupação,
    data de abertura da empresa), dispositivos de acesso e extrato de transações PIX/TED da conta.
    """
    perfil = execute_query("""
        SELECT cnt.id AS conta_id, cnt.numero_conta, cnt.saldo, cnt.status, cnt.data_abertura,
               cli.nome, cli.documento, cli.tipo_pessoa, cli.renda_declarada,
               cli.ocupacao, cli.data_abertura_empresa, cli.cidade, cli.estado, cli.score_credito
        FROM contas cnt
        JOIN clientes cli ON cli.id = cnt.cliente_id
        WHERE cnt.id = %s
    """, (conta_id,))

    acessos = execute_query("""
        SELECT d.device_id, d.modelo, d.sistema_operacional, a.ip_origem, a.geolocalizacao, a.data_hora
        FROM acessos a
        JOIN dispositivos d ON d.id = a.dispositivo_id
        WHERE a.conta_id = %s
    """, (conta_id,))

    transacoes = execute_query("""
        SELECT t.id, t.valor, t.tipo, t.data_hora, t.descricao,
               co.numero_conta AS conta_origem, cd.numero_conta AS conta_destino,
               CASE WHEN t.conta_origem_id = %s THEN 'SAIDA' ELSE 'ENTRADA' END AS direcao
        FROM transacoes t
        JOIN contas co ON co.id = t.conta_origem_id
        JOIN contas cd ON cd.id = t.conta_destino_id
        WHERE t.conta_origem_id = %s OR t.conta_destino_id = %s
        ORDER BY t.data_hora DESC
        LIMIT 20
    """, (conta_id, conta_id, conta_id))

    return _serializar({
        "perfil_conta": dict(perfil[0]) if perfil else {},
        "dispositivos_e_ips": [dict(a) for a in acessos],
        "ultimas_transacoes": [dict(t) for t in transacoes],
    })


def investigar_vinculos_grafo(conta_id: int) -> dict:
    """
    Consulta no banco de grafos FalkorDB (via Cypher) a teia de relacionamentos da conta:
    ciclos de triangulação (A -> B -> C -> A), compartilhamento do mesmo aparelho físico ou IP
    com outros titulares e rastreamento do fluxo de entrada e saída de recursos.
    """
    return _serializar({
        "ciclos_financeiros": graph_queries.detectar_ciclos_financeiros(conta_id),
        "contas_mesmo_dispositivo_ou_ip": graph_queries.contas_com_mesmo_dispositivo_ou_ip(conta_id),
        "fluxo_saida": graph_queries.rastrear_fluxo_dinheiro(conta_id, direcao="saida", max_saltos=2),
        "fluxo_entrada": graph_queries.rastrear_fluxo_dinheiro(conta_id, direcao="entrada", max_saltos=1),
    })


def consultar_normas_regulatorias_rag(consulta: str) -> list:
    """
    Executa busca híbrida (Semântica Vetorial + Léxica BM25 com fusão RRF) no Qdrant Cloud
    para encontrar artigos da Circular BACEN 3.978/2020, Carta Circular 4.001/2020,
    códigos de tipologia do COAF e regras do MED aplicáveis ao caso investigado.
    """
    return busca_hibrida(consulta, top_k=3)


FERRAMENTAS_AGENTE = [
    consultar_dados_bancarios_sql,
    investigar_vinculos_grafo,
    consultar_normas_regulatorias_rag,
]
