from graph.connection import get_graph


def _rows(result) -> list:
    colunas = [c[1] if isinstance(c, (list, tuple)) else c for c in result.header]
    return [dict(zip(colunas, linha)) for linha in result.result_set]


def detectar_grupos_economicos() -> list:
    q = """
        MATCH (c1:Cliente)-[v1:POSSUI_VINCULO]->(s:Socio)<-[v2:POSSUI_VINCULO]-(c2:Cliente)
        WHERE c1.nome < c2.nome
        RETURN s.nome AS socio_ou_holding_comum,
               s.documento AS documento_vinculo,
               c1.nome AS empresa_1,
               v1.tipo AS vinculo_empresa_1,
               v1.participacao AS participacao_1,
               c2.nome AS empresa_2,
               v2.tipo AS vinculo_empresa_2,
               v2.participacao AS participacao_2
        ORDER BY socio_ou_holding_comum
    """
    return _rows(get_graph().query(q))


def listar_clientes_grafo() -> list:
    q = """
        MATCH (c:Cliente)
        WHERE (c)-[:POSSUI_VINCULO]->() OR (c)-[:PARTE_EM]->()
        RETURN DISTINCT c.nome AS nome
        ORDER BY c.nome
    """
    return [r["nome"] for r in _rows(get_graph().query(q))]


def mapear_rede_cliente(termo_cliente: str) -> dict:
    g = get_graph()

    socios_q = """
        MATCH (c:Cliente)-[v:POSSUI_VINCULO]->(s:Socio)
        WHERE toLower(c.nome) CONTAINS toLower($termo) OR c.documento CONTAINS $termo
        OPTIONAL MATCH (outra:Cliente)-[v2:POSSUI_VINCULO]->(s)
        WHERE outra <> c
        RETURN c.nome AS cliente,
               s.nome AS vinculado,
               s.documento AS documento_vinculado,
               v.tipo AS tipo_vinculo,
               v.participacao AS percentual,
               collect(DISTINCT outra.nome) AS outras_empresas_mesmo_socio
    """
    processos_q = """
        MATCH (c:Cliente)-[:PARTE_EM]->(p:Processo)-[:CONTRA]->(pc:ParteContraria)
        MATCH (adv:Advogado)-[:PATROCINA]->(p)
        WHERE toLower(c.nome) CONTAINS toLower($termo) OR c.documento CONTAINS $termo
        RETURN c.nome AS cliente,
               p.numero_cnj AS numero_cnj,
               p.area_direito AS area_direito,
               p.tribunal AS tribunal,
               p.valor_causa AS valor_causa,
               p.risco_perda AS risco_perda,
               p.status AS status,
               pc.nome AS parte_contraria,
               adv.nome AS advogado_responsavel
    """
    return {
        "vinculos_societarios": _rows(g.query(socios_q, {"termo": termo_cliente})),
        "processos_conectados": _rows(g.query(processos_q, {"termo": termo_cliente})),
    }


def partes_contrarias_recorrentes() -> list:
    q = """
        MATCH (c:Cliente)-[:PARTE_EM]->(p:Processo)-[:CONTRA]->(pc:ParteContraria)
        WITH pc, count(p) AS qtd_processos, sum(p.valor_causa) AS valor_total_disputado,
             collect(DISTINCT c.nome) AS clientes_afetados
        RETURN pc.nome AS parte_contraria,
               qtd_processos,
               valor_total_disputado,
               clientes_afetados
        ORDER BY qtd_processos DESC, valor_total_disputado DESC
    """
    return _rows(get_graph().query(q))


def obter_subgrafo_visualizacao(termo_busca: str = "") -> dict:
    g = get_graph()

    if termo_busca and termo_busca.strip():
        q_socios = """
            MATCH (c:Cliente)-[v:POSSUI_VINCULO]->(s:Socio)
            OPTIONAL MATCH (c2:Cliente)-[v2:POSSUI_VINCULO]->(s)
            WHERE toLower(c.nome) CONTAINS toLower($filtro)
               OR toLower(c.segmento) CONTAINS toLower($filtro)
               OR toLower(s.nome) CONTAINS toLower($filtro)
               OR toLower(s.documento) CONTAINS toLower($filtro)
               OR toLower(v.tipo) CONTAINS toLower($filtro)
               OR (c2 IS NOT NULL AND toLower(c2.nome) CONTAINS toLower($filtro))
            RETURN c.id AS c1_id, c.nome AS c1_nome, c.segmento AS c1_seg,
                   s.documento AS s_doc, s.nome AS s_nome, v.tipo AS v1_tipo, v.participacao AS v1_part,
                   c2.id AS c2_id, c2.nome AS c2_nome, v2.tipo AS v2_tipo, v2.participacao AS v2_part
        """
        q_proc = """
            MATCH (c:Cliente)-[:PARTE_EM]->(p:Processo)-[:CONTRA]->(pc:ParteContraria)
            MATCH (adv:Advogado)-[:PATROCINA]->(p)
            WHERE toLower(c.nome) CONTAINS toLower($filtro)
               OR toLower(p.numero_cnj) CONTAINS toLower($filtro)
               OR toLower(p.area_direito) CONTAINS toLower($filtro)
               OR toLower(p.tribunal) CONTAINS toLower($filtro)
               OR toLower(p.risco_perda) CONTAINS toLower($filtro)
               OR toLower(pc.nome) CONTAINS toLower($filtro)
               OR toLower(adv.nome) CONTAINS toLower($filtro)
            RETURN c.id AS c_id, c.nome AS c_nome,
                   p.numero_cnj AS cnj, p.area_direito AS area, p.valor_causa AS valor, p.risco_perda AS risco,
                   pc.nome AS parte_contraria,
                   adv.id AS adv_id, adv.nome AS adv_nome, adv.especialidade AS adv_esp
        """
        params = {"filtro": termo_busca.strip()}
    else:
        q_socios = """
            MATCH (c:Cliente)-[v:POSSUI_VINCULO]->(s:Socio)
            OPTIONAL MATCH (c2:Cliente)-[v2:POSSUI_VINCULO]->(s)
            RETURN c.id AS c1_id, c.nome AS c1_nome, c.segmento AS c1_seg,
                   s.documento AS s_doc, s.nome AS s_nome, v.tipo AS v1_tipo, v.participacao AS v1_part,
                   c2.id AS c2_id, c2.nome AS c2_nome, v2.tipo AS v2_tipo, v2.participacao AS v2_part
        """
        q_proc = """
            MATCH (c:Cliente)-[:PARTE_EM]->(p:Processo)-[:CONTRA]->(pc:ParteContraria)
            MATCH (adv:Advogado)-[:PATROCINA]->(p)
            RETURN c.id AS c_id, c.nome AS c_nome,
                   p.numero_cnj AS cnj, p.area_direito AS area, p.valor_causa AS valor, p.risco_perda AS risco,
                   pc.nome AS parte_contraria,
                   adv.id AS adv_id, adv.nome AS adv_nome, adv.especialidade AS adv_esp
        """
        params = {}

    return {
        "socios": _rows(g.query(q_socios, params)),
        "processos": _rows(g.query(q_proc, params)),
    }


def listar_documentos_com_grafo() -> list:
    q = """
        MATCH (d:DocumentoGrafo)
        RETURN DISTINCT d.nome AS nome
        ORDER BY d.nome
    """
    return [r["nome"] for r in _rows(get_graph().query(q))]


def obter_grafo_de_documento(nome_documento: str = "", termo_busca: str = "") -> list:
    g = get_graph()
    filtro_doc = nome_documento if (nome_documento and not nome_documento.startswith("Todos")) else ""
    termo = termo_busca.strip() if termo_busca else ""

    q = """
        MATCH (o:EntidadeDoc)-[r:RELACAO_DOC]->(dst:EntidadeDoc)
        WHERE ($doc = '' OR o.documento = $doc)
          AND (
              $termo = ''
              OR toLower(o.nome) CONTAINS toLower($termo)
              OR toLower(dst.nome) CONTAINS toLower($termo)
              OR toLower(r.tipo) CONTAINS toLower($termo)
              OR toLower(o.tipo) CONTAINS toLower($termo)
              OR toLower(dst.tipo) CONTAINS toLower($termo)
          )
        RETURN o.documento AS documento,
               o.nome AS origem,
               o.tipo AS tipo_origem,
               r.tipo AS relacao,
               dst.nome AS destino,
               dst.tipo AS tipo_destino
    """
    return _rows(g.query(q, {"doc": filtro_doc, "termo": termo}))

