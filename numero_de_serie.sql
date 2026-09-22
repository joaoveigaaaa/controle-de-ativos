CREATE DATABASE numero_de_serie
    CHARACTER SET utf8mb4;

USE numero_de_serie;

CREATE TABLE ativo (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ativo VARCHAR(100) NOT NULL,
    numero_serie VARCHAR(100) NOT NULL,
    categoria VARCHAR(100),
    status VARCHAR(100),
    matricula VARCHAR(50),
    data_garantia DATE,
    dp VARCHAR(100),
    nome_responsavel VARCHAR(150),
    sede VARCHAR(100),

    INDEX idx_numero_serie (numero_serie)
);

