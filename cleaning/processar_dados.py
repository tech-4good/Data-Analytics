import pandas as pd
import re
import unicodedata

def clean_excel_mapa_desigualdade(input_path, output_xlsx, output_csv):
    df = pd.read_excel(input_path, sheet_name='2. Dados_distritos_2024')  # lê a planilha específica

    def clean_cell(cell):
        if pd.isnull(cell):
            return 'NAO INFORMADO'
        if isinstance(cell, str):
            cell = cell.upper()  # converte para maiúscula
            cell = unicodedata.normalize('NFD', cell)  # remove os acentos
            cell = ''.join(c for c in cell if unicodedata.category(c) != 'Mn')
            cell = re.sub(r'[^\w\s.,%()-]', '', cell)  # remove os caracteres especiais
            cell = re.sub(r'\s+', ' ', cell)  # remove os espaços múltiplos
            cell = cell.strip()  # remove os espaços das bordas
            return cell
        return cell

    # Processa os valores nulos primeiro
    for coluna in df.columns:
        nulos = df[coluna].isnull().sum()
        if nulos > 0:
            # Se coluna tem texto, converte para string
            valores_nao_nulos = df[coluna].dropna()
            if len(valores_nao_nulos) > 0:
                tem_texto = any(isinstance(val, str) or 
                              any(c.isalpha() for c in str(val)) 
                              for val in valores_nao_nulos.head(10))
                if tem_texto or 'distrito' in coluna.lower():
                    df[coluna] = df[coluna].astype(str)
                    df[coluna] = df[coluna].replace(['nan', 'None', 'NaN'], 'NAO INFORMADO')
                    df[coluna] = df[coluna].fillna('NAO INFORMADO')
                else:
                    try:
                        df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
                        if df[coluna].isnull().sum() > 0:
                            df[coluna] = df[coluna].astype(str).replace('nan', 'NAO INFORMADO')
                    except:
                        df[coluna] = df[coluna].fillna('NAO INFORMADO')

    # Aplica a limpeza em colunas de texto
    for coluna in df.columns:
        if df[coluna].dtype == 'object':
            df[coluna] = df[coluna].apply(clean_cell)

    # Salva os arquivos
    df.to_excel(output_xlsx, index=False, sheet_name='Dados_Padronizados')
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')

# processar o arquivo principal 
clean_excel_mapa_desigualdade('mapa_da_desigualdade_2024_dados.xlsx',
                             'mapa_da_desigualdade_2024_padronizado.xlsx',
                             'mapa_da_desigualdade_2024_padronizado.csv')
