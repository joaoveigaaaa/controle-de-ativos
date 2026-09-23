"""APIs do HTML de equipamentos, usando exclusivamente o MySQL existente."""
from contextlib import contextmanager
from datetime import date, datetime
from io import BytesIO
import json
import re
import unicodedata
import zipfile

from flask import jsonify, request, send_file
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
import mysql.connector

FIELDS = ['ativo', 'numero_serie', 'categoria', 'status', 'matricula', 'data_garantia', 'departamento', 'responsavel', 'sede']
LABELS = ['Ativo', 'Número de série', 'Categoria', 'Status', 'Matrícula', 'Data de garantia', 'Departamento', 'Responsável', 'Sede']
STATUSES = ['', 'Em estoque', 'Em uso', 'Em manutenção', 'Inativo']


def norm(value):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower())


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Envie os dados de um equipamento.')
    item = {}
    for field in FIELDS:
        value = data.get(field, data.get('empresa', '') if field == 'sede' else '')
        if value is None:
            value = ''
        if isinstance(value, (dict, list, bool)):
            raise ValueError(f'Valor inválido em {field}.')
        if isinstance(value, (datetime, date)):
            value = value.strftime('%Y-%m-%d')
        value = str(value).strip()
        limit = {'responsavel': 150, 'matricula': 50}.get(field, 100)
        if len(value) > limit:
            raise ValueError(f'{field}: máximo de {limit} caracteres.')
        item[field] = value
    if not item['ativo'] or not item['numero_serie']:
        raise ValueError('Preencha o ativo e o número de série.')
    if item['status'] not in STATUSES:
        raise ValueError('Status inválido. Use as opções do formulário.')
    if item['data_garantia']:
        try:
            value = item['data_garantia']
            parsed = datetime.strptime(value, '%d/%m/%Y').date() if '/' in value else date.fromisoformat(value)
            if parsed.year < 1000:
                raise ValueError()
            item['data_garantia'] = parsed.isoformat()
        except ValueError:
            raise ValueError('Data de garantia inválida.') from None
    return item


def register_inventory(app, configuration, connect, env):
    @contextmanager
    def database():
        options, table, serial = configuration()
        connection = cursor = None
        try:
            connection = connect(**options)
            cursor = connection.cursor(dictionary=True)
            yield connection, cursor, table, serial
        finally:
            for resource in (cursor, connection):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        pass

    def schema(cursor, table, serial):
        cursor.execute(f'SHOW COLUMNS FROM `{table}`')
        columns = cursor.fetchall()
        names = [c['Field'] for c in columns]
        if serial not in names:
            raise ValueError('A coluna de série configurada não existe nessa tabela. Confira MYSQL_SERIAL_COLUMN no .env.')
        aliases = {'ativo': ['ativo', 'nome', 'equipamento', 'descricao', 'produto'],
                   'sede': ['sede', 'empresa'], 'responsavel': ['responsavel', 'nome_responsavel'],
                   'data_garantia': ['data_garantia', 'garantia']}
        mapping = {'numero_serie': serial}
        for field in FIELDS:
            if field == 'numero_serie':
                continue
            for alias in aliases.get(field, [field]):
                match = next((n for n in names if norm(n) == norm(alias) and n != serial), None)
                if match:
                    mapping[field] = match
                    break
        try:
            overrides = json.loads(env.get('MYSQL_FIELD_MAP', '{}'))
        except (TypeError, json.JSONDecodeError):
            raise ValueError('MYSQL_FIELD_MAP deve ser um objeto JSON válido.') from None
        if not isinstance(overrides, dict):
            raise ValueError('MYSQL_FIELD_MAP deve ser um objeto JSON.')
        for field, column in overrides.items():
            if field not in FIELDS or column not in names:
                raise ValueError('MYSQL_FIELD_MAP contém campo ou coluna inexistente.')
            mapping[field] = column
        if mapping['numero_serie'] != serial or len(set(mapping.values())) != len(mapping):
            raise ValueError('Confira MYSQL_FIELD_MAP: cada campo deve usar uma coluna diferente, e a série deve corresponder a MYSQL_SERIAL_COLUMN.')
        # Column identifiers are escaped even when they originate from SHOW COLUMNS.
        return mapping, columns

    def quoted(name):
        return '`' + name.replace('`', '``') + '`'

    def record(raw, mapping):
        result = {}
        for field in FIELDS:
            value = raw.get(mapping.get(field, ''))
            if isinstance(value, (datetime, date)):
                value = value.strftime('%Y-%m-%d')
            result[field] = '' if value is None else str(value)
        return result

    def write_values(item, mapping, columns):
        if 'ativo' not in mapping:
            raise ValueError('Não foi identificada a coluna do ativo. Configure MYSQL_FIELD_MAP no .env antes de cadastrar.')
        absent = [LABELS[FIELDS.index(f)] for f in FIELDS if item[f] and f not in mapping]
        if absent:
            raise ValueError('Campos sem coluna correspondente no MySQL: ' + ', '.join(absent) + '. Configure MYSQL_FIELD_MAP.')
        details = {c['Field']: c for c in columns}
        values = {}
        for field, column in mapping.items():
            value = item[field]
            nullable = details[column].get('Null') == 'YES'
            if not value and field == 'data_garantia':
                if nullable:
                    values[column] = None
                elif details[column].get('Default') is None:
                    raise ValueError('O banco exige uma data de garantia.')
            else:
                values[column] = None if not value and nullable else value
        for column in columns:
            if column['Field'] not in values and column.get('Null') == 'NO' and column.get('Default') is None and not any(x in column.get('Extra', '').lower() for x in ('auto_increment', 'generated')):
                raise ValueError(f'O banco exige o campo {column["Field"]}, que não está disponível no formulário. Ajuste o mapeamento ou o padrão no banco.')
        return values

    def insert(cursor, table, values):
        cursor.execute(f'INSERT INTO `{table}` (' + ','.join(quoted(k) for k in values) + ') VALUES (' + ','.join('%s' for _ in values) + ')', tuple(values.values()))

    @app.get('/api/equipamentos')
    def inventory():
        with database() as (_, cursor, table, serial):
            mapping, _ = schema(cursor, table, serial)
            cursor.execute(f'SELECT * FROM `{table}` ORDER BY `{serial}`')
            raw = cursor.fetchall()
            dates = [r.get(k) for r in raw for k in ('criado_em', 'created_at', 'data_cadastro') if r.get(k)]
            latest = max(str(d) for d in dates) if dates else None
            return jsonify(registros=[record(r, mapping) for r in raw], ultimo_cadastro=latest)

    @app.get('/api/consulta')
    def lookup():
        serial_value = request.args.get('serie', '').strip()
        if not serial_value or len(serial_value) > 100 or any(ord(c) < 32 for c in serial_value):
            raise ValueError('Informe um número de série válido, com até 100 caracteres.')
        with database() as (_, cursor, table, serial):
            mapping, _ = schema(cursor, table, serial)
            cursor.execute(f'SELECT * FROM `{table}` WHERE `{serial}` = %s LIMIT 2', (serial_value,))
            rows = cursor.fetchall()
            if len(rows) > 1:
                return jsonify(erro='Há mais de um ativo com esta série. Confira os registros no MySQL.'), 409
            return jsonify(registros=[record(r, mapping) for r in rows])

    @app.post('/api/equipamentos')
    def register():
        item = validate(request.get_json())
        with database() as (connection, cursor, table, serial):
            mapping, columns = schema(cursor, table, serial)
            values = write_values(item, mapping, columns)
            connection.start_transaction()
            try:
                cursor.execute(f'SELECT `{serial}` FROM `{table}` WHERE `{serial}` = %s FOR UPDATE', (item['numero_serie'],))
                if cursor.fetchall():
                    connection.rollback()
                    return jsonify(erro='Este número de série já está cadastrado.'), 409
                insert(cursor, table, values)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return jsonify(registro=item), 201

    def spreadsheet():
        file = request.files.get('arquivo')
        if not file or not (file.filename or '').lower().endswith('.xlsx'):
            raise ValueError('Selecione uma planilha .xlsx.')
        content = file.read(20 * 1024 * 1024 + 1)
        if not content or len(content) > 20 * 1024 * 1024:
            raise ValueError('A planilha deve ter até 20 MB.')
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 100 * 1024 * 1024:
                    raise ValueError()
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
        except Exception:
            raise ValueError('Arquivo Excel inválido ou grande demais ao descompactar.') from None
        try:
            name = request.form.get('aba') or workbook.sheetnames[0]
            if name not in workbook.sheetnames:
                raise ValueError('Aba não encontrada.')
            sheet = workbook[name]
            if (sheet.max_row or 0) > 10001 or (sheet.max_column or 0) > 100:
                raise ValueError('Use até 10.000 linhas e 100 colunas.')
            aliases = {norm(k): k for k in FIELDS}
            aliases.update({norm(label): field for field, label in zip(FIELDS, LABELS)})
            aliases.update(serie='numero_serie', serial='numero_serie', numerodeserie='numero_serie', empresa='sede')
            iterator = sheet.iter_rows()
            headers = [aliases.get(norm(c.value)) for c in next(iterator, [])]
            known = [h for h in headers if h]
            if len(known) != len(set(known)) or not {'ativo', 'numero_serie'}.issubset(known):
                raise ValueError('Use cabeçalhos sem repetição, incluindo Ativo e Número de série. Baixe o modelo.')
            records = []
            for number, cells in enumerate(iterator, 2):
                if number > 10001:
                    raise ValueError('Use até 10.000 linhas.')
                if all(c.value is None for c in cells):
                    continue
                raw = {}
                for field, cell in zip(headers, cells):
                    if not field:
                        continue
                    if cell.data_type == 'f':
                        raise ValueError(f'Linha {number}: substitua as fórmulas por valores.')
                    value = cell.value
                    if field in ('numero_serie', 'matricula') and isinstance(value, (int, float)):
                        if isinstance(value, float) and not value.is_integer():
                            raise ValueError(f'Linha {number}: use série e matrícula como texto.')
                        value = str(int(value))
                        if re.fullmatch('0+', cell.number_format):
                            value = value.zfill(len(cell.number_format))
                    raw[field] = value
                try:
                    records.append(validate(raw))
                except ValueError as error:
                    raise ValueError(f'Linha {number}: {error}') from error
            return workbook.sheetnames, name, records
        finally:
            workbook.close()

    @app.post('/api/excel')
    def excel():
        action = request.form.get('acao')
        if action not in ('visualizar', 'importar'):
            raise ValueError('Ação de importação inválida.')
        sheets, name, records = spreadsheet()
        if action == 'visualizar':
            return jsonify(abas=sheets, aba=name, quantidade=len(records))
        imported = ignored = 0
        with database() as (connection, cursor, table, serial):
            mapping, columns = schema(cursor, table, serial)
            values = [write_values(item, mapping, columns) for item in records]
            connection.start_transaction()
            try:
                for item, value in zip(records, values):
                    cursor.execute(f'SELECT `{serial}` FROM `{table}` WHERE `{serial}` = %s FOR UPDATE', (item['numero_serie'],))
                    if cursor.fetchall():
                        ignored += 1
                    else:
                        insert(cursor, table, value)
                        imported += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return jsonify(importados=imported, ignorados=ignored)

    @app.get('/api/excel/<kind>')
    def download(kind):
        if kind not in ('modelo', 'exportar'):
            return jsonify(erro='Arquivo não encontrado.'), 404
        rows = []
        headers = list(LABELS)
        keys = list(FIELDS)
        conflicts = []
        removed = 0
        if kind == 'exportar':
            with database() as (_, cursor, table, serial):
                mapping, columns = schema(cursor, table, serial)
                cursor.execute(f'SELECT * FROM `{table}` ORDER BY `{serial}`')
                raw_rows = cursor.fetchall()
                extra = [c['Field'] for c in columns if c['Field'] not in mapping.values()]
                for column in extra:
                    keys.append('extra:' + column)
                    label = column if column.casefold() not in {h.casefold() for h in headers} else column + ' (banco)'
                    headers.append(label)
                groups = {}
                def priority(raw):
                    timestamp = next((str(raw[k]) for k in ('updated_at', 'atualizado_em', 'criado_em', 'created_at', 'data_cadastro') if raw.get(k)), '')
                    try:
                        identifier = int(raw.get('id', 0))
                    except (TypeError, ValueError):
                        identifier = 0
                    return timestamp, identifier, sum(v not in (None, '') for v in raw.values()), str(sorted((k, str(v)) for k, v in raw.items()))
                for raw in sorted(raw_rows, key=priority, reverse=True):
                    item = record(raw, mapping)
                    item.update({'extra:' + k: '' if raw.get(k) is None else str(raw[k]) for k in extra})
                    serial_value = item['numero_serie'].strip()
                    group_key = ('serie', serial_value.casefold()) if serial_value else ('sem-serie', tuple(item[k] for k in keys))
                    groups.setdefault(group_key, []).append(item)
                for items in groups.values():
                    chosen = dict(items[0])
                    removed += len(items) - 1
                    for key, label in zip(keys, headers):
                        variants = list(dict.fromkeys(item[key] for item in items if item[key] not in ('', None)))
                        if not chosen[key] and variants:
                            chosen[key] = variants[0]
                        if len(variants) > 1 and key != 'numero_serie':
                            conflicts.append([chosen['numero_serie'], label, str(chosen[key]), '\n'.join(str(v) for v in variants)])
                    rows.append(chosen)
                rows.sort(key=lambda r: r['numero_serie'].casefold())
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Equipamentos'
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='064D7F')
        for i in range(1, len(headers) + 1):
            sheet.column_dimensions[get_column_letter(i)].width = 24
        sheet.freeze_panes = 'A2'
        for row in rows:
            sheet.append([row[f] for f in keys])
            for cell in sheet[sheet.max_row]:
                cell.data_type = 's'
                cell.number_format = '@'
        sheet.auto_filter.ref = sheet.dimensions
        if conflicts:
            notes = workbook.create_sheet('Divergências')
            notes.append(['Número de série', 'Campo', 'Valor usado', 'Valores encontrados'])
            for row in conflicts:
                notes.append(row)
                for cell in notes[notes.max_row]:
                    cell.data_type = 's'
                    cell.number_format = '@'
            notes.freeze_panes = 'A2'
            notes.auto_filter.ref = notes.dimensions
            for i, width in enumerate((24, 26, 40, 60), 1):
                notes.column_dimensions[get_column_letter(i)].width = width
            from openpyxl.styles import Alignment
            for row in notes:
                for cell in row:
                    cell.alignment = Alignment(vertical='top', wrap_text=True)
            for cell in notes[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='064D7F')
        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)
        response = send_file(stream, as_attachment=True, download_name=f'{kind}-equipamentos.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response.headers['X-Export-Registros'] = str(len(rows))
        response.headers['X-Export-Repetidos'] = str(removed)
        response.headers['X-Export-Divergencias'] = str(len(conflicts))
        return response
