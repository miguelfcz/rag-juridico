-- ========================================================
-- 🛡️ SENTINEL AI - SCHEMA DO BANCO RELACIONAL (POSTGRESQL)
-- ========================================================

-- Limpar tabelas caso já existam (ordem reversa de dependência)
DROP TABLE IF EXISTS alertas_fraude CASCADE;
DROP TABLE IF EXISTS transacoes CASCADE;
DROP TABLE IF EXISTS acessos CASCADE;
DROP TABLE IF EXISTS dispositivos CASCADE;
DROP TABLE IF EXISTS contas CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;

-- 1. Clientes (Pessoas Físicas e Jurídicas)
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    documento VARCHAR(20) UNIQUE NOT NULL, -- CPF ou CNPJ (sintéticos)
    tipo_pessoa VARCHAR(2) NOT NULL CHECK (tipo_pessoa IN ('PF', 'PJ')),
    renda_declarada NUMERIC(15, 2) NOT NULL,
    ocupacao VARCHAR(100),
    data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE,
    data_abertura_empresa DATE, -- Relevante para PJs recentes (empresas de fachada)
    cidade VARCHAR(100),
    estado VARCHAR(2),
    score_credito INT DEFAULT 500
);

-- 2. Contas Bancárias
CREATE TABLE contas (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero_conta VARCHAR(20) UNIQUE NOT NULL,
    agencia VARCHAR(10) NOT NULL DEFAULT '0001',
    tipo_conta VARCHAR(20) NOT NULL DEFAULT 'CORRENTE' CHECK (tipo_conta IN ('CORRENTE', 'POUPANCA', 'PAGAMENTO')),
    saldo NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVA' CHECK (status IN ('ATIVA', 'BLOQUEADA_CAUTELAR', 'ENCERRADA', 'SOB_ANALISE')),
    data_abertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Dispositivos (Celulares, Computadores usados para login)
CREATE TABLE dispositivos (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE NOT NULL, -- Fingerprint único do aparelho
    modelo VARCHAR(100),
    sistema_operacional VARCHAR(50),
    data_primeiro_uso TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Acessos (Sessões / Logs de Login por Conta e Dispositivo)
CREATE TABLE acessos (
    id SERIAL PRIMARY KEY,
    conta_id INT NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    dispositivo_id INT NOT NULL REFERENCES dispositivos(id) ON DELETE CASCADE,
    ip_origem VARCHAR(45) NOT NULL,
    geolocalizacao VARCHAR(100),
    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Transações Financeiras (PIX, TED, Boleto)
CREATE TABLE transacoes (
    id SERIAL PRIMARY KEY,
    conta_origem_id INT NOT NULL REFERENCES contas(id),
    conta_destino_id INT NOT NULL REFERENCES contas(id),
    valor NUMERIC(15, 2) NOT NULL,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('PIX', 'TED', 'BOLETO')),
    chave_pix_destino VARCHAR(100),
    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'CONCLUIDA' CHECK (status IN ('CONCLUIDA', 'BLOQUEADA', 'REVERTIDA')),
    descricao TEXT
);

-- 6. Fila de Alertas de Fraude / PLD (A mesa de trabalho do analista)
CREATE TABLE alertas_fraude (
    id SERIAL PRIMARY KEY,
    conta_alvo_id INT NOT NULL REFERENCES contas(id),
    tipo_alerta VARCHAR(50) NOT NULL, -- 'SMURFING', 'CONTA_PASSAGEM', 'DISPOSITIVO_COMPARTILHADO', 'TRIANGULACAO', etc.
    score_risco INT NOT NULL CHECK (score_risco BETWEEN 0 AND 100),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE', 'EM_INVESTIGACAO', 'CONCLUIDO_COM_BLOQUEIO', 'FALSO_POSITIVO')),
    detalhes JSONB NOT NULL,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analise_ia TEXT -- Aqui a IA irá registrar o Dossiê e parecer final
);

-- Índices para otimização de consultas analíticas e MCP
CREATE INDEX idx_transacoes_origem ON transacoes(conta_origem_id);
CREATE INDEX idx_transacoes_destino ON transacoes(conta_destino_id);
CREATE INDEX idx_transacoes_data ON transacoes(data_hora);
CREATE INDEX idx_acessos_conta ON acessos(conta_id);
CREATE INDEX idx_acessos_dispositivo ON acessos(dispositivo_id);
CREATE INDEX idx_alertas_status ON alertas_fraude(status);
