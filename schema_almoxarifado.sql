-- Schema de banco de dados para controle de almoxarifado
-- Equipamentos por Unidade + Insumos Centralizados
-- SQLite compatível com Python/Flask

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    papel TEXT NOT NULL DEFAULT 'administrador',
    ativo INTEGER NOT NULL DEFAULT 1,
    primeiro_acesso INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email
ON usuarios (email);

-- Tabela de Unidades
CREATE TABLE IF NOT EXISTS unidades (
    id_unidade INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    grupo_rede TEXT,
    tipo_unidade TEXT,
    endereco TEXT,
    ativo BOOLEAN DEFAULT 1
);

-- Tabela de Equipamentos
CREATE TABLE IF NOT EXISTS equipamentos (
    id_equipamento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_unidade INTEGER NOT NULL,
    patrimonio TEXT NOT NULL,
    nome TEXT,
    modelo TEXT,
    marca TEXT,
    numero_serie TEXT,
    data_entrada DATE,
    situacao TEXT,
    observacao TEXT,

    FOREIGN KEY (id_unidade)
        REFERENCES unidades(id_unidade)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    UNIQUE(id_unidade, patrimonio)
);

-- Tabela de Insumos
CREATE TABLE IF NOT EXISTS insumos (
    id_insumo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_unidade INTEGER,
    modelo TEXT,
    marca TEXT,
    numero_serie TEXT,
    quantidade INTEGER DEFAULT 0,
    data_entrega DATE,
    data_fabricacao DATE,
    vencimento DATE,
    localizacao TEXT,
    observacao TEXT,

    FOREIGN KEY (id_unidade)
        REFERENCES unidades(id_unidade)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- Tabela de Movimentações
CREATE TABLE IF NOT EXISTS movimentacoes (
    id_movimentacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_insumo INTEGER NOT NULL,
    id_unidade_origem INTEGER,
    id_unidade_destino INTEGER,
    quantidade INTEGER NOT NULL,
    data_movimentacao DATE DEFAULT CURRENT_DATE,
    tipo TEXT,
    observacao TEXT,

    FOREIGN KEY (id_insumo)
        REFERENCES insumos(id_insumo),

    FOREIGN KEY (id_unidade_origem)
        REFERENCES unidades(id_unidade),

    FOREIGN KEY (id_unidade_destino)
        REFERENCES unidades(id_unidade)
);

-- Índices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_equipamentos_unidade
ON equipamentos(id_unidade);

CREATE INDEX IF NOT EXISTS idx_insumos_vencimento
ON insumos(vencimento);

CREATE INDEX IF NOT EXISTS idx_insumos_unidade
ON insumos(id_unidade);