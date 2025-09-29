import pandas as pd
import unicodedata
import re
from datetime import datetime
import os

def detectar_separador(caminho):
    with open(caminho, 'r', encoding='utf-8-sig') as f:
        primeira_linha = f.readline()
        return ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','

def normalizar_texto(texto):
    if pd.isna(texto) or texto == '':
        return 'NAO INFORMADO'
    if isinstance(texto, str):
        texto = texto.upper()
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) 
                       if unicodedata.category(c) != 'Mn')
        texto = re.sub(r'[^\w\s]', '', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
    return texto

def padronizar_distrito(nome_distrito):
    if pd.isna(nome_distrito):
        return 'NAO INFORMADO'
    distrito = normalizar_texto(str(nome_distrito))
    distrito = re.sub(r'\(DISTRITO\)', '', distrito)
    distrito = re.sub(r'DISTRITO', '', distrito)
    return distrito.strip()

def carregar_csv_generico(caminho, colunas_esperadas):
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=colunas_esperadas)
    
    separador = detectar_separador(caminho)
    df = pd.read_csv(caminho, sep=separador, encoding='utf-8-sig')
    
    mapeamento = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if any(termo in col_lower for termo in ['regiao', 'região']):
            mapeamento['regiao'] = col
        elif 'nome' in col_lower:
            mapeamento['nome'] = col
        elif any(termo in col_lower for termo in ['periodo', 'período']):
            mapeamento['periodo'] = col
        elif 'resultado' in col_lower:
            mapeamento['resultado'] = col
    
    if not all(k in mapeamento for k in ['regiao', 'nome', 'periodo', 'resultado']):
        return pd.DataFrame(columns=colunas_esperadas)
    
    df['distrito'] = df[mapeamento['regiao']].apply(padronizar_distrito)
    df['ano'] = pd.to_numeric(df[mapeamento['periodo']], errors='coerce')
    df['valor'] = pd.to_numeric(df[mapeamento['resultado']], errors='coerce')
    df['nome_indicador'] = df[mapeamento['nome']].apply(normalizar_texto)
    
    df = df[df['ano'].notna()].copy()
    if len(df) > 0:
        df['ano'] = df['ano'].astype(int)
    
    return df[['distrito', 'ano', 'nome_indicador', 'valor']]

def carregar_mapa_desigualdade():
    print("Carregando Mapa da Desigualdade...")
    caminho = '../Arquivos_Tratados/mapa_da_desigualdade_2024_padronizado.csv'
    
    if not os.path.exists(caminho):
        return pd.DataFrame()
    
    separador = detectar_separador(caminho)
    df = pd.read_csv(caminho, sep=separador, encoding='utf-8-sig')
    
    coluna_distrito = None
    for col in df.columns:
        if 'distrito' in col.lower():
            coluna_distrito = col
            break
    
    if not coluna_distrito:
        coluna_distrito = df.columns[0]
    
    df['distrito'] = df[coluna_distrito].apply(padronizar_distrito)
    df['ano'] = 2024
    
    colunas_finais = {'distrito': 'distrito', 'ano': 'ano'}
    
    mapeamento_busca = {
        'idade_media_morrer': ['idade', 'morrer'],
        'gravidez_adolescencia': ['gravidez', 'adolescen'],
        'mortalidade_materna': ['mortalidade', 'materna'],
        'mortalidade_infantil': ['mortalidade', 'infantil'],
        'favelas': ['favela']
    }
    
    for col_nova, termos in mapeamento_busca.items():
        for col in df.columns:
            if all(t.lower() in col.lower() for t in termos):
                colunas_finais[col] = col_nova
                break
    
    colunas_existentes = [c for c in colunas_finais.keys() if c in df.columns]
    df_final = df[colunas_existentes].copy()
    df_final.columns = [colunas_finais[c] for c in colunas_existentes]
    
    print(f"  {len(df_final)} distritos, {len(df_final.columns)} colunas")
    return df_final
