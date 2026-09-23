from decimal import Decimal
from datetime import date, datetime
from flask import jsonify, request

def converter_dados(obj):
    """Converte tipos do MySQL (Decimal, Date) para tipos compatíveis com JSON."""
    if isinstance(obj, list):
        return [converter_dados(i) for i in obj]
    if isinstance(obj, dict):
        return {k: converter_dados(v) for k, v in obj.items()}
    if isinstance(obj, (datetime, date)):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def register_inventory(app, configuration, connect, env):
    
    # Rota principal de consulta dos equipamentos/ativos
    @app.route('/api/equipamentos', methods=['GET', 'POST'])
    @app.route('/api/ativos', methods=['GET', 'POST'])
    @app.route('/equipamentos', methods=['GET', 'POST'])
    @app.route('/ativos', methods=['GET', 'POST'])
    def gerenciar_inventario():
        try:
            options, table, serial_column = configuration()
            conn = connect(**options)
            cursor = conn.cursor(dictionary=True)
            
            if request.method == 'GET':
                cursor.execute(f"SELECT * FROM {table}")
                dados = cursor.fetchall()
                cursor.close()
                conn.close()
                return jsonify(converter_dados(dados)), 200
                
            elif request.method == 'POST':
                payload = request.get_json() or {}
                
                # Monta inserção dinâmica com os campos enviados
                colunas = list(payload.keys())
                valores = list(payload.values())
                
                if not colunas:
                    cursor.close()
                    conn.close()
                    return jsonify(erro="Nenhum dado enviado."), 400
                
                cols_str = ", ".join(colunas)
                placeholders = ", ".join(["%s"] * len(valores))
                
                query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
                cursor.execute(query, valores)
                
                cursor.close()
                conn.close()
                return jsonify(sucesso=True, mensagem="Registro salvo com sucesso!"), 201
                
        except Exception as e:
            app.logger.error("Erro na API de Inventário: %s", str(e))
            return jsonify(erro=f"Erro ao processar requisição: {str(e)}"), 500

    # Rota individual de cada ativo por ID ou Número
    @app.route('/api/equipamentos/<id_ativo>', methods=['GET', 'PUT', 'DELETE'])
    @app.route('/api/ativos/<id_ativo>', methods=['GET', 'PUT', 'DELETE'])
    def elemento_inventario(id_ativo):
        try:
            options, table, serial_column = configuration()
            conn = connect(**options)
            cursor = conn.cursor(dictionary=True)
            
            if request.method == 'GET':
                cursor.execute(f"SELECT * FROM {table} WHERE id = %s OR {serial_column} = %s", (id_ativo, id_ativo))
                item = cursor.fetchone()
                cursor.close()
                conn.close()
                if not item:
                    return jsonify(erro="Registro não encontrado."), 404
                return jsonify(converter_dados(item)), 200

            elif request.method == 'DELETE':
                cursor.execute(f"DELETE FROM {table} WHERE id = %s OR {serial_column} = %s", (id_ativo, id_ativo))
                cursor.close()
                conn.close()
                return jsonify(sucesso=True), 200
                
        except Exception as e:
            return jsonify(erro=str(e)), 500