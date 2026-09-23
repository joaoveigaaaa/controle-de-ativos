import os
import pandas as pd

pasta_projeto = r"C:\Users\Luxafit\Desktop\controle-de-ativos"

# 1. Localizar o arquivo Excel
ficheiros = [f for f in os.listdir(pasta_projeto) if f.endswith(('.xlsx', '.xls', '.csv')) and not f.startswith('Inventario_Limpo')]

if not ficheiros:
    print("Nenhum ficheiro de inventário original foi encontrado!")
    exit()

caminho_excel = os.path.join(pasta_projeto, ficheiros[0])
print(f"Lendo o ficheiro: {caminho_excel}")

# 2. Identificar aba e carregar dados brutos
aba_correta = None
if caminho_excel.endswith('.csv'):
    df_raw = pd.read_csv(caminho_excel, header=None)
else:
    excel_file = pd.ExcelFile(caminho_excel)
    aba_correta = excel_file.sheet_names[0]
    for nome_aba in excel_file.sheet_names:
        if any(termo in nome_aba.lower() for termo in ['base', 'dados', 'ativo', 'geral', 'planilha1', 'sheet1']):
            aba_correta = nome_aba
            break
            
    df_raw = pd.read_excel(caminho_excel, sheet_name=aba_correta, header=None)

# 3. Encontrar a linha do cabeçalho
colunas_chave = ['ativo', 'número de série', 'numero', 'categoria', 'status', 'matrícula', 'matricula', 'responsável', 'colaborador', 'empresa', 'sede']
linha_cabecalho = None

for idx, row in df_raw.iterrows():
    valores_linha = [str(val).lower().strip() for val in row.values]
    if any(chave in valores_linha for chave in colunas_chave):
        linha_cabecalho = idx
        break

if linha_cabecalho is None:
    linha_cabecalho = 0

# 4. Recarregar dados a partir da linha correta
if caminho_excel.endswith('.csv'):
    df = pd.read_csv(caminho_excel, skiprows=linha_cabecalho)
else:
    df = pd.read_excel(caminho_excel, sheet_name=aba_correta, skiprows=linha_cabecalho)

# Remover colunas vazias/resumos
df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^COUNTA|Total|Soma', case=False, na=False)]

# --- DIAGNÓSTICO: MOSTRAR NOMES REAIS DAS COLUNAS DA PLANILHA ORIGINAL ---
print("\n" + "="*60)
print("CABEÇALHOS ENCONTRADOS NA SUA PLANILHA ORIGINAL:")
for i, col in enumerate(df.columns):
    print(f" [{i}] -> '{col}'")
print("="*60 + "\n")

# 5. MAPEAMENTO EXPANDIDO (Colaborador / Responsável)
mapeamento_colunas = {
    # Ativo
    'Ativo': 'ativo', 'Nome Ativo': 'ativo', 'Equipamento': 'ativo', 'Item': 'ativo', 'Descrição': 'ativo', 'Descricao': 'ativo',
    
    # Número de Série
    'Número de série': 'numero', 'Numero de serie': 'numero', 'Nº de Série': 'numero', 'N/S': 'numero', 'Serial': 'numero', 'Série': 'numero',
    
    # Categoria
    'Categoria': 'categoria', 'Tipo': 'categoria',
    
    # Status
    'Status': 'status', 'Estado': 'status', 'Situação': 'status', 'Situacao': 'status',
    
    # Matrícula
    'Matrícula': 'matricula', 'Matricula': 'matricula', 'RE': 'matricula', 'ID Colaborador': 'matricula',
    
    # Data de Garantia
    'Data de garantia': 'data_garantia', 'Data Garantia': 'data_garantia', 'Garantia': 'data_garantia',
    
    # Departamento
    'Departamento': 'dp', 'DP': 'dp', 'Setor': 'dp', 'Área': 'dp', 'Area': 'dp',
    
    # Responsável / Colaborador (TODAS AS POSSÍVEIS VARIAÇÕES)
    'Responsável': 'nome_responsavel', 'Responsavel': 'nome_responsavel', 
    'Nome Responsável': 'nome_responsavel', 'Nome Responsavel': 'nome_responsavel', 
    'Colaborador': 'nome_responsavel', 'Nome Colaborador': 'nome_responsavel', 'Nome do Colaborador': 'nome_responsavel',
    'Atribuído a': 'nome_responsavel', 'Atribuido a': 'nome_responsavel',
    'Usuario': 'nome_responsavel', 'Usuário': 'nome_responsavel', 'Nome Usuário': 'nome_responsavel',
    'Funcionário': 'nome_responsavel', 'Funcionario': 'nome_responsavel', 'Nome': 'nome_responsavel',
    
    # Sede / Empresa
    'Sede': 'sede', 'Empresa': 'sede', 'Nome Empresa': 'sede', 'Local': 'sede', 
    'Unidade': 'sede', 'Filial': 'sede', 'Planta': 'sede', 'Localidade': 'sede', 'Sede/Empresa': 'sede'
}

novas_colunas = {}
for col in df.columns:
    col_str = str(col).strip()
    col_encontrada = False
    for ch, val in mapeamento_colunas.items():
        if ch.lower() == col_str.lower():
            novas_colunas[col] = val
            col_encontrada = True
            break
    if not col_encontrada:
        novas_colunas[col] = col_str

df = df.rename(columns=novas_colunas)

# Manter apenas as colunas estruturadas para o banco
colunas_mysql = ['ativo', 'numero', 'categoria', 'status', 'matricula', 'data_garantia', 'dp', 'nome_responsavel', 'sede']
colunas_presentes = [c for c in colunas_mysql if c in df.columns]
df = df[colunas_presentes]

# 6. Limpeza e Tratamento
df = df.astype(str)
df = df.apply(lambda x: x.str.strip())
df = df.replace(['(vazio)', 'nan', 'None', 'NaN', ''], None)

if 'ativo' in df.columns:
    df = df.dropna(subset=['ativo'])

if 'data_garantia' in df.columns:
    df['data_garantia'] = pd.to_datetime(df['data_garantia'], errors='coerce').dt.strftime('%Y-%m-%d')

# 7. Salvar resultado final
caminho_saida = os.path.join(pasta_projeto, "Inventario_Limpo.xlsx")

try:
    df.to_excel(caminho_saida, index=False)
    print(f"Ficheiro limpo salvo com sucesso em: {caminho_saida}")
except PermissionError:
    import datetime
    agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_saida = os.path.join(pasta_projeto, f"Inventario_Limpo_{agora}.xlsx")
    df.to_excel(caminho_saida, index=False)
    print(f"Ficheiro limpo salvo com nome alternativo: {caminho_saida}")

print(f"Total de ativos processados: {len(df)}")