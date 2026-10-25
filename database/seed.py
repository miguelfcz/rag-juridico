import os
import sys
import random
import json
from datetime import datetime, timedelta
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

    with get_db_connection() as conn:
        cur = conn.cursor()

        clientes_ids = []
        contas_ids = []

        for _ in range(120):
            is_pj = random.random() < 0.2
            if is_pj:
                doc = fake.cnpj()
                tipo = 'PJ'
                nome = fake.company()
                renda = round(random.uniform(15000, 250000), 2)
                ocupacao = "Comércio e Serviços"
                dt_empresa = fake.date_between(start_date='-10y', end_date='-1y')
            else:
                doc = fake.cpf()
                tipo = 'PF'
                nome = fake.name()
                renda = round(random.uniform(2000, 25000), 2)
                ocupacao = fake.job()[:90]
                dt_empresa = None

            cur.execute("""
                INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, data_abertura_empresa, cidade, estado, score_credito)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (nome, doc, tipo, renda, ocupacao, dt_empresa, fake.city(), fake.state_abbr(), random.randint(350, 950)))
            c_id = cur.fetchone()['id']
            clientes_ids.append(c_id)

            num_conta = f"{random.randint(10000, 99999)}-{random.randint(0, 9)}"
            cur.execute("""
                INSERT INTO contas (cliente_id, numero_conta, saldo, status, data_abertura)
                VALUES (%s, %s, %s, 'ATIVA', %s) RETURNING id
            """, (c_id, num_conta, round(random.uniform(500, 50000), 2), fake.date_time_between(start_date='-3y', end_date='-6m')))
            contas_ids.append(cur.fetchone()['id'])

        for i, c_id in enumerate(contas_ids):
            d_id = f"DEV_LEGITIMO_{i+1:04d}_{fake.uuid4()[:8]}"
            cur.execute("""
                INSERT INTO dispositivos (device_id, modelo, sistema_operacional)
                VALUES (%s, %s, %s) RETURNING id
            """, (d_id, random.choice(["iPhone 14", "Samsung Galaxy S23", "Motorola Edge", "Xiaomi 13"]), random.choice(["iOS", "Android"])))
            dev_id = cur.fetchone()['id']
            cur.execute("""
                INSERT INTO acessos (conta_id, dispositivo_id, ip_origem, geolocalizacao)
                VALUES (%s, %s, %s, %s)
            """, (c_id, dev_id, fake.ipv4(), f"{fake.city()} - {fake.state_abbr()}"))

        for _ in range(300):
            origem = random.choice(contas_ids)
            destino = random.choice(contas_ids)
            if origem != destino:
                val = round(random.uniform(20.0, 3500.0), 2)
                cur.execute("""
                    INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, chave_pix_destino, data_hora, status, descricao)
                    VALUES (%s, %s, %s, 'PIX', %s, %s, 'CONCLUIDA', %s)
                """, (origem, destino, val, fake.email(), fake.date_time_between(start_date='-30d', end_date='now'), "Pagamento de rotina"))

        # Caso 1: Smurfing (fracionamento abaixo de R$ 10k em janela noturna)
        cur.execute("""
            INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, cidade, estado, score_credito)
            VALUES ('Carlos Eduardo Peixoto (Suspeito)', '111.222.333-44', 'PF', 2800.00, 'Auxiliar de Almoxarifado', 'Campinas', 'SP', 420)
            RETURNING id
        """)
        c1_cliente_id = cur.fetchone()['id']
        cur.execute("""
            INSERT INTO contas (cliente_id, numero_conta, saldo, status)
            VALUES (%s, '99101-1', 450.00, 'ATIVA') RETURNING id
        """, (c1_cliente_id,))
        c1_conta_id = cur.fetchone()['id']

        cur.execute("""
            INSERT INTO dispositivos (device_id, modelo, sistema_operacional)
            VALUES ('DEV_SMURF_001_A998F', 'Samsung Galaxy A10', 'Android') RETURNING id
        """)
        dev_smurf_id = cur.fetchone()['id']
        cur.execute("INSERT INTO acessos (conta_id, dispositivo_id, ip_origem, geolocalizacao) VALUES (%s, %s, '187.54.12.89', 'Campinas - SP')", (c1_conta_id, dev_smurf_id))

        cur.execute("""
            INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, cidade, estado)
            VALUES ('Operador Receptor Desconhecido', '222.333.444-55', 'PF', 15000.00, 'Consultor Autônomo', 'São Paulo', 'SP') RETURNING id
        """)
        c1_dest_cli = cur.fetchone()['id']
        cur.execute("INSERT INTO contas (cliente_id, numero_conta, saldo) VALUES (%s, '88202-2', 58000.00) RETURNING id", (c1_dest_cli,))
        c1_dest_conta = cur.fetchone()['id']

        hora_smurf = datetime.now() - timedelta(days=1, hours=18)
        for i in range(5):
            cur.execute("""
                INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, chave_pix_destino, data_hora, status, descricao)
                VALUES (%s, %s, 9800.00, 'PIX', 'receptor@pagamento.com', %s, 'CONCLUIDA', 'Transferencia Pix')
            """, (c1_conta_id, c1_dest_conta, hora_smurf + timedelta(minutes=i*4)))

        cur.execute("""
            INSERT INTO alertas_fraude (conta_alvo_id, tipo_alerta, score_risco, status, detalhes)
            VALUES (%s, 'SMURFING', 92, 'PENDENTE', %s)
        """, (c1_conta_id, json.dumps({
            "motivo": "Múltiplas transferências de alto valor logo abaixo de R$ 10.000 em curto intervalo noturno",
            "qtd_transacoes": 5,
            "valor_total": 49000.00,
            "renda_declarada": 2800.00,
            "incompatibilidade": "Movimentação 17x maior que a renda mensal declarada"
        })))

        # Caso 2: Conta de passagem (recebe aporte alto e esvazia em minutos)
        cur.execute("""
            INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, cidade, estado)
            VALUES ('Juliana Mendes Castro (Estudante/Laranja)', '333.444.555-66', 'PF', 1200.00, 'Estudante Universitária', 'Belo Horizonte', 'MG')
            RETURNING id
        """)
        c2_cli = cur.fetchone()['id']
        cur.execute("INSERT INTO contas (cliente_id, numero_conta, saldo, data_abertura) VALUES (%s, '77303-3', 120.00, NOW() - INTERVAL '12 days') RETURNING id", (c2_cli,))
        c2_conta = cur.fetchone()['id']

        conta_origem_laranja = random.choice(contas_ids)
        conta_fim_laranja = random.choice(contas_ids)
        tempo_base = datetime.now() - timedelta(days=2)
        cur.execute("""
            INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao)
            VALUES (%s, %s, 75000.00, 'TED', %s, 'Aporte Financeiro')
        """, (conta_origem_laranja, c2_conta, tempo_base))
        cur.execute("""
            INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao)
            VALUES (%s, %s, 74800.00, 'PIX', %s, 'Repasse Imediato')
        """, (c2_conta, conta_fim_laranja, tempo_base + timedelta(minutes=6)))

        cur.execute("""
            INSERT INTO alertas_fraude (conta_alvo_id, tipo_alerta, score_risco, status, detalhes)
            VALUES (%s, 'CONTA_PASSAGEM', 96, 'PENDENTE', %s)
        """, (c2_conta, json.dumps({
            "motivo": "Conta recente com saldo quase zerado recebeu aporte atípico de R$ 75.000 e repassou 99.7% em 6 minutos",
            "tempo_retencao_minutos": 6,
            "renda_declarada": 1200.00
        })))

        # Caso 3: Dispositivo e IP compartilhados entre titulares distintos
        cur.execute("""
            INSERT INTO dispositivos (device_id, modelo, sistema_operacional)
            VALUES ('DEV_COMPARTILHADO_FRAUDE_X77', 'Xiaomi Poco X5 (Rooted)', 'Android Custom') RETURNING id
        """)
        dev_compartilhado_id = cur.fetchone()['id']
        ip_vpn_fraude = "45.181.24.11"

        contas_compartilhadas = []
        for i, nome_falso in enumerate(['Marcos Vinicius Lima', 'Tatiane Rocha Alves', 'Rodrigo Barreto Silva']):
            cur.execute("""
                INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, cidade, estado)
                VALUES (%s, %s, 'PF', 2500.00, 'Autônomo', 'Curitiba', 'PR') RETURNING id
            """, (nome_falso, f"444.555.66{i}-77"))
            cli_c3 = cur.fetchone()['id']
            cur.execute("INSERT INTO contas (cliente_id, numero_conta, saldo) VALUES (%s, %s, 12000.00) RETURNING id", (cli_c3, f"6640{i}-4"))
            cnt_c3 = cur.fetchone()['id']
            contas_compartilhadas.append(cnt_c3)

            cur.execute("""
                INSERT INTO acessos (conta_id, dispositivo_id, ip_origem, geolocalizacao)
                VALUES (%s, %s, %s, 'Curitiba - PR (VPN Datacenter)')
            """, (cnt_c3, dev_compartilhado_id, ip_vpn_fraude))

        cur.execute("""
            INSERT INTO alertas_fraude (conta_alvo_id, tipo_alerta, score_risco, status, detalhes)
            VALUES (%s, 'DISPOSITIVO_COMPARTILHADO', 88, 'PENDENTE', %s)
        """, (contas_compartilhadas[0], json.dumps({
            "motivo": "Mesmo identificador físico de aparelho (Device ID) e IP de VPN controlando 3 contas bancárias distintas de titulares sem parentesco",
            "device_id": "DEV_COMPARTILHADO_FRAUDE_X77",
            "ip": ip_vpn_fraude
        })))

        # Caso 4: Triangulação circular (A -> B -> C -> A)
        contas_ciclo = []
        for i, nome_ciclo in enumerate(['Empresa Alpha Log', 'Beta Servicos Digitais', 'Gamma Consultoria ME']):
            cur.execute("""
                INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, data_abertura_empresa, cidade, estado)
                VALUES (%s, %s, 'PJ', 60000.00, 'Serviços Terceirizados', NOW() - INTERVAL '6 months', 'Rio de Janeiro', 'RJ') RETURNING id
            """, (nome_ciclo, f"12.345.67{i}/0001-90"))
            cli_loop = cur.fetchone()['id']
            cur.execute("INSERT INTO contas (cliente_id, numero_conta, saldo) VALUES (%s, %s, 40000.00) RETURNING id", (cli_loop, f"5550{i}-5"))
            contas_ciclo.append(cur.fetchone()['id'])

        t_ciclo = datetime.now() - timedelta(days=3)
        cur.execute("INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao) VALUES (%s, %s, 30000.00, 'TED', %s, 'Prestacao de Servico')", (contas_ciclo[0], contas_ciclo[1], t_ciclo))
        cur.execute("INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao) VALUES (%s, %s, 29500.00, 'TED', %s, 'Subcontratacao')", (contas_ciclo[1], contas_ciclo[2], t_ciclo + timedelta(hours=2)))
        cur.execute("INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao) VALUES (%s, %s, 29000.00, 'TED', %s, 'Comissao Operacional')", (contas_ciclo[2], contas_ciclo[0], t_ciclo + timedelta(hours=4)))

        cur.execute("""
            INSERT INTO alertas_fraude (conta_alvo_id, tipo_alerta, score_risco, status, detalhes)
            VALUES (%s, 'TRIANGULACAO', 95, 'PENDENTE', %s)
        """, (contas_ciclo[0], json.dumps({
            "motivo": "Ciclo financeiro fechado detectado: o dinheiro saiu da Empresa Alpha, passou por duas outras e retornou para a Alpha com deságio de comissão em menos de 5 horas",
            "contas_envolvidas": contas_ciclo
        })))

        # Caso 5: Empresa de fachada recém-aberta atuando como conta coletora
        cur.execute("""
            INSERT INTO clientes (nome, documento, tipo_pessoa, renda_declarada, ocupacao, data_abertura_empresa, cidade, estado)
            VALUES ('Nexus Global Intermediações LTDA (Fantasma)', '99.888.777/0001-11', 'PJ', 10000.00, 'Consultoria Empresarial', NOW() - INTERVAL '5 days', 'Brasília', 'DF')
            RETURNING id
        """)
        c5_cli = cur.fetchone()['id']
        cur.execute("INSERT INTO contas (cliente_id, numero_conta, saldo, data_abertura) VALUES (%s, '11005-9', 240000.00, NOW() - INTERVAL '4 days') RETURNING id", (c5_cli,))
        c5_conta = cur.fetchone()['id']

        for i in range(4):
            cur.execute("""
                INSERT INTO transacoes (conta_origem_id, conta_destino_id, valor, tipo, data_hora, descricao)
                VALUES (%s, %s, 60000.00, 'TED', %s, 'Honorarios Consultoria')
            """, (random.choice(contas_ids), c5_conta, datetime.now() - timedelta(days=1, hours=i*3)))

        cur.execute("""
            INSERT INTO alertas_fraude (conta_alvo_id, tipo_alerta, score_risco, status, detalhes)
            VALUES (%s, 'EMPRESA_FACHADA', 98, 'PENDENTE', %s)
        """, (c5_conta, json.dumps({
            "motivo": "CNPJ com 5 dias de fundação e capital irrisório recebeu R$ 240.000 em 24 horas de múltiplas fontes sem histórico comercial prévio",
            "dias_fundacao": 5,
            "valor_total_recebido": 240000.00
        })))

    print("Banco PostgreSQL populado com sucesso.")


if __name__ == '__main__':
    popular_banco()
