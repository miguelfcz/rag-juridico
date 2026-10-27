DROP TABLE IF EXISTS contratos_honorarios CASCADE;
DROP TABLE IF EXISTS processos CASCADE;
DROP TABLE IF EXISTS socios_e_vinculos CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;
DROP TABLE IF EXISTS advogados CASCADE;

CREATE TABLE advogados (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    oab VARCHAR(30) UNIQUE NOT NULL,
    especialidade VARCHAR(60) NOT NULL,
    email VARCHAR(120)
);

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    documento VARCHAR(20) UNIQUE NOT NULL,
    tipo_pessoa VARCHAR(2) NOT NULL CHECK (tipo_pessoa IN ('PF', 'PJ')),
    segmento VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE socios_e_vinculos (
    id SERIAL PRIMARY KEY,
    cliente_origem_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome_vinculado VARCHAR(150) NOT NULL,
    documento_vinculado VARCHAR(20) NOT NULL,
    tipo_vinculo VARCHAR(50) NOT NULL, -- 'SOCIO_ADMINISTRADOR', 'HOLDING_CONTROLADORA', 'SUBSIDIARIA', 'REPRESENTANTE_LEGAL'
    participacao_percentual NUMERIC(5, 2) DEFAULT 0.00
);

CREATE TABLE processos (
    id SERIAL PRIMARY KEY,
    numero_cnj VARCHAR(35) UNIQUE NOT NULL,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    advogado_id INT NOT NULL REFERENCES advogados(id),
    parte_contraria VARCHAR(150) NOT NULL,
    area_direito VARCHAR(50) NOT NULL CHECK (area_direito IN ('TRABALHISTA', 'CIVEL', 'TRIBUTARIO', 'SOCIETARIO', 'CONSUMIDOR')),
    tribunal VARCHAR(50) NOT NULL,
    valor_causa NUMERIC(15, 2) NOT NULL,
    risco_perda VARCHAR(20) NOT NULL CHECK (risco_perda IN ('PROVAVEL', 'POSSIVEL', 'REMOTO')),
    status VARCHAR(30) NOT NULL CHECK (status IN ('ATIVO', 'SUSPENSO', 'ACORDO', 'ENCERRADO', 'RECURSO')),
    proximo_prazo DATE,
    resumo_objeto TEXT
);

CREATE TABLE contratos_honorarios (
    id SERIAL PRIMARY KEY,
    codigo_contrato VARCHAR(30) UNIQUE NOT NULL,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_contrato VARCHAR(50) NOT NULL, -- 'PARTIDO_MENSAL', 'EXITO_CONTENCIOSO', 'CONSULTORIA_SOCIETARIA'
    valor_mensal NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    percentual_exito NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    status_pagamento VARCHAR(30) NOT NULL CHECK (status_pagamento IN ('EM_DIA', 'EM_ATRASO', 'QUITADO')),
    data_assinatura DATE NOT NULL,
    data_vencimento DATE
);

CREATE INDEX idx_processos_cliente ON processos(cliente_id);
CREATE INDEX idx_processos_advogado ON processos(advogado_id);
CREATE INDEX idx_processos_area ON processos(area_direito);
CREATE INDEX idx_vinculos_cliente ON socios_e_vinculos(cliente_origem_id);
