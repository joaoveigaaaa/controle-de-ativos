import os
import pandas as pd

caminho_excel = r"C:\Users\Luxafit\Desktop\controle-de-ativos\Inventário de TI.xlsx"

if not os.path.exists(caminho_excel):
    print("=" * 60)
    print(f"ERRO: Ficheiro não encontrado!")
    print(f"Verifique se o ficheiro está em: {caminho_excel}")
    print("DICA: Confirme a extensão do ficheiro (.xlsx, .xls ou .csv)")
    print("=" * 60)
else:

    df = pd.read_excel(caminho_excel)
    print("Ficheiro carregado com sucesso!")

    mapeamento_colunas = {
        'Ativo': 'ativo',
        'Número de série': 'numero',
        'Categoria': 'categoria',
        'Status': 'status',
        'Matrícula': 'matricula',
        'Data de garantia': 'data_garantia',
        'Departamento': 'dp',
        'Responsável': 'nome_responsavel',
        'Sede': 'sede'
    }

    df = df.rename(columns=mapeamento_colunas)

    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    if 'numero' in df.columns:
        df = df.drop_duplicates(subset=['numero'], keep='first')

    if 'ativo' in df.columns:
        df = df.dropna(subset=['ativo'])

    df = df.where(pd.notnull(df), None)

    if 'data_garantia' in df.columns:
        df['data_garantia'] = pd.to_datetime(df['data_garantia'], errors='coerce').dt.strftime('%Y-%m-%d')
        df['data_garantia'] = df['data_garantia'].where(pd.notnull(df['data_garantia']), None)

    caminho_saida = r"C:\Users\Luxafit\Desktop\controle-de-ativos\Inventario_Limpo.xlsx"
    df.to_excel(caminho_saida, index=False)

    print("-" * 60)
    print("Tratamento concluído com sucesso!")
    print(f"Total de registos limpos e prontos: {len(df)}")
    print(f"Ficheiro guardado em: {caminho_saida}")