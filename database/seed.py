import os
import sys
import random
from datetime import date, timedelta
from faker import Faker
from connection import get_db_connection

sys.stdout.reconfigure(encoding='utf-8')

fake = Faker('pt_BR')
Faker.seed(42)
random.seed(42)


def inicializar_schema():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)


def popular_banco():
    inicializar_schema()
    hoje = date.today()

    with get_db_connection() as conn:
        cur = conn.cursor()

        advogados_seed = [
            ("Dra. Helena Vasconcelos", "OAB/SP 245.890", "Societário e M&A", "helena.vasconcelos@banca.adv.br"),
            ("Dr. Ricardo Albuquerque", "OAB/SP 198.412", "Trabalhista Estratégico", "ricardo.albuquerque@banca.adv.br"),
            ("Dra. Beatriz Fontes", "OAB/RJ 167.320", "Tributário e Fiscal", "beatriz.fontes@banca.adv.br"),
            ("Dr. Marcelo Cavalcanti", "OAB/SP 312.501", "Contencioso Cível", "marcelo.cavalcanti@banca.adv.br"),
            ("Dra. Camila Montenegro", "OAB/MG 142.880", "Direito do Consumidor", "camila.montenegro@banca.adv.br"),
        ]

        advogados_ids = {}
        for nome, oab, esp, email in advogados_seed:
            cur.execute("""
                INSERT INTO advogados (nome, oab, especialidade, email)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (nome, oab, esp, email))
            advogados_ids[esp] = cur.fetchone()['id']

        clientes_principais = [
            ("Horizonte Logística S.A.", "12.456.789/0001-10", "PJ", "Transporte e Logística", "São Paulo", "SP", date(2021, 3, 15)),
            ("TransBrasil Cargas Ltda.", "12.456.789/0002-91", "PJ", "Transporte Rodoviário", "Campinas", "SP", date(2022, 6, 10)),
            ("Rota Sul Armazéns Gerais S.A.", "45.987.123/0001-55", "PJ", "Armazenagem e Portos", "Santos", "SP", date(2023, 1, 20)),
            ("Construtora Vanguarda S.A.", "33.221.445/0001-80", "PJ", "Construção Civil e Incorporação", "Rio de Janeiro", "RJ", date(2020, 8, 5)),
            ("Vanguarda SPE Empreendimentos Imobiliários Ltda.", "33.221.445/0002-61", "PJ", "Incorporação Imobiliária", "Niterói", "RJ", date(2022, 11, 12)),
            ("TechNova Pagamentos e Fintech S.A.", "67.890.123/0001-04", "PJ", "Tecnologia e Meios de Pagamento", "São Paulo", "SP", date(2023, 4, 2)),
            ("AgroVerde Exportadora de Grãos S.A.", "88.776.554/0001-33", "PJ", "Agronegócio", "Ribeirão Preto", "SP", date(2019, 10, 18)),
            ("Rede Saúde Vida Hospitais Ltda.", "55.443.221/0001-77", "PJ", "Saúde Suplementar", "Belo Horizonte", "MG", date(2021, 7, 25)),
            ("Eduardo Mendonça Ferraz", "289.451.778-09", "PF", "Investidor e Executivo", "São Paulo", "SP", date(2021, 3, 18)),
            ("Roberto Viana Almeida", "412.889.301-54", "PF", "Empresário do Setor Imobiliário", "Rio de Janeiro", "RJ", date(2020, 9, 1)),
        ]

        clientes_map = {}
        for nome, doc, tipo, seg, cid, uf, dt_cad in clientes_principais:
            cur.execute("""
                INSERT INTO clientes (nome, documento, tipo_pessoa, segmento, cidade, estado, data_cadastro)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (nome, doc, tipo, seg, cid, uf, dt_cad))
            clientes_map[nome] = cur.fetchone()['id']

        for _ in range(15):
            is_pj = random.random() < 0.7
            if is_pj:
                nome = fake.company()
                doc = fake.cnpj()
                tipo = "PJ"
                seg = random.choice(["Varejo", "Indústria Metalúrgica", "Comércio Exterior", "Serviços de TI", "Energia Solar"])
            else:
                nome = fake.name()
                doc = fake.cpf()
                tipo = "PF"
                seg = "Consultoria Particular"

            cur.execute("""
                INSERT INTO clientes (nome, documento, tipo_pessoa, segmento, cidade, estado, data_cadastro)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (nome, doc, tipo, seg, fake.city(), fake.state_abbr(), fake.date_between(start_date='-4y', end_date='-3m')))
            clientes_map[nome] = cur.fetchone()['id']

        vinculos_seed = [
            # Grupo Econômico Logístico (Eduardo Mendonça Ferraz e Atlas Holding controlam 3 empresas)
            (clientes_map["Horizonte Logística S.A."], "Eduardo Mendonça Ferraz", "289.451.778-09", "SOCIO_ADMINISTRADOR", 45.00),
            (clientes_map["Horizonte Logística S.A."], "Atlas Participações Holding S.A.", "90.111.222/0001-00", "HOLDING_CONTROLADORA", 55.00),
            (clientes_map["TransBrasil Cargas Ltda."], "Eduardo Mendonça Ferraz", "289.451.778-09", "SOCIO_ADMINISTRADOR", 60.00),
            (clientes_map["TransBrasil Cargas Ltda."], "Atlas Participações Holding S.A.", "90.111.222/0001-00", "HOLDING_CONTROLADORA", 40.00),
            (clientes_map["Rota Sul Armazéns Gerais S.A."], "Eduardo Mendonça Ferraz", "289.451.778-09", "REPRESENTANTE_LEGAL", 25.00),
            (clientes_map["Rota Sul Armazéns Gerais S.A."], "Horizonte Logística S.A.", "12.456.789/0001-10", "HOLDING_CONTROLADORA", 75.00),

            # Grupo Imobiliário Vanguarda (Roberto Viana Almeida)
            (clientes_map["Construtora Vanguarda S.A."], "Roberto Viana Almeida", "412.889.301-54", "SOCIO_ADMINISTRADOR", 70.00),
            (clientes_map["Construtora Vanguarda S.A."], "Vanguarda SPE Empreendimentos Imobiliários Ltda.", "33.221.445/0002-61", "SUBSIDIARIA", 100.00),
            (clientes_map["Vanguarda SPE Empreendimentos Imobiliários Ltda."], "Roberto Viana Almeida", "412.889.301-54", "SOCIO_ADMINISTRADOR", 50.00),
            (clientes_map["Vanguarda SPE Empreendimentos Imobiliários Ltda."], "Construtora Vanguarda S.A.", "33.221.445/0001-80", "HOLDING_CONTROLADORA", 50.00),

            # Outras empresas com sócios cruzados
            (clientes_map["TechNova Pagamentos e Fintech S.A."], "Atlas Participações Holding S.A.", "90.111.222/0001-00", "HOLDING_CONTROLADORA", 35.00),
            (clientes_map["TechNova Pagamentos e Fintech S.A."], "Lucas Silveira Prado", "334.556.778-11", "SOCIO_ADMINISTRADOR", 65.00),
            (clientes_map["AgroVerde Exportadora de Grãos S.A."], "Henrique Junqueira Mattos", "556.778.990-22", "SOCIO_ADMINISTRADOR", 80.00),
            (clientes_map["Rede Saúde Vida Hospitais Ltda."], "Fernanda Nogueira Bastos", "778.112.334-66", "SOCIO_ADMINISTRADOR", 50.00),
        ]

        for cli_id, nome_vinc, doc_vinc, tipo_vinc, perc in vinculos_seed:
            cur.execute("""
                INSERT INTO socios_e_vinculos (cliente_origem_id, nome_vinculado, documento_vinculado, tipo_vinculo, participacao_percentual)
                VALUES (%s, %s, %s, %s, %s)
            """, (cli_id, nome_vinc, doc_vinc, tipo_vinc, perc))

        processos_seed = [
            (
                "1004521-88.2024.5.02.0014",
                clientes_map["Horizonte Logística S.A."],
                advogados_ids["Trabalhista Estratégico"],
                "Sindicato dos Motoristas e Trabalhadores em Transportes de SP",
                "TRABALHISTA",
                "TRT-2",
                1450000.00,
                "PROVAVEL",
                "ATIVO",
                hoje + timedelta(days=5),
                "Ação coletiva cobrando horas extras, adicional noturno e reconhecimento de grupo econômico solidário com TransBrasil Cargas e Rota Sul Armazéns (Art. 2º, §2º da CLT)."
            ),
            (
                "1008932-11.2024.5.15.0092",
                clientes_map["TransBrasil Cargas Ltda."],
                advogados_ids["Trabalhista Estratégico"],
                "Sindicato dos Motoristas e Trabalhadores em Transportes de SP",
                "TRABALHISTA",
                "TRT-15",
                890000.00,
                "PROVAVEL",
                "RECURSO",
                hoje + timedelta(days=8),
                "Reclamação trabalhista com pedido de responsabilidade solidária do grupo econômico controlado por Eduardo Mendonça Ferraz e Atlas Participações."
            ),
            (
                "0023410-55.2023.8.26.0562",
                clientes_map["Rota Sul Armazéns Gerais S.A."],
                advogados_ids["Contencioso Cível"],
                "Porto Atlântico Operações Marítimas S.A.",
                "CIVEL",
                "TJSP",
                2300000.00,
                "POSSIVEL",
                "ATIVO",
                hoje + timedelta(days=12),
                "Ação indenizatória por rescisão antecipada de contrato de armazenagem portuária e cobrança de cláusula penal compensatória."
            ),
            (
                "5011290-74.2023.4.03.6100",
                clientes_map["Horizonte Logística S.A."],
                advogados_ids["Tributário e Fiscal"],
                "União Federal (Fazenda Nacional)",
                "TRIBUTARIO",
                "TRF-3",
                4800000.00,
                "POSSIVEL",
                "SUSPENSO",
                hoje + timedelta(days=25),
                "Execução fiscal referente a créditos de PIS/COFINS sobre insumos de frota e combustível (Tema 779 STJ), com garantia via seguro-garantia judicial."
            ),
            (
                "0087412-30.2024.8.19.0001",
                clientes_map["Construtora Vanguarda S.A."],
                advogados_ids["Contencioso Cível"],
                "Condomínio Edifício Reserva do Parque",
                "CIVEL",
                "TJRJ",
                3100000.00,
                "PROVAVEL",
                "ATIVO",
                hoje + timedelta(days=3),
                "Ação de obrigação de fazer cumulada com indenização por vícios construtivos e atraso na entrega de obra (Art. 43-A da Lei 4.591/64), com pedido de desconsideração da personalidade jurídica (Art. 50 do CC) para atingir a Vanguarda SPE."
            ),
            (
                "0019283-44.2024.8.19.0002",
                clientes_map["Vanguarda SPE Empreendimentos Imobiliários Ltda."],
                advogados_ids["Direito do Consumidor"],
                "Associação dos Adquirentes do Residencial Baía Sul",
                "CONSUMIDOR",
                "TJRJ",
                1250000.00,
                "PROVAVEL",
                "ACORDO",
                hoje + timedelta(days=15),
                "Ação revisional de distrato imobiliário discutindo limite de retenção de valores pagos e multa moratória por atraso superior a 180 dias."
            ),
            (
                "1045998-22.2024.8.26.0100",
                clientes_map["TechNova Pagamentos e Fintech S.A."],
                advogados_ids["Societário e M&A"],
                "Fundo Venture Capital Latam II FIP",
                "SOCIETARIO",
                "TJSP",
                6500000.00,
                "POSSIVEL",
                "ATIVO",
                hoje + timedelta(days=7),
                "Procedimento cautelar pré-arbitral sobre exercício de cláusula de Tag Along, diluição societária e acordo de acionistas."
            ),
            (
                "5004811-19.2023.4.03.6102",
                clientes_map["AgroVerde Exportadora de Grãos S.A."],
                advogados_ids["Tributário e Fiscal"],
                "Estado de São Paulo (Fazenda Estadual)",
                "TRIBUTARIO",
                "TJSP",
                3900000.00,
                "REMOTO",
                "ATIVO",
                hoje + timedelta(days=19),
                "Mandado de Segurança para afastar incidência de ICMS sobre operações de exportação indireta de soja e milho."
            ),
            (
                "1022341-09.2024.8.13.0024",
                clientes_map["Rede Saúde Vida Hospitais Ltda."],
                advogados_ids["Direito do Consumidor"],
                "Ministério Público do Estado de Minas Gerais",
                "CONSUMIDOR",
                "TJMG",
                980000.00,
                "POSSIVEL",
                "RECURSO",
                hoje + timedelta(days=10),
                "Ação Civil Pública questionando reajustes por sinistralidade em contratos coletivos empresariais e cobertura de tratamentos de alta complexidade."
            ),
            (
                "1056712-90.2024.8.26.0100",
                clientes_map["Eduardo Mendonça Ferraz"],
                advogados_ids["Societário e M&A"],
                "Credores Quirografários Logística SP",
                "SOCIETARIO",
                "TJSP",
                1750000.00,
                "POSSIVEL",
                "ATIVO",
                hoje + timedelta(days=4),
                "Incidente de Desconsideração da Personalidade Jurídica (IDPJ - Arts. 133 a 137 do CPC) alegando confusão patrimonial entre o sócio pessoa física e as empresas do grupo logístico."
            ),
        ]

        for num_cnj, cli_id, adv_id, parte, area, trib, valor, risco, status, prazo, resumo in processos_seed:
            cur.execute("""
                INSERT INTO processos (
                    numero_cnj, cliente_id, advogado_id, parte_contraria, area_direito,
                    tribunal, valor_causa, risco_perda, status, proximo_prazo, resumo_objeto
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (num_cnj, cli_id, adv_id, parte, area, trib, valor, risco, status, prazo, resumo))

        contratos_seed = [
            ("HON-2024-001", clientes_map["Horizonte Logística S.A."], "PARTIDO_MENSAL", 35000.00, 10.00, "EM_DIA", date(2024, 1, 10), date(2026, 1, 10)),
            ("HON-2024-002", clientes_map["TransBrasil Cargas Ltda."], "PARTIDO_MENSAL", 18000.00, 12.00, "EM_ATRASO", date(2024, 2, 1), date(2026, 2, 1)),
            ("HON-2024-003", clientes_map["Rota Sul Armazéns Gerais S.A."], "EXITO_CONTENCIOSO", 8000.00, 15.00, "EM_DIA", date(2023, 6, 15), date(2025, 12, 31)),
            ("HON-2024-004", clientes_map["Construtora Vanguarda S.A."], "PARTIDO_MENSAL", 42000.00, 10.00, "EM_ATRASO", date(2023, 9, 1), date(2025, 9, 1)),
            ("HON-2024-005", clientes_map["Vanguarda SPE Empreendimentos Imobiliários Ltda."], "EXITO_CONTENCIOSO", 5000.00, 18.00, "EM_DIA", date(2024, 3, 20), date(2026, 3, 20)),
            ("HON-2024-006", clientes_map["TechNova Pagamentos e Fintech S.A."], "CONSULTORIA_SOCIETARIA", 28000.00, 8.00, "EM_DIA", date(2024, 4, 15), date(2025, 10, 15)),
            ("HON-2024-007", clientes_map["AgroVerde Exportadora de Grãos S.A."], "EXITO_CONTENCIOSO", 15000.00, 15.00, "QUITADO", date(2023, 5, 10), date(2025, 5, 10)),
            ("HON-2024-008", clientes_map["Rede Saúde Vida Hospitais Ltda."], "PARTIDO_MENSAL", 25000.00, 10.00, "EM_DIA", date(2024, 1, 20), date(2026, 1, 20)),
        ]

        for cod, cli_id, tipo_c, v_mensal, p_exito, st_pag, dt_ass, dt_venc in contratos_seed:
            cur.execute("""
                INSERT INTO contratos_honorarios (
                    codigo_contrato, cliente_id, tipo_contrato, valor_mensal,
                    percentual_exito, status_pagamento, data_assinatura, data_vencimento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cod, cli_id, tipo_c, v_mensal, p_exito, st_pag, dt_ass, dt_venc))

    print("Banco PostgreSQL Jurídico populado com sucesso.")


if __name__ == '__main__':
    popular_banco()
