CREATE DATABASE numero_de_serie
	DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE numero_de_serie;

CREATE TABLE ativos(
	ativo VARCHAR(100)NOT NULL,
    numero VARCHAR(100)NULL,
    categoria VARCHAR(100)NULL,
    status VARCHAR(100) NULL,
    matricula VARCHAR(100)NULL,
    data_garantia DATE NULL,
    dp VARCHAR(100)NULL,
    nome_responsavel VARCHAR(150)NULL,
    sede VARCHAR(100)NULL,
    
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE key uk_numero_serie(numero)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;