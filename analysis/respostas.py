import os
import pandas as pd
import numpy as np

# Questão 2: Extrema Pobreza
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

# Questão 5: Transferência de Renda
def preparar_dados_transferencia_renda(regiao='SE'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    path_beneficios = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_beneficios.csv')
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_5_transferencia_renda.csv')
    
    if not os.path.exists(path_beneficios):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_beneficios}")
    if not os.path.exists(path_observa):
        print(f"AVISO: ObservaSampa não encontrado: {path_observa} -- seguirei apenas com o tabelão de benefícios.")
    
    df_beneficios = pd.read_csv(path_beneficios, encoding='utf-8')
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

# Questão 8: Educação
def preparar_dados_educacao():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_mapa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_mapa.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_8_educacao.csv')
    
    if not os.path.exists(path_observa):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_observa}")
    
    df_observa = pd.read_csv(path_observa, encoding='utf-8')
    df_observa['Nome'] = df_observa['Nome'].astype(str).str.strip()
    df_observa['Distrito'] = df_observa['Distrito'].astype(str).str.strip()
    
    # Indicadores relacionados à pergunta 8 (educação)
    indicadores_educacao_map = {
        '040101': 'Taxa_Universalizacao',
        '040102': 'Alunos_por_Turma',
        '040103': 'Distorcao_Idade_Serie',
        '040104': 'Distorcao_Idade_Serie',
        '040201': 'Demanda_Atendida',
        '040202': 'Demanda_Atendida',
        '040203': 'Alunos_por_Turma',
        '040204': 'Alunos_por_Turma',
        '040A01': 'Educacao_Especial',
        '040A02': 'Educacao_Especial'
    }
    
    # Indicadores complementares
    indicadores_complementares = ['V0009', 'V0015', 'V0050', 'V0054', 'V0611', 'V0612']
    
    # Filtrar dados pelo periodo de 2024
    df_2024 = df_observa[df_observa['Período'] == 2024].copy()
    df_2024['code'] = ''
    all_codes = list(indicadores_educacao_map.keys()) + indicadores_complementares
    for c in all_codes:
        mask = df_2024['Nome'].str.contains(c, na=False)
        df_2024.loc[mask, 'code'] = c
    missing_mask = df_2024['code'] == ''
    df_2024.loc[missing_mask, 'code'] = df_2024.loc[missing_mask, 'Nome'].str.split().str[0].str.upper()
    
    # Processar os indicadores principais
    df_principais = df_2024[df_2024['code'].isin(indicadores_educacao_map.keys())].copy()
    df_principais['Resultado'] = pd.to_numeric(df_principais['Resultado'], errors='coerce')
    
    # Tratar os valores inválidos
    df_principais.loc[df_principais['Resultado'] > 1000, 'Resultado'] = np.nan
    
    # Mapear por categoria
    df_principais['Categoria'] = df_principais['code'].map(indicadores_educacao_map)
    
    # Juntae por distrito e categoria 
    df_resumo = df_principais.groupby(['Distrito', 'Categoria']).agg({'Resultado': 'mean'}).reset_index()
    df_pivot = df_resumo.pivot(index='Distrito', columns='Categoria', values='Resultado').fillna(0).reset_index()
    
    # Processar indicadores complementares
    df_complementar = df_2024[df_2024['code'].isin(indicadores_complementares)].copy()
    df_complementar['Resultado'] = pd.to_numeric(df_complementar['Resultado'], errors='coerce')
    
    # Calcular o total de matrículas por distrito
    df_matriculas = df_complementar[df_complementar['code'].isin(['V0009', 'V0015', 'V0050', 'V0054'])]
    df_total_matriculas = df_matriculas.groupby('Distrito')['Resultado'].sum().reset_index()
    df_total_matriculas = df_total_matriculas.rename(columns={'Resultado': 'Total_Matriculas'})
    
    # Contar o número de escolas por distrito
    df_escolas = df_complementar[df_complementar['code'] == 'V0611']
    df_num_escolas = df_escolas.groupby('Distrito')['Resultado'].sum().reset_index()
    df_num_escolas = df_num_escolas.rename(columns={'Resultado': 'Numero_Escolas'})
    
    # Combinar dados
    df_final = df_pivot.merge(df_total_matriculas, on='Distrito', how='left')
    df_final = df_final.merge(df_num_escolas, on='Distrito', how='left')

    # Adicionar os dados do mapa da desigualdade
    mapa_cols_to_use = [
        'Matrículas no ensino básico em escolas públicas',
        'Abandono escolar no ensino fundamental da rede municipal',
        'Ideb (Escolas públicas - anos iniciais)',
        'Ideb (Escolas públicas - anos finais)'
    ]
    if os.path.exists(path_mapa):
        try:
            df_mapa = pd.read_csv(path_mapa, encoding='utf-8')
            df_mapa['Distrito'] = df_mapa['Distrito'].astype(str).str.strip()
            available = [c for c in mapa_cols_to_use if c in df_mapa.columns]
            if available:
                temp = df_mapa[['Distrito'] + available].copy()
               
                # Limpar os valores não numéricos
                for c in available:
                    temp[c] = pd.to_numeric(temp[c].replace('NAO INFORMADO', np.nan), errors='coerce')
                
                # Renomear as colunas
                rename_map = {
                    'Matrículas no ensino básico em escolas públicas': 'Matriculas_Ensino_Basico',
                    'Abandono escolar no ensino fundamental da rede municipal': 'Abandono_Escolar',
                    'Ideb (Escolas públicas - anos iniciais)': 'Ideb_Iniciais',
                    'Ideb (Escolas públicas - anos finais)': 'Ideb_Finais'
                }
                temp = temp.rename(columns=rename_map)
                df_final = df_final.merge(temp, on='Distrito', how='left')
        except Exception:
            pass

    # Remover as colunas não utilizadas
    for col in ['Demanda_Atendida', 'Distorcao_Idade_Serie', 'Educacao_Especial', 'Alunos_por_Turma']:
        if col in df_final.columns:
            df_final = df_final.drop(columns=[col])
    
    # Calcular os alunos por escola
    df_final['Alunos_por_Escola'] = np.where(
        df_final['Numero_Escolas'] > 0,
        df_final['Total_Matriculas'] / df_final['Numero_Escolas'],
        0
    )
    
    # Substituir valores ausentes
    df_final = df_final.fillna('NAO INFORMADO')
    
    colunas_numericas = df_final.select_dtypes(include=[np.number]).columns
    for col in colunas_numericas:
        df_final[col] = df_final[col].round(2)
    
    df_final = df_final.sort_values('Distrito').reset_index(drop=True)
    
    return df_final, path_output

# Questão 10: Habitação
def preparar_dados_habitacao():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_10_habitacao.csv')
    
    if not os.path.exists(path_observa):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_observa}")
    
    df_observa = pd.read_csv(path_observa, encoding='utf-8')
    
    # Indicadores relacionados à pergunta 10 (habitação)
    indicadores_habitacao_codes = {
        '010502': 'Atendimento_Habitacional',
        '010503': 'Atendimento_Habitacional',
        '110107': 'Domicilios_Favelas',
        '110108': 'Auxilio_Aluguel',
        'V0284': 'Domicilios_Favelas',
        'V0574': 'Auxilio_Aluguel',
        '110103': 'Unidades_Entregues',
        'V0283': 'Unidades_Entregues'
    }

    # Processando os dados do ObservaSampa
    df_2024 = df_observa[df_observa['Período'] == 2024].copy()

    # Normalizar campos
    df_2024['Nome'] = df_2024['Nome'].astype(str).str.strip()
    df_2024['Distrito'] = df_2024['Distrito'].astype(str).str.strip()
    df_2024['code'] = ''
    for code in indicadores_habitacao_codes.keys():
        mask = df_2024['Nome'].str.contains(code, na=False)
        df_2024.loc[mask, 'code'] = code
    missing = df_2024['code'] == ''
    df_2024.loc[missing, 'code'] = df_2024.loc[missing, 'Nome'].str.split().str[0].str.upper()

    # Filtrar os indicadores importantes
    df_habitacao = df_2024[df_2024['code'].isin(indicadores_habitacao_codes.keys())].copy()

    # Converter resultado para numérico
    df_habitacao['Resultado'] = pd.to_numeric(df_habitacao['Resultado'], errors='coerce')
    
    # Tratar os valores inválidos
    df_habitacao.loc[df_habitacao['Resultado'] > 100000, 'Resultado'] = np.nan
    
    # Mapear por categoria
    df_habitacao['Categoria'] = df_habitacao['code'].map(indicadores_habitacao_codes)
    
    # Juntar por categoria e distrito
    df_favelas = df_habitacao[df_habitacao['Categoria'] == 'Domicilios_Favelas'].groupby('Distrito')['Resultado'].sum().reset_index()
    df_favelas = df_favelas.rename(columns={'Resultado': 'Total_Domicilios_Favelas'})

    df_auxilio = df_habitacao[df_habitacao['Categoria'] == 'Auxilio_Aluguel'].groupby('Distrito')['Resultado'].sum().reset_index()
    df_auxilio = df_auxilio.rename(columns={'Resultado': 'Familias_Auxilio_Aluguel'})

    df_atendimento = df_habitacao[df_habitacao['Categoria'] == 'Atendimento_Habitacional'].groupby('Distrito')['Resultado'].sum().reset_index()
    df_atendimento = df_atendimento.rename(columns={'Resultado': 'Atendimento_Habitacional_Provisorio'})

    df_unidades = df_habitacao[df_habitacao['Categoria'] == 'Unidades_Entregues'].groupby('Distrito')['Resultado'].sum().reset_index()
    df_unidades = df_unidades.rename(columns={'Resultado': 'Unidades_Habitacionais_Entregues'})
    
    # Combinar os dados
    all_distritos = pd.Index([])
    for dfc in [df_favelas, df_auxilio, df_atendimento, df_unidades]:
        all_distritos = all_distritos.union(dfc['Distrito'])
    df_final = pd.DataFrame({'Distrito': all_distritos})
    df_final = df_final.merge(df_favelas, on='Distrito', how='left')
    df_final = df_final.merge(df_auxilio, on='Distrito', how='left')
    df_final = df_final.merge(df_atendimento, on='Distrito', how='left')
    df_final = df_final.merge(df_unidades, on='Distrito', how='left')
    df_final = df_final.fillna(0)
    
    # Calcular total de famílias em situação habitacional precária
    df_final['Total_Situacao_Precaria'] = (
        df_final['Total_Domicilios_Favelas'] + 
        df_final['Familias_Auxilio_Aluguel'] + 
        df_final['Atendimento_Habitacional_Provisorio']
    )
    
    # Calcular os percentuais
    df_final['Perc_Favelas'] = np.where(
        df_final['Total_Situacao_Precaria'] > 0,
        (df_final['Total_Domicilios_Favelas'] / df_final['Total_Situacao_Precaria']) * 100,
        0
    )
    
    df_final['Perc_Auxilio_Aluguel'] = np.where(
        df_final['Total_Situacao_Precaria'] > 0,
        (df_final['Familias_Auxilio_Aluguel'] / df_final['Total_Situacao_Precaria']) * 100,
        0
    )
    
    df_final['Taxa_Atendimento'] = np.where(
        df_final['Total_Situacao_Precaria'] > 0,
        (df_final['Unidades_Habitacionais_Entregues'] / df_final['Total_Situacao_Precaria']) * 100,
        0
    )
    
    # Arredondar os valores
    colunas_numericas = df_final.select_dtypes(include=[np.number]).columns
    for col in colunas_numericas:
        df_final[col] = df_final[col].round(2)
    
    # Ordenar por total de situação precária
    df_final = df_final.sort_values('Total_Situacao_Precaria', ascending=False).reset_index(drop=True)
    
    return df_final, path_output

# Execução principal
if __name__ == "__main__":
    print("Iniciando o processamento dos dados para as questões")
    
    # QUESTÃO 2: EXTREMA POBREZA
    print("\n[QUESTÃO 2] Processando dados de extrema pobreza...")
    try:
        df_q2, output_q2 = preparar_dados_extrema_pobreza()
        df_q2.to_csv(output_q2, index=False, encoding='utf-8')
        total_extrema_pobreza = int(df_q2[df_q2['Categoria'] == 'Extrema Pobreza']['Quantidade_Familias'].sum()) if 'Extrema Pobreza' in df_q2['Categoria'].values else 0
        print(f"[QUESTÃO 2] Total de famílias em extrema pobreza: {total_extrema_pobreza}")
    except Exception as e:
        print(f"[QUESTÃO 2] ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    # QUESTÃO 5: TRANSFERÊNCIA DE RENDA
    print("\n[QUESTÃO 5] Processando dados de transferência de renda...")
    try:
        df_q5, output_q5 = preparar_dados_transferencia_renda(regiao='SE')
        df_q5.to_csv(output_q5, index=False, encoding='utf-8')
        total_bolsa = int(df_q5['BOLSA_FAMILIA'].sum()) if 'BOLSA_FAMILIA' in df_q5.columns else 0
        print(f"[QUESTÃO 5] Total de famílias atendidas pelo Bolsa Família (SE): {total_bolsa}")
    except Exception as e:
        print(f"[QUESTÃO 5] ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    # QUESTÃO 8: EDUCAÇÃO
    print("\n[QUESTÃO 8] Processando dados de educação...")
    try:
        df_q8, output_q8 = preparar_dados_educacao()
        df_q8.to_csv(output_q8, index=False, encoding='utf-8')
        total_matriculas = int(df_q8['Total_Matriculas'].replace('NAO INFORMADO', 0).astype(float).sum()) if 'Total_Matriculas' in df_q8.columns else 0
        print(f"[QUESTÃO 8] Total de matrículas na rede municipal: {total_matriculas}")
    except Exception as e:
        print(f"[QUESTÃO 8] ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    # QUESTÃO 10: HABITAÇÃO
    print("\n[QUESTÃO 10] Processando dados de habitação...")
    try:
        df_q10, output_q10 = preparar_dados_habitacao()
        df_q10.to_csv(output_q10, index=False, encoding='utf-8')
        total_favelas = int(df_q10['Total_Domicilios_Favelas'].sum()) if 'Total_Domicilios_Favelas' in df_q10.columns else 0
        print(f"[QUESTÃO 10] Total de domicílios em favelas: {total_favelas}")
    except Exception as e:
        print(f"[QUESTÃO 10] ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPROCESSAMENTO CONCLUÍDO")