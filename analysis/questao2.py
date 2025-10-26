import os
import pandas as pd
import numpy as np

def preparar_dados_extrema_pobreza():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_mapa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_mapa.csv')
    path_cadunico = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'cadunico_familias_jul24_tratado.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_2_extrema_pobreza.csv')

    if not os.path.exists(path_observa) and not os.path.exists(path_cadunico):
        raise FileNotFoundError(f"Nenhum dos arquivos esperados foi encontrado:\n {path_observa}\n {path_cadunico}")

    df_observa = pd.read_csv(path_observa, encoding='utf-8') if os.path.exists(path_observa) else None
    df_cadunico = pd.read_csv(path_cadunico, encoding='utf-8') if os.path.exists(path_cadunico) else None

    # Indicadores relacionados à pergunta 2 (extrema pobreza)
    indicadores_pobreza = [
        '010101 QUANTIDADE DE FAMILIAS EM SITUACAO DE EXTREMA POBREZA ATE 14 SALARIO MINIMO',
        '010201 QUANTIDADE DE FAMILIAS EM SITUACAO DE POBREZA RENDA POR PESSOA DE ATE DE SALARIOMINIMO',
        '010202 QUANTIDADE DE FAMILIAS EM SITUACAO DE BAIXA RENDA RENDA POR PESSOA DE ATE SALARIO MINIMO',
        'V0204 FAMILIAS NO CADASTRO UNICO EM SITUACAO DE EXTREMA POBREZA',
        'V0717 FAMILIAS COM RENDA PER CAPITA ACIMA DE ATE SALARIOMINIMO CADASTRADAS NO CADUNICO'
    ]

    # Função auxiliar para buscar colunas
    def col_existente(df, candidates):
        if df is None:
            return None
        cols = list(df.columns)
        for c in candidates:
            if c in cols:
                return c
        lc = {c.lower(): c for c in cols}
        for cand in candidates:
            if cand.lower() in lc:
                return lc[cand.lower()]
        return None

    # Procesasndo os dados do ObservaSampa
    df_counts = pd.DataFrame(columns=['Distrito', 'Categoria', 'Quantidade_Familias'])
    if df_observa is not None:
        col_nome = col_existente(df_observa, ['Nome', 'INDICADOR', 'Indicador', 'nome'])
        col_periodo = col_existente(df_observa, ['Período', 'Periodo', 'ANO', 'Ano'])
        col_result = col_existente(df_observa, ['Resultado', 'Valor', 'resultado', 'Valor Resultado'])
        col_distrito = col_existente(df_observa, ['Distrito', 'distrito', 'Area', 'Regiao'])
        if None not in (col_nome, col_periodo, col_result, col_distrito):
            df_observa[col_result] = pd.to_numeric(df_observa[col_result], errors='coerce')
            
            # Filtrar pelo período de 2024
            mask = df_observa[col_nome].isin(indicadores_pobreza) & df_observa[col_periodo].astype(str).str.contains('2024')
            df_filtrado = df_observa[mask].copy()
            if not df_filtrado.empty:
                
                # Renomear as colunas
                df_filtrado = df_filtrado.rename(columns={col_distrito: 'Distrito', col_nome: 'Nome', col_result: 'Resultado'})
                
                # Categorizar os estados de pobreza
                def categorizar(nome):
                    n = str(nome).upper() if pd.notna(nome) else ''
                    if 'EXTREMA' in n: return 'Extrema Pobreza'
                    if 'POBREZA' in n: return 'Pobreza'
                    if 'BAIXA' in n: return 'Baixa Renda'
                    return 'Outras Faixas'
                df_filtrado['Categoria'] = df_filtrado['Nome'].apply(categorizar)
                
                # Juntar por distrito e categoria
                df_counts = df_filtrado.groupby(['Distrito', 'Categoria'], as_index=False)['Resultado'].sum().rename(columns={'Resultado': 'Quantidade_Familias'})

    # Pegar o total do cadunico por distrito
    totals = None
    if os.path.exists(path_mapa):
        try:
            df_mapa = pd.read_csv(path_mapa, encoding='utf-8')
            col_total = col_existente(df_mapa, ['Total_CadUnico', 'Total_Familias', 'Total_Familia', 'Total'])
            col_distr_mapa = col_existente(df_mapa, ['Distrito', 'distrito', 'Area'])
            if col_total and col_distr_mapa:
                df_mapa[col_total] = pd.to_numeric(df_mapa[col_total], errors='coerce').fillna(0).astype(int)
                totals = df_mapa[[col_distr_mapa, col_total]].rename(columns={col_distr_mapa: 'Distrito', col_total: 'Total_CadUnico'}).groupby('Distrito', as_index=False).max()
        except Exception:
            totals = None

    if totals is None and df_cadunico is not None:
        col_distr_cad = col_existente(df_cadunico, ['Distrito', 'distrito', 'Area'])
        if col_distr_cad:
            df_cadunico = df_cadunico.rename(columns={col_distr_cad: 'Distrito'})
            col_total_cad = col_existente(df_cadunico, ['Total_Familias', 'Total_CadUnico'])
            if col_total_cad:
                df_cadunico[col_total_cad] = pd.to_numeric(df_cadunico[col_total_cad], errors='coerce').fillna(0).astype(int)
                totals = df_cadunico.groupby('Distrito', as_index=False)[col_total_cad].max().rename(columns={col_total_cad: 'Total_CadUnico'})
            else:
                totals = df_cadunico.groupby('Distrito', as_index=False).size().reset_index(name='Total_CadUnico')

    # Soma da quantidade de famílias por distrito
    if totals is None:
        totals = df_counts.groupby('Distrito', as_index=False)['Quantidade_Familias'].sum().rename(columns={'Quantidade_Familias': 'Total_CadUnico'}) if not df_counts.empty else pd.DataFrame(columns=['Distrito', 'Total_CadUnico'])

    # Calculos
    result = df_counts.merge(totals, on='Distrito', how='left')
    if result['Total_CadUnico'].isna().any():
        fallback = result.groupby('Distrito', as_index=False)['Quantidade_Familias'].sum().rename(columns={'Quantidade_Familias': 'Total_CadUnico'})
        result['Total_CadUnico'] = result['Total_CadUnico'].fillna(result['Distrito'].map(fallback.set_index('Distrito')['Total_CadUnico']).fillna(0)).astype(int)

    result['Percentual'] = np.where(
        result['Total_CadUnico'] > 0,
        (result['Quantidade_Familias'] / result['Total_CadUnico']) * 100,
        0
    )
    
    df_final = result[['Distrito', 'Categoria', 'Quantidade_Familias', 'Total_CadUnico', 'Percentual']].sort_values(['Distrito', 'Categoria']).reset_index(drop=True)
    df_final['Percentual'] = df_final['Percentual'].round(2)

    return df_final, path_output

if __name__ == "__main__":
    try:
        df_resultado, output_path = preparar_dados_extrema_pobreza()
        
        # Salvar o CSV de resumo por distrito
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')
        
        # Resposta da pergunta 2: quantidade total de famílias em extrema pobreza
        total_extrema_pobreza = int(df_resultado[df_resultado['Categoria'] == 'Extrema Pobreza']['Quantidade_Familias'].sum()) if 'Extrema Pobreza' in df_resultado['Categoria'].values else 0
        print(total_extrema_pobreza)
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()