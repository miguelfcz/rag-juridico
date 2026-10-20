# ========================================================
# 🛡️ SENTINEL AI - PIPELINE POSTGRESQL ➔ FALKORDB
# ========================================================
# O PostgreSQL é a fonte da verdade. Este script lê as tabelas
# relacionais e reconstrói o grafo de investigação no FalkorDB.
#
# Modelo do grafo:
#   (:Cliente)-[:TITULAR_DE]->(:Conta)
#   (:Conta)-[:TRANSFERIU {valor, tipo, data_hora}]->(:Conta)
#   (:Conta)-[:ACESSOU_VIA]->(:Dispositivo)
#   (:Conta)-[:CONECTOU_DE]->(:IP)
#
# Uso (a partir da raiz do projeto):
#   python -m graph.sync_postgres_to_falkor
# ========================================================

import sys
from datetime import date, datetime
from decimal import Decimal

from database.connection import execute_query
from graph.connection import get_graph

sys.stdout.reconfigure(encoding="utf-8")


def _normalizar(row: dict) -> dict:
    """Converte tipos do Postgres (Decimal, datetime, None) para tipos aceitos pelo FalkorDB."""
    saida = {}
    for chave, valor in row.items():
        if isinstance(valor, Decimal):
            saida[chave] = float(valor)
        elif isinstance(valor, (datetime, date)):
            saida[chave] = valor.isoformat()
        elif valor is None:
            saida[chave] = ""
        else:
            saida[chave] = valor
    return saida


def _carregar(sql: str) -> list:
    return [_normalizar(dict(r)) for r in execute_query(sql)]


def sincronizar():
    g = get_graph()

    # 1. Recria o grafo do zero (sincronização completa)
    try:
        g.delete()
        print("🧹 Grafo anterior removido.")
    except Exception:
        pass  # grafo ainda não existia

    for label, prop in [("Cliente", "id"), ("Conta", "id"), ("Dispositivo", "id"), ("IP", "endereco")]:
        g.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")

    # 2. Nós
    clientes = _carregar("""
        SELECT id, nome, documento, tipo_pessoa, renda_declarada, ocupacao,
               data_abertura_empresa, cidade, estado
        FROM clientes
    """)
    g.query("""
        UNWIND $rows AS r
        CREATE (:Cliente {id: r.id, nome: r.nome, documento: r.documento, tipo_pessoa: r.tipo_pessoa,
                          renda_declarada: r.renda_declarada, ocupacao: r.ocupacao,
                          data_abertura_empresa: r.data_abertura_empresa, cidade: r.cidade, estado: r.estado})
    """, {"rows": clientes})
    print(f"👥 {len(clientes)} nós :Cliente")

    contas = _carregar("SELECT id, cliente_id, numero_conta, status, data_abertura FROM contas")
    g.query("""
        UNWIND $rows AS r
        MATCH (cli:Cliente {id: r.cliente_id})
        CREATE (cli)-[:TITULAR_DE]->(:Conta {id: r.id, numero: r.numero_conta, status: r.status,
                                             data_abertura: r.data_abertura})
    """, {"rows": contas})
    print(f"🏦 {len(contas)} nós :Conta (+ arestas TITULAR_DE)")

    dispositivos = _carregar("SELECT id, device_id, modelo, sistema_operacional FROM dispositivos")
    g.query("""
        UNWIND $rows AS r
        CREATE (:Dispositivo {id: r.id, device_id: r.device_id, modelo: r.modelo, so: r.sistema_operacional})
    """, {"rows": dispositivos})
    print(f"📱 {len(dispositivos)} nós :Dispositivo")

    # 3. Arestas de acesso (conta ➔ aparelho, conta ➔ IP)
    acessos = _carregar("SELECT conta_id, dispositivo_id, ip_origem, geolocalizacao FROM acessos")
    g.query("""
        UNWIND $rows AS r
        MATCH (c:Conta {id: r.conta_id}), (d:Dispositivo {id: r.dispositivo_id})
        MERGE (c)-[:ACESSOU_VIA]->(d)
        MERGE (ip:IP {endereco: r.ip_origem})
        MERGE (c)-[:CONECTOU_DE {geo: r.geolocalizacao}]->(ip)
    """, {"rows": acessos})
    print(f"🔌 {len(acessos)} acessos (arestas ACESSOU_VIA / CONECTOU_DE)")

    # 4. Arestas de dinheiro
    transacoes = _carregar("""
        SELECT id, conta_origem_id, conta_destino_id, valor, tipo, data_hora, status
        FROM transacoes
    """)
    g.query("""
        UNWIND $rows AS r
        MATCH (o:Conta {id: r.conta_origem_id}), (d:Conta {id: r.conta_destino_id})
        CREATE (o)-[:TRANSFERIU {id: r.id, valor: r.valor, tipo: r.tipo, data_hora: r.data_hora, status: r.status}]->(d)
    """, {"rows": transacoes})
    print(f"💸 {len(transacoes)} arestas TRANSFERIU")

    # 5. Conferência
    nos = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    arestas = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"\n✅ Grafo sincronizado: {nos} nós e {arestas} arestas.")


if __name__ == "__main__":
    sincronizar()
