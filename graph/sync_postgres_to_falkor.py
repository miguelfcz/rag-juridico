import sys
from datetime import date, datetime
from decimal import Decimal

from database.connection import execute_query
from graph.connection import get_graph

sys.stdout.reconfigure(encoding="utf-8")


def _normalizar(row: dict) -> dict:
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

    try:
        g.delete()
    except Exception:
        pass

    indices = [
        ("Cliente", "id"),
        ("Cliente", "documento"),
        ("Socio", "documento"),
        ("Advogado", "id"),
        ("Processo", "numero_cnj"),
        ("ParteContraria", "nome"),
    ]
    for label, prop in indices:
        g.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")

    clientes = _carregar("""
        SELECT id, nome, documento, tipo_pessoa, segmento, cidade, estado, data_cadastro
        FROM clientes
    """)
    g.query("""
        UNWIND $rows AS r
        CREATE (:Cliente {
            id: r.id,
            nome: r.nome,
            documento: r.documento,
            tipo_pessoa: r.tipo_pessoa,
            segmento: r.segmento,
            cidade: r.cidade,
            estado: r.estado,
            data_cadastro: r.data_cadastro
        })
    """, {"rows": clientes})

    advogados = _carregar("SELECT id, nome, oab, especialidade, email FROM advogados")
    g.query("""
        UNWIND $rows AS r
        CREATE (:Advogado {
            id: r.id,
            nome: r.nome,
            oab: r.oab,
            especialidade: r.especialidade,
            email: r.email
        })
    """, {"rows": advogados})

    vinculos = _carregar("""
        SELECT cliente_origem_id, nome_vinculado, documento_vinculado,
               tipo_vinculo, participacao_percentual
        FROM socios_e_vinculos
    """)
    g.query("""
        UNWIND $rows AS r
        MATCH (cli:Cliente {id: r.cliente_origem_id})
        MERGE (s:Socio {documento: r.documento_vinculado})
        ON CREATE SET s.nome = r.nome_vinculado
        CREATE (cli)-[:POSSUI_VINCULO {
            tipo: r.tipo_vinculo,
            participacao: r.participacao_percentual
        }]->(s)
    """, {"rows": vinculos})

    processos = _carregar("""
        SELECT id, numero_cnj, cliente_id, advogado_id, parte_contraria,
               area_direito, tribunal, valor_causa, risco_perda, status, proximo_prazo
        FROM processos
    """)
    g.query("""
        UNWIND $rows AS r
        MATCH (cli:Cliente {id: r.cliente_id}), (adv:Advogado {id: r.advogado_id})
        MERGE (pc:ParteContraria {nome: r.parte_contraria})
        CREATE (p:Processo {
            id: r.id,
            numero_cnj: r.numero_cnj,
            area_direito: r.area_direito,
            tribunal: r.tribunal,
            valor_causa: r.valor_causa,
            risco_perda: r.risco_perda,
            status: r.status,
            proximo_prazo: r.proximo_prazo
        })
        CREATE (cli)-[:PARTE_EM]->(p)
        CREATE (adv)-[:PATROCINA]->(p)
        CREATE (p)-[:CONTRA]->(pc)
    """, {"rows": processos})

    nos = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    arestas = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"Grafo Jurídico sincronizado no FalkorDB: {nos} nós e {arestas} arestas.")


if __name__ == "__main__":
    sincronizar()
