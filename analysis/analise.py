import pandas as pd
import optparse
import os

# Configuração dos distritos
DISTRITOS_IGREJA = ['BELA VISTA', 'BOM RETIRO', 'CAMBUCI', 'CONSOLACAO', 'LIBERDADE', 'REPUBLICA', 'SANTA CECILIA', 'SE']

MAPEAMENTO_DISTRITOS = {
    'BELA VISTA': ['BELA VISTA', 'BELA VISTA DISTRITO'],
    'BOM RETIRO': ['BOM RETIRO', 'BOM RETIRO DISTRITO'],
    'CAMBUCI': ['CAMBUCI', 'CAMBUCI DISTRITO'],
    'CONSOLACAO': ['CONSOLACAO', 'CONSOLACAO DISTRITO'],
    'LIBERDADE': ['LIBERDADE', 'LIBERDADE DISTRITO'],
    'REPUBLICA': ['REPUBLICA', 'REPUBLICA DISTRITO'],
    'SANTA CECILIA': ['SANTA CECILIA', 'SANTA CECILIA DISTRITO'],
    'SE': ['SE', 'SE DISTRITO']
}

MESES_MAP = {
    'JANEIRO': 1, 'FEVEREIRO': 2, 'MARCO': 3, 'ABRIL': 4,
    'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8,
    'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12
}

def normalizar_distrito(nome):
    if pd.isna(nome):
        return None
    nome_norm = str(nome).upper().strip().replace(' DISTRITO', '')
    for distrito_padrao, variacoes in MAPEAMENTO_DISTRITOS.items():
        if nome_norm in variacoes:
            return distrito_padrao
    return nome_norm

def identificar_coluna_distrito(df):
    colunas_possiveis = ['Distrito', 'Regiao', 'Região']
    for col in colunas_possiveis:
        if col in df.columns:
            return col 
    for col in df.columns:
        if 'DISTRITO' in col.upper() or 'REGIAO' in col.upper():
            return col
    return None

def carregar_csv(caminho):
    if not os.path.exists(caminho):
        print(f"Arquivo nao encontrado: {caminho}")
        return None
    try:
        return pd.read_csv(caminho, encoding='utf-8-sig')
    except Exception as e:
        print(f"Erro ao carregar {os.path.basename(caminho)}: {e}")
        return None

def filtrar_distritos(df, coluna_distrito=None, filtrar_apenas_igreja=False):
    if df is None or len(df) == 0:
        return df
    
    if coluna_distrito is None:
        coluna_distrito = identificar_coluna_distrito(df)
    
    if coluna_distrito is None:
        return pd.DataFrame()
    
    df_filtrado = df.copy()
    df_filtrado['Distrito'] = df_filtrado[coluna_distrito].apply(normalizar_distrito)
    
    # Remove distritos inválidos 
    df_filtrado = df_filtrado[df_filtrado['Distrito'].notna()]
    df_filtrado = df_filtrado[df_filtrado['Distrito'] != '']
    
    # Se filtrar_apenas_igreja=True, filtra pelos distritos da igreja
    if filtrar_apenas_igreja:
        df_filtrado = df_filtrado[df_filtrado['Distrito'].isin(DISTRITOS_IGREJA)]
    
    return df_filtrado

# Benefícios
def consolidar_bpc():
    print("\nCarregando BPC...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    caminho = os.path.join(base_dir, 'Arquivos_Tratados', 'bpc_2024_consolidado.csv')
    
    df = carregar_csv(caminho)
    if df is None:
        return None
    
    # ALTERAÇÃO IMPORTANTE:
    # Para uma melhor analise, estou fazendo uma varivel para caso seja necessario
    # pegar apenas os distritos da igreja ou todos os distritos
    df = filtrar_distritos(df, 'Distrito', filtrar_apenas_igreja=False)
    if len(df) == 0:
        return None
    
    df = df.rename(columns={'Total': 'Quantidade_Beneficiados'})
    df['Programa'] = 'BPC'
    df['Categoria'] = df['Tipo_Beneficio']
    df['Mes_Numero'] = df['Mes'].map(MESES_MAP)
    
    colunas = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Programa', 
               'Categoria', 'Quantidade_Beneficiados', 'Mes', 'Mes_Numero', 'Ano']
    
    print(f"BPC: {len(df)} registros, {df['Quantidade_Beneficiados'].sum()} beneficiados")
    return df[colunas]

def consolidar_bolsa_familia():
    print("\nCarregando Bolsa Familia...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    caminho = os.path.join(base_dir, 'Arquivos_Tratados', 'programa_bolsafamilia_2024_1_tratado.csv')
    
    df = carregar_csv(caminho)
    if df is None:
        return None
    
    # Filtrando todos os distritos
    df = filtrar_distritos(df, 'Distrito', filtrar_apenas_igreja=False)
    if len(df) == 0:
        return None
    
    df = df.rename(columns={'Total_Familias': 'Quantidade_Beneficiados'})
    df['Programa'] = 'BOLSA_FAMILIA'
    df['Categoria'] = 'FAMILIA'
    df['Mes_Numero'] = df['Mes'].map(MESES_MAP)
    
    colunas = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Programa', 
                'Categoria', 'Quantidade_Beneficiados', 'Mes', 'Mes_Numero', 'Ano']
    
    print(f"Bolsa Familia: {len(df)} registros, {df['Quantidade_Beneficiados'].sum()} familias")
    return df[colunas]

def consolidar_cadunico():
    print("\nCarregando CadUnico...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    caminho = os.path.join(base_dir, 'Arquivos_Tratados', 'cadunico_familias_jul24_tratado.csv')
    
    df = carregar_csv(caminho)
    if df is None:
        return None
    
    # Filtrando todos os distritos
    df = filtrar_distritos(df, 'Distrito', filtrar_apenas_igreja=False)
    if len(df) == 0:
        return None
    
    df = df.rename(columns={'Total_Familias': 'Quantidade_Beneficiados'})
    df['Programa'] = 'CADUNICO'
    df['Categoria'] = 'FAMILIA'
    df['Mes_Numero'] = df['Mes'].map(MESES_MAP)
    
    colunas = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Programa', 
                'Categoria', 'Quantidade_Beneficiados', 'Mes', 'Mes_Numero', 'Ano']
    
    print(f"CadUnico: {len(df)} registros, {df['Quantidade_Beneficiados'].sum()} familias")
    return df[colunas]

def consolidar_valores_alimentos():
    print("\nCarregando Valores de Alimentos...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    caminho = os.path.join(base_dir, 'Arquivos_Tratados', 'valores_alimentos_consolidado.csv')
    
    df = carregar_csv(caminho)
    if df is None:
        return None
    
    if len(df) == 0:
        return None
    
    # Padroniza as colunas 
    df = df.rename(columns={
        'nome': 'Alimento',
        'preco': 'Preco_Medio',
        'data_mes': 'Mes_Numero',
        'mes_nome': 'Mes',
        'data_ano': 'Ano'
    })
    
    # Seleciona e ordena as colunas finais
    colunas = ['Alimento', 'Preco_Medio', 'Mes', 'Mes_Numero', 'Ano']
    df = df[colunas]

    # Ordena as linhas por alimento, ano e mes
    df = df.sort_values(['Alimento', 'Ano', 'Mes_Numero']).reset_index(drop=True)
    
    print(f"Valores de Alimentos: {len(df)} registros")
    print(f"Alimentos: {df['Alimento'].nunique()}")
    print(f"Periodo: {df['Mes_Numero'].min():02d}/{df['Ano'].min()} a {df['Mes_Numero'].max():02d}/{df['Ano'].max()}")
    
    return df

def consolidar_beneficios():
    print("Consolidando os beneficios")
    print("="*70)
    
    dfs = []
    for df in [consolidar_bpc(), consolidar_bolsa_familia(), consolidar_cadunico()]:
        if df is not None and len(df) > 0:
            dfs.append(df)
    
    if not dfs:
        print("Nenhum dado de beneficios carregado")
        return None
    
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.sort_values(['Distrito', 'Programa', 'Ano', 'Mes_Numero']).reset_index(drop=True)
    
    print(f"\nTotal: {len(df_final)} registros, {df_final['Quantidade_Beneficiados'].sum()} beneficiados")
    print(f"Programas: {df_final['Programa'].unique()}")
    print(f"Distritos únicos: {df_final['Distrito'].nunique()}")
    
    return df_final

# Indicadores
def consolidar_mapa_desigualdade():
    print("\nConsolidando o mapa da desigualdade")
    print("="*70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    caminho = os.path.join(base_dir, 'Arquivos_Tratados', 'mapa_da_desigualdade_2024_padronizado.csv')
    
    df = carregar_csv(caminho)
    if df is None:
        return None
    
    # Filtrando todos os distritos
    df = filtrar_distritos(df, filtrar_apenas_igreja=False)
    if len(df) == 0:
        return None
    
    if 'Ano' not in df.columns:
        df['Ano'] = 2024
    
    print(f"Mapa: {len(df)} distritos, {len(df.columns)} indicadores")
    return df

def consolidar_observasampa():
    print("\nConsolidando os dados do ObservaSampa")
    print("="*70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    tratados_dir = os.path.join(base_dir, 'Arquivos_Tratados')
    
    arquivos = [
        'OSDAI_tratado.csv',
        'OSDAI_ODS_tratado.csv',
        'OSDAV_tratado.csv'
    ]
    
    dfs = []
    for arquivo in arquivos:
        print(f"\nCarregando {arquivo}...")
        df = carregar_csv(os.path.join(tratados_dir, arquivo))
        
        if df is not None:
            # Filtrando todos os distritos
            df_filtrado = filtrar_distritos(df, filtrar_apenas_igreja=False)
            if len(df_filtrado) > 0:
                dfs.append(df_filtrado)
                print(f"{arquivo}: {len(df_filtrado)} registros")
                print(f"Distritos únicos: {df_filtrado['Distrito'].nunique()}")
    
    if not dfs:
        print("Nenhum dado do ObservaSampa carregado")
        return None
    
    df_final = pd.concat(dfs, ignore_index=True)
    
    print(f"\nTotal: {len(df_final)} registros")
    if 'Nome' in df_final.columns:
        print(f"Indicadores: {df_final['Nome'].nunique()}")
    if 'Distrito' in df_final.columns:
        print(f"Distritos únicos: {df_final['Distrito'].nunique()}")
    
    return df_final

# Salvando os dados
def salvar_consolidados(df_beneficios, df_mapa, df_observa, df_alimentos):
    print("\nSalvando os dados consolidados")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(base_dir, 'Arquivos_Tratados', 'Consolidados')
    os.makedirs(output_dir, exist_ok=True)
    
    if df_beneficios is not None and len(df_beneficios) > 0:
        caminho = os.path.join(output_dir, 'tabelao_beneficios.csv')
        df_beneficios.to_csv(caminho, index=False, encoding='utf-8-sig')
        print(f"Salvo: tabelao_beneficios.csv ({len(df_beneficios)} registros, {df_beneficios['Distrito'].nunique()} distritos)")
    
    if df_mapa is not None and len(df_mapa) > 0:
        caminho = os.path.join(output_dir, 'tabelao_indicadores_mapa.csv')
        df_mapa.to_csv(caminho, index=False, encoding='utf-8-sig')
        print(f"Salvo: tabelao_indicadores_mapa.csv ({len(df_mapa)} registros, {df_mapa['Distrito'].nunique()} distritos)")
    
    if df_observa is not None and len(df_observa) > 0:
        caminho = os.path.join(output_dir, 'tabelao_indicadores_observa.csv')
        df_observa.to_csv(caminho, index=False, encoding='utf-8-sig')
        print(f"Salvo: tabelao_indicadores_observa.csv ({len(df_observa)} registros, {df_observa['Distrito'].nunique()} distritos)")
    
    if df_alimentos is not None and len(df_alimentos) > 0:
        caminho = os.path.join(output_dir, 'tabelao_valores_alimentos.csv')
        df_alimentos.to_csv(caminho, index=False, encoding='utf-8-sig')
        print(f"Salvo: tabelao_valores_alimentos.csv ({len(df_alimentos)} registros)")
    
    print(f"\nArquivos em: {output_dir}")
    return output_dir

def main():
    print("Consolidando os dados")
    
    try:
        df_beneficios = consolidar_beneficios()
        df_mapa = consolidar_mapa_desigualdade()
        df_observa = consolidar_observasampa()
        df_alimentos = consolidar_valores_alimentos()
        
        salvar_consolidados(df_beneficios, df_mapa, df_observa, df_alimentos)
        
        print("Finalizado")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()