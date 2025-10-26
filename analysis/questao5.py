import pandas as pd
import numpy as np
import os

def preparar_dados_transferencia_renda(regiao='SE'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    path_beneficios = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_beneficios.csv')
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_5_transferencia_renda.csv')
    
    if not os.path.exists(path_beneficios):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_beneficios}")
    if not os.path.exists(path_observa):
        print(f"AVISO: ObservaSampa não encontrado: {path_observa} -- seguirei apenas com o tabelão de benefícios.")
    
    print(f"Carregando dados de benefícios: {path_beneficios}")
    df_beneficios = pd.read_csv(path_beneficios, encoding='utf-8')
    print(f"Carregando dados do ObservaSampa: {path_observa}")
    df_observa = pd.read_csv(path_observa, encoding='utf-8')
    
    # Indicadores relacionados à pergunta 5
    indicadores_transferencia = [
        '010302 QUANTIDADE DE FAMILIAS BENEFICIARIAS DO PROGRAMA BOLSA FAMILIA',
        '010301 QUANTIDADE DE FAMILIAS QUE RECEBEM RECURSOS DOS PROGRAMAS DE TRANSFERENCIA DE RENDA',
        'V0205 FAMILIAS BENEFICIADAS PELO BOLSA FAMILIA',
        'V0206 FAMILIAS QUE RECEBEM RECURSOS DOS PROGRAMAS DE TRANSFERENCIA DE RENDA'
    ]
    
    # Função auxiliar para achar as colunas
    def achar_col(df, candidates):
        cols = list(df.columns)
        for c in candidates:
            if c in cols:
                return c
        lc = {c.lower(): c for c in cols}
        for cand in candidates:
            if cand.lower() in lc:
                return lc[cand.lower()]
        return None

    col_subpref = achar_col(df_beneficios, ['Subprefeitura', 'Subprefeitura', 'SubPrefeitura'])
    col_distr = achar_col(df_beneficios, ['Distrito', 'distrito'])
    col_prog = achar_col(df_beneficios, ['Programa', 'programa'])
    col_cat = achar_col(df_beneficios, ['Categoria', 'categoria'])
    col_qt = achar_col(df_beneficios, ['Quantidade_Beneficiados', 'Quantidade', 'Quantidade_Beneficiario', 'QuantidadeBeneficiados'])

    if col_qt is None or col_prog is None or col_distr is None:
        raise RuntimeError('Arquivo de benefícios não contém as colunas esperadas (Programa/Distrito/Quantidade).')

    df_beneficios[col_qt] = pd.to_numeric(df_beneficios[col_qt], errors='coerce').fillna(0).astype(int)

    # Filtar pela região da SE
    if col_subpref is not None:
        df_benef_region = df_beneficios[df_beneficios[col_subpref].astype(str).str.upper() == str(regiao).upper()].copy()
    else:
        df_benef_region = df_beneficios.copy()

    # Separar os dados por programa e categoria
    df_resumo_beneficios = df_benef_region.groupby([col_distr, col_prog, col_cat], as_index=False)[col_qt].sum()
    df_resumo_beneficios = df_resumo_beneficios.rename(columns={col_distr: 'Distrito', col_prog: 'Programa', col_cat: 'Categoria', col_qt: 'Quantidade_Beneficiados'})

    # Narmaliznado as colunas
    df_resumo_beneficios['Programa_up'] = df_resumo_beneficios['Programa'].astype(str).str.upper()
    df_resumo_beneficios['Categoria_up'] = df_resumo_beneficios['Categoria'].astype(str).str.upper()

    # Calcular os totais por programa
    # Bolsa Família
    mask_bolsa = df_resumo_beneficios['Programa_up'].str.contains('BOLSA')
    df_bolsa = df_resumo_beneficios[mask_bolsa].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum().rename(columns={'Quantidade_Beneficiados': 'BOLSA_FAMILIA'})

    # BPC
    mask_bpc_prog = df_resumo_beneficios['Programa_up'].str.contains('BPC')
    mask_bpc_cat = df_resumo_beneficios['Categoria_up'].isin(['PCD', 'IDOSA'])
    df_bpc = df_resumo_beneficios[mask_bpc_prog & mask_bpc_cat].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum().rename(columns={'Quantidade_Beneficiados': 'BPC'})

    # CadUnico
    mask_cad = df_resumo_beneficios['Programa_up'].str.contains('CADUNICO')
    df_cad = df_resumo_beneficios[mask_cad].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum().rename(columns={'Quantidade_Beneficiados': 'CADUNICO'})

    # dataframe por distrito com os torais
    df_pivot = df_bolsa.merge(df_bpc, on='Distrito', how='outer').merge(df_cad, on='Distrito', how='outer').fillna(0)
    df_pivot['BOLSA_FAMILIA'] = df_pivot['BOLSA_FAMILIA'].astype(int)
    df_pivot['BPC'] = df_pivot['BPC'].astype(int)
    df_pivot['CADUNICO'] = df_pivot['CADUNICO'].astype(int)
    
    df_observa_filtrado = df_observa[
        (df_observa['Nome'].isin(indicadores_transferencia)) & 
        (df_observa['Período'] == 2024)
    ].copy()
    
    if df_observa_filtrado.empty:
        print("AVISO: Nenhum indicador do ObservaSampa encontrado para 2024")
        df_observa_resumo = pd.DataFrame(columns=['Distrito', 'Media_Familias_Indicadores'])
    else:
        df_observa_filtrado['Resultado'] = pd.to_numeric(
            df_observa_filtrado['Resultado'], 
            errors='coerce'
        )
        
        # Juntar por distrito e calcular a média
        df_observa_resumo = df_observa_filtrado.groupby('Distrito').agg({
            'Resultado': 'mean'
        }).reset_index()
        df_observa_resumo = df_observa_resumo.rename(columns={'Resultado': 'Media_Familias_Indicadores'})
    
    df_resultado = df_pivot.merge(df_observa_resumo, on='Distrito', how='left')
    
    # Calcular o total de beneficiados
    df_resultado['Total_Beneficiados'] = (
        df_resultado['BOLSA_FAMILIA'] + 
        df_resultado['BPC'] + 
        df_resultado['CADUNICO']
    )
    
    # Calcular os percentuais de cada programa
    df_resultado['Perc_Bolsa_Familia'] = np.where(
        df_resultado['Total_Beneficiados'] > 0,
        (df_resultado['BOLSA_FAMILIA'] / df_resultado['Total_Beneficiados']) * 100,
        0
    )
    
    df_resultado['Perc_BPC'] = np.where(
        df_resultado['Total_Beneficiados'] > 0,
        (df_resultado['BPC'] / df_resultado['Total_Beneficiados']) * 100,
        0
    )
    
    df_resultado['Perc_CadUnico'] = np.where(
        df_resultado['Total_Beneficiados'] > 0,
        (df_resultado['CADUNICO'] / df_resultado['Total_Beneficiados']) * 100,
        0
    )
    
    # Reorganizar colunas
    colunas_finais = [
        'Distrito', 
        'BOLSA_FAMILIA', 
        'BPC', 
        'CADUNICO',
        'Total_Beneficiados',
        'Media_Familias_Indicadores',
        'Perc_Bolsa_Familia',
        'Perc_BPC',
        'Perc_CadUnico'
    ]

    df_final = df_resultado[colunas_finais].copy()
    
    # Arredondar os valores
    colunas_arredondar = ['Media_Familias_Indicadores', 'Perc_Bolsa_Familia', 'Perc_BPC', 'Perc_CadUnico']
    for col in colunas_arredondar:
        if col in df_final.columns:
            df_final[col] = df_final[col].round(2)
    
    return df_final, path_output

if __name__ == "__main__":
    try:
        df_resultado, output_path = preparar_dados_transferencia_renda(regiao='SE')

        # Salvar o CSV de resumo por distrito
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')

        # Resposta da pergunta 5: total de famílias atendidas pelo Bolsa Família na região
        total_bolsa = int(df_resultado['BOLSA_FAMILIA'].sum()) if 'BOLSA_FAMILIA' in df_resultado.columns else 0
        print(total_bolsa)
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()