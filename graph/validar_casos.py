# ========================================================
# 🛡️ SENTINEL AI - VALIDAÇÃO DO GRAFO NOS 5 CASOS DE FRAUDE
# ========================================================
# Uso (a partir da raiz do projeto):
#   python -m graph.validar_casos
# ========================================================

import sys

from database.connection import execute_query
from graph import queries

sys.stdout.reconfigure(encoding="utf-8")


def main():
    alertas = execute_query("""
        SELECT a.id, a.tipo_alerta, a.conta_alvo_id, c.numero_conta
        FROM alertas_fraude a JOIN contas c ON c.id = a.conta_alvo_id
        ORDER BY a.id
    """)

    for a in alertas:
        print(f"\n{'=' * 70}\n🚨 Alerta #{a['id']} | {a['tipo_alerta']} | conta {a['numero_conta']}\n{'=' * 70}")
        cid = a["conta_alvo_id"]

        ciclos = queries.detectar_ciclos_financeiros(cid)
        print(f"🔁 Ciclos financeiros: {len(ciclos)}")
        for c in ciclos[:3]:
            print(f"   {' ➔ '.join(c['caminho'])} | valores {[t['valor'] for t in c['transferencias']]}")

        vinculos = queries.contas_com_mesmo_dispositivo_ou_ip(cid)
        print(f"📱 Contas no mesmo aparelho/IP: {len(vinculos)}")
        for v in vinculos:
            print(f"   [{v['tipo_vinculo']}] {v['identificador']} ➔ {v['conta']} ({v['titular']})")

        saida = queries.rastrear_fluxo_dinheiro(cid, "saida", 2)
        entrada = queries.rastrear_fluxo_dinheiro(cid, "entrada", 1)
        print(f"💸 Caminhos de saída (até 2 saltos): {len(saida)} | origens diretas: {len(entrada)}")
        for s in saida[:3]:
            print(f"   {' ➔ '.join(s['caminho'])} | {[t['valor'] for t in s['transferencias']]}")

    print(f"\n{'=' * 70}\n🏦 Contas coletoras (recebem de 3+ origens)\n{'=' * 70}")
    for r in queries.receptores_concentrados(min_origens=3, limite=5):
        print(f"   {r['conta']} | {r['titular']} | {r['origens']} origens | R$ {r['total_recebido']:,.2f}")


if __name__ == "__main__":
    main()
