from datetime import date, datetime
from decimal import Decimal
import json
import logging
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import mysql.connector
from werkzeug.exceptions import HTTPException

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')


def create_app(settings=None, connector=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 21 * 1024 * 1024
    env = dict(os.environ) if settings is None else dict(settings)
    aliases = {'MYSQL_HOST': 'DB_HOST', 'MYSQL_PORT': 'DB_PORT', 'MYSQL_DATABASE': 'DB_NAME',
               'MYSQL_USER': 'DB_USER', 'MYSQL_PASSWORD': 'DB_PASSWORD'}
    for target, source in aliases.items():
        if not env.get(target) and env.get(source):
            env[target] = env[source]
    if not env.get('MYSQL_DATABASE') and env.get('MYSQL_DB'):
        env['MYSQL_DATABASE'] = env['MYSQL_DB']
    env.setdefault('MYSQL_TABLE', 'numero_de_serie')
    env.setdefault('MYSQL_SERIAL_COLUMN', 'ativos')
    connect = connector or mysql.connector.connect

    def configuration():
        required = ['MYSQL_HOST', 'MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_TABLE', 'MYSQL_SERIAL_COLUMN']
        missing = [name for name in required if not env.get(name, '').strip()]
        if missing:
            raise ValueError('Preencha no arquivo .env: ' + ', '.join(missing) + '.')
        table = env['MYSQL_TABLE'].strip()
        serial_column = env['MYSQL_SERIAL_COLUMN'].strip()
        for identifier in (table, serial_column):
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', identifier):
                raise ValueError('Use nomes simples de tabela e coluna na configuração do MySQL.')
        try:
            port = int(env.get('MYSQL_PORT', '3306'))
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            raise ValueError('MYSQL_PORT deve ser uma porta entre 1 e 65535.') from None
        options = dict(host=env['MYSQL_HOST'].strip(), port=port,
                       database=env['MYSQL_DATABASE'].strip(), user=env['MYSQL_USER'].strip(),
                       password=env.get('MYSQL_PASSWORD', ''), connection_timeout=5,
                       read_timeout=10, write_timeout=10, autocommit=True)
        if env.get('MYSQL_SSL_CA'):
            options.update(ssl_ca=env['MYSQL_SSL_CA'], ssl_verify_cert=True, ssl_verify_identity=True)
        return options, table, serial_column

    @app.before_request
    def local_only():
        if request.method == 'POST' and request.headers.get('Origin') not in (None, request.host_url.rstrip('/')):
            return jsonify(erro='Origem da solicitação inválida.'), 403
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            return jsonify(erro='Abra o sistema pelo endereço local.'), 403

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
                                 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'"})
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(erro='Solicitação inválida.'), error.code

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(erro=str(error)), 400

    @app.errorhandler(mysql.connector.Error)
    def mysql_error(error):
        app.logger.warning('Falha MySQL (código %s)', error.errno)
        if error.errno == 1062:
            return jsonify(erro='Já existe um registro com essa série ou outro campo único.'), 409
        if error.errno in (1044, 1045, 1142):
            message = 'O MySQL recusou a operação. Confira o usuário e as permissões de consulta e cadastro.'
        elif error.errno in (1049, 1054, 1146):
            message = 'Confira os nomes do banco, tabela e coluna no arquivo .env.'
        elif error.errno in (1364, 1048, 1406, 1265, 1292):
            message = 'Os dados não correspondem às regras da tabela MySQL. Confira campos obrigatórios, tipos e tamanhos.'
        else:
            message = 'Não foi possível acessar o MySQL. Confira a conexão com o computador da empresa e tente novamente.'
        return jsonify(erro=message), 503

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.error('Falha inesperada na operação de inventário.')
        return jsonify(erro='Não foi possível concluir a operação.'), 500

    from inventory_api import register_inventory
    register_inventory(app, configuration, connect, env)

    return app


if __name__ == '__main__':
    from waitress import create_server
    import socket
    import webbrowser
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get('PORT', '5000'))
    requested_port = port
    while port < requested_port + 20:
        with socket.socket() as probe:
            probe.settimeout(0.3)
            if probe.connect_ex(('127.0.0.1', port)) != 0:
                break
        port += 1
    if port >= requested_port + 20:
        raise SystemExit('Não foi encontrada uma porta livre. Encerre as versões antigas do sistema.')
    server = create_server(create_app(), host='127.0.0.1', port=port, threads=4)
    if port != requested_port:
        print(f'A porta {requested_port} está ocupada. Esta versão usará a porta {port}.', flush=True)
    print(f'Controle de ativos: http://127.0.0.1:{port}', flush=True)
    if os.environ.get('OPEN_BROWSER') == '1':
        webbrowser.open(f'http://127.0.0.1:{port}')
    server.run()
