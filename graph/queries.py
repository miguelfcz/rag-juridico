# ========================================================
# 🛡️ SENTINEL AI - CONSULTAS CYPHER DE INVESTIGAÇÃO
# ========================================================
# Cada função responde uma pergunta que o SQL não responde bem,
# porque exige atravessar várias relações em sequência.
# Essas funções serão expostas ao agente como ferramentas (Etapa 5).
# ========================================================

from graph.connection import get_graph


def _rows(result) -> list:
    """Converte o result_set do FalkorDB em lista de dicionários."""
    colunas = [c[1] if isinstance(c, (list, tuple)) else c for c in result.header]
    return [dict(zip(colunas, linha)) for linha in result.result_set]


def _validar_saltos(n: int, maximo: int = 5) -> int:
    # Cypher não aceita parâmetro no tamanho do caminho (*1..N),
    # então o número entra na string e precisa ser validado.
    n = int(n)
    if not 1 <= n <= maximo:
        raise ValueError(f"Número de saltos deve estar entre 1 e {maximo}")
    return n


# Retorno padrão de um caminho de dinheiro.
# Obs.: no FalkorDB, nodes(p) e relationships(p) podem vir fora de ordem em
# caminhos de tamanho variável (principalmente cíclicos). Por isso cada aresta
# traz origem/destino explícitos (startNode/endNode) e a ordem é reconstruída em Python.
_TRANSFERENCIAS = "[r IN relationships(p) | [startNode(r).numero, endNode(r).numero, r.valor, r.data_hora]]"


def _encadear(trechos: list, inicio: str = None) -> list:
    """Ordena as transferências para que o destino de cada uma seja a origem da próxima."""
    restantes = list(trechos)
    if inicio is None:
        destinos = {t["destino"] for t in restantes}
        sem_antecessor = [t for t in restantes if t["origem"] not in destinos]
        primeiro = sem_antecessor[0] if sem_antecessor else restantes[0]
    else:
        primeiro = next(t for t in restantes if t["origem"] == inicio)
    ordenados = [primeiro]
    restantes.remove(primeiro)
    while restantes:
        proximo = next((t for t in restantes if t["origem"] == ordenados[-1]["destino"]), None)
        if proximo is None:
            break
        ordenados.append(proximo)
        restantes.remove(proximo)
    return ordenados


def _formatar_caminho(linha: dict, inicio: str = None) -> dict:
    trechos = [
        {"origem": o, "destino": d, "valor": v, "data_hora": dt}
        for o, d, v, dt in linha.pop("transferencias")
    ]
    trechos = _encadear(trechos, inicio)
    linha["caminho"] = [trechos[0]["origem"]] + [t["destino"] for t in trechos]
    linha["transferencias"] = trechos
    return linha


def detectar_ciclos_financeiros(conta_id: int, max_saltos: int = 4) -> list:
    """Dinheiro que sai da conta e volta para ela passando por intermediários (A ➔ B ➔ C ➔ A)."""
    n = _validar_saltos(max_saltos)
    q = f"""
        MATCH p = (c:Conta {{id: $id}})-[:TRANSFERIU*2..{n}]->(c)
        RETURN c.numero AS inicio, {_TRANSFERENCIAS} AS transferencias
        LIMIT 20
    """
    linhas = _rows(get_graph().query(q, {"id": conta_id}))
    return [_formatar_caminho(l, inicio=l.pop("inicio")) for l in linhas]


def contas_com_mesmo_dispositivo_ou_ip(conta_id: int) -> list:
    """Outras contas que usaram o mesmo aparelho ou o mesmo IP (indício de controle por uma só pessoa)."""
    q = """
        MATCH (c:Conta {id: $id})-[:ACESSOU_VIA|CONECTOU_DE]->(x)<-[:ACESSOU_VIA|CONECTOU_DE]-(outra:Conta)
        WHERE outra <> c
        MATCH (cli:Cliente)-[:TITULAR_DE]->(outra)
        RETURN labels(x)[0] AS tipo_vinculo,
               coalesce(x.device_id, x.endereco) AS identificador,
               outra.numero AS conta,
               cli.nome AS titular,
               cli.documento AS documento
    """
    return _rows(get_graph().query(q, {"id": conta_id}))


def rastrear_fluxo_dinheiro(conta_id: int, direcao: str = "saida", max_saltos: int = 3) -> list:
    """Segue o dinheiro a partir da conta: para onde foi (saida) ou de onde veio (entrada)."""
    n = _validar_saltos(max_saltos)
    if direcao == "saida":
        padrao = f"(c:Conta {{id: $id}})-[:TRANSFERIU*1..{n}]->(fim:Conta)"
    elif direcao == "entrada":
        padrao = f"(fim:Conta)-[:TRANSFERIU*1..{n}]->(c:Conta {{id: $id}})"
    else:
        raise ValueError("direcao deve ser 'saida' ou 'entrada'")
    q = f"""
        MATCH p = {padrao}
        RETURN c.numero AS conta_investigada, {_TRANSFERENCIAS} AS transferencias, length(p) AS saltos
        ORDER BY saltos
        LIMIT 30
    """
    linhas = _rows(get_graph().query(q, {"id": conta_id}))
    resultado = []
    for l in linhas:
        conta = l.pop("conta_investigada")
        resultado.append(_formatar_caminho(l, inicio=conta if direcao == "saida" else None))
    return resultado


def receptores_concentrados(min_origens: int = 3, limite: int = 10) -> list:
    """Contas que recebem de muitas origens diferentes (padrão de conta coletora / empresa de fachada)."""
    q = """
        MATCH (o:Conta)-[t:TRANSFERIU]->(d:Conta)<-[:TITULAR_DE]-(cli:Cliente)
        WITH d, cli, count(DISTINCT o) AS origens, sum(t.valor) AS total_recebido
        WHERE origens >= $min
        RETURN d.numero AS conta, cli.nome AS titular, cli.tipo_pessoa AS tipo,
               cli.data_abertura_empresa AS abertura_empresa,
               origens, total_recebido
        ORDER BY total_recebido DESC
        LIMIT $limite
    """
    return _rows(get_graph().query(q, {"min": min_origens, "limite": limite}))
