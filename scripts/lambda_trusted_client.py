import pandas as pd
import numpy as np
import boto3
from io import StringIO
import json
import os
import csv

def read_and_clean_csv(s3, bucket, key, numeric_cols=None):
    """
    Lê um arquivo CSV do S3 e faz a limpeza básica dos dados
    :param s3: Cliente S3
    :param bucket: Nome do bucket
    :param key: Chave do arquivo
    :param numeric_cols: Lista de colunas que devem ser convertidas para número
    :return: DataFrame limpo ou None em caso de erro
    """
    try:
        # Lê o arquivo do S3
        obj = s3.get_object(Bucket=bucket, Key=key)
        raw = obj['Body'].read()
        # Tentar decodificar com UTF-8, caso falhe, tentar latin-1
        try:
            content = raw.decode('utf-8')
        except Exception:
            try:
                content = raw.decode('latin-1')
            except Exception as e:
                raise Exception(f"Erro ao decodificar arquivo: {e}")

        df = None
        error_msg = None

        # 1) Tentar detectar delimitador com csv.Sniffer usando uma amostra
        try:
            sample = content[:8192]
            dialect = csv.Sniffer().sniff(sample, delimiters=[',',';','\t','|'])
            sep = dialect.delimiter
            df = pd.read_csv(StringIO(content), dtype=str, sep=sep, engine='python')
        except Exception as e:
            error_msg = str(e)

        # 2) Caso falhe, tentar delimitadores comuns com engine python e diferentes encodings
        if df is None:
            for delimiter in [',',';','\t','|']:
                try:
                    df = pd.read_csv(StringIO(content), dtype=str, sep=delimiter, engine='python')
                    if df.shape[1] > 0:
                        break
                except Exception as e:
                    error_msg = str(e)
                    df = None
                    continue

        # 3) Se ainda não foi possível ler, tentar ler pulando cabeçalho e inferir
        if df is None:
            try:
                df = pd.read_csv(StringIO(content), dtype=str, engine='python', header=None)
                # se não tem colunas nomeadas, tentar renomear com índices
                if df.shape[1] == 0:
                    raise Exception('No columns parsed')
            except Exception as e:
                raise Exception(f"Não foi possível ler o arquivo com nenhum delimitador. Último erro: {error_msg} | {e}")
        
        # Converte colunas numéricas se especificadas
        if numeric_cols:
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        print(f"Erro ao ler {key}: {str(e)}")
        return None


def find_column(df, candidates):
    """Procura por uma coluna em um DataFrame usando uma lista de aliases (case-insensitive).
    Retorna o nome real da coluna encontrado ou None.
    """
    if df is None:
        return None
    cols = list(df.columns)
    # busca exata
    for c in candidates:
        if c in cols:
            return c
    # busca case-insensitive
    lc = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lc:
            return lc[cand.lower()]
    # busca por substring
    for cand in candidates:
        for col in cols:
            if cand.lower() in str(col).lower():
                return col
    return None


def detect_quantity_column(df):
    """Tenta detectar automaticamente uma coluna de quantidade/numérica a partir do DataFrame.
    Retorna o nome da coluna encontrada ou None.
    """
    if df is None:
        return None
    best_col = None
    best_count = 0
    for col in df.columns:
        # tentar converter e contar valores numéricos
        try:
            numeric = pd.to_numeric(df[col], errors='coerce')
            non_null = numeric.notna().sum()
            if non_null > best_count:
                best_count = non_null
                best_col = col
        except Exception:
            continue
    # exigir pelo menos alguns valores numéricos
    if best_count >= 3:
        return best_col
    return None

def get_bucket_names():
    """Obtém os nomes dos buckets trusted e client e lista os arquivos disponíveis"""
    try:
        s3 = boto3.client('s3')
        response = s3.list_buckets()
        trusted_bucket = None
        client_bucket = None
        
        for bucket in response['Buckets']:
            if 't4g-tr' in bucket['Name']:
                trusted_bucket = bucket['Name']
            elif 't4g-cu' in bucket['Name']:
                client_bucket = bucket['Name']
                
        if not trusted_bucket or not client_bucket:
            raise Exception("Buckets não encontrados")
        
        # Lista os arquivos no bucket trusted para debug
        print("Arquivos disponíveis no bucket trusted:")
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=trusted_bucket):
            if 'Contents' in page:
                for obj in page['Contents']:
                    print(f"- {obj['Key']}")
            
        return trusted_bucket, client_bucket
    except Exception as e:
        print(f"Erro ao obter nomes dos buckets: {str(e)}")
        raise

def process_extrema_pobreza(s3, trusted_bucket, client_bucket):
    """Processa dados de extrema pobreza"""
    try:
        # Lê os arquivos necessários do bucket trusted
        path_observa = 'Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv'
        path_mapa = 'Arquivos_Tratados/mapa_da_desigualdade_2024_dados_tratado.csv'
        path_cadunico = 'Arquivos_Tratados/cadunico_familias_jul24_tratado.csv'
        
        # Lista para armazenar os DataFrames carregados
        dfs = {}
        
        # Lê os arquivos necessários
        dfs['observa'] = read_and_clean_csv(s3, trusted_bucket, path_observa, ['Resultado'])
        dfs['mapa'] = read_and_clean_csv(s3, trusted_bucket, path_mapa, ['Total_CadUnico', 'Total_Familias'])
        dfs['cadunico'] = read_and_clean_csv(s3, trusted_bucket, path_cadunico, ['Total_Familias'])

        # Indicadores relacionados à extrema pobreza
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

        # Processando os dados do ObservaSampa
        df_counts = pd.DataFrame(columns=['Distrito', 'Categoria', 'Quantidade_Familias'])
        if dfs['observa'] is not None:
            col_nome = col_existente(dfs['observa'], ['Nome', 'INDICADOR', 'Indicador', 'nome'])
            col_periodo = col_existente(dfs['observa'], ['Período', 'Periodo', 'ANO', 'Ano'])
            col_result = col_existente(dfs['observa'], ['Resultado', 'Valor', 'resultado', 'Valor Resultado'])
            col_distrito = col_existente(dfs['observa'], ['Distrito', 'distrito', 'Area', 'Regiao'])
            
            if None not in (col_nome, col_periodo, col_result, col_distrito):
                dfs['observa'][col_result] = pd.to_numeric(dfs['observa'][col_result], errors='coerce')
                
                # Converter resultado para numérico antes do filtro e preencher NaN com 0
            dfs['observa'][col_result] = pd.to_numeric(dfs['observa'][col_result], errors='coerce').fillna(0)

            # Filtrar pelo período de 2024
            mask = dfs['observa'][col_nome].isin(indicadores_pobreza) & dfs['observa'][col_periodo].astype(str).str.contains('2024')
            df_filtrado = dfs['observa'][mask].copy()
            
            if not df_filtrado.empty:
                # Renomear as colunas
                df_filtrado = df_filtrado.rename(columns={
                    col_distrito: 'Distrito', 
                    col_nome: 'Nome', 
                    col_result: 'Resultado'
                })
                
                # Categorizar os estados de pobreza
                def categorizar(nome):
                    n = str(nome).upper() if pd.notna(nome) else ''
                    if 'EXTREMA' in n: return 'Extrema Pobreza'
                    if 'POBREZA' in n: return 'Pobreza'
                    if 'BAIXA' in n: return 'Baixa Renda'
                    return 'Outras Faixas'
                
                df_filtrado['Categoria'] = df_filtrado['Nome'].apply(categorizar)
                
                # Garantir que Resultado é numérico
                df_filtrado['Resultado'] = pd.to_numeric(df_filtrado['Resultado'], errors='coerce').fillna(0)
                
                # Juntar por distrito e categoria
                df_counts = df_filtrado.groupby(['Distrito', 'Categoria'], as_index=False)['Resultado'].sum()
                df_counts = df_counts.rename(columns={'Resultado': 'Quantidade_Familias'})
                # Garantir que Quantidade_Familias seja numérica
                df_counts['Quantidade_Familias'] = pd.to_numeric(df_counts['Quantidade_Familias'], errors='coerce').fillna(0).astype(int)

        # Pegar o total do CadÚnico por distrito
        totals = None
        if dfs['mapa'] is not None:
            try:
                col_total = col_existente(dfs['mapa'], ['Total_CadUnico', 'Total_Familias', 'Total_Familia', 'Total'])
                col_distr_mapa = col_existente(dfs['mapa'], ['Distrito', 'distrito', 'Area'])
                if col_total and col_distr_mapa:
                    dfs['mapa'][col_total] = pd.to_numeric(dfs['mapa'][col_total], errors='coerce').fillna(0).astype(int)
                    totals = dfs['mapa'][[col_distr_mapa, col_total]]
                    totals = totals.rename(columns={col_distr_mapa: 'Distrito', col_total: 'Total_CadUnico'})
                    totals = totals.groupby('Distrito', as_index=False).max()
            except Exception:
                totals = None

        if totals is None and dfs['cadunico'] is not None:
            col_distr_cad = col_existente(dfs['cadunico'], ['Distrito', 'distrito', 'Area'])
            if col_distr_cad:
                dfs['cadunico'] = dfs['cadunico'].rename(columns={col_distr_cad: 'Distrito'})
                col_total_cad = col_existente(dfs['cadunico'], ['Total_Familias', 'Total_CadUnico'])
                if col_total_cad:
                    dfs['cadunico'][col_total_cad] = pd.to_numeric(dfs['cadunico'][col_total_cad], errors='coerce').fillna(0).astype(int)
                    totals = dfs['cadunico'].groupby('Distrito', as_index=False)[col_total_cad].max()
                    totals = totals.rename(columns={col_total_cad: 'Total_CadUnico'})
                else:
                    totals = dfs['cadunico'].groupby('Distrito', as_index=False).size()
                    totals = totals.reset_index(name='Total_CadUnico')

        if totals is None:
            totals = df_counts.groupby('Distrito', as_index=False)['Quantidade_Familias'].sum()
            totals = totals.rename(columns={'Quantidade_Familias': 'Total_CadUnico'})
            if totals.empty:
                totals = pd.DataFrame(columns=['Distrito', 'Total_CadUnico'])

        # Cálculos finais
        result = df_counts.merge(totals, on='Distrito', how='left')
        if result['Total_CadUnico'].isna().any():
            fallback = result.groupby('Distrito', as_index=False)['Quantidade_Familias'].sum()
            fallback = fallback.rename(columns={'Quantidade_Familias': 'Total_CadUnico'})
            result['Total_CadUnico'] = result['Total_CadUnico'].fillna(
                result['Distrito'].map(fallback.set_index('Distrito')['Total_CadUnico']).fillna(0)
            ).astype(int)

        result['Percentual'] = np.where(
            result['Total_CadUnico'] > 0,
            (result['Quantidade_Familias'] / result['Total_CadUnico']) * 100,
            0
        )
        
        df_final = result[['Distrito', 'Categoria', 'Quantidade_Familias', 'Total_CadUnico', 'Percentual']]
        df_final = df_final.sort_values(['Distrito', 'Categoria']).reset_index(drop=True)
        df_final['Percentual'] = df_final['Percentual'].round(2)

        # Salva o resultado no bucket client
        output_buffer = StringIO()
        df_final.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
        
        s3.put_object(
            Bucket=client_bucket,
            Key='resultados/dados_pergunta_2_extrema_pobreza.csv',
            Body=output_buffer.getvalue().encode('utf-8-sig')
        )

        return True

    except Exception as e:
        print(f"Erro ao processar dados de extrema pobreza: {str(e)}")
        raise

def process_transferencia_renda(s3, trusted_bucket, client_bucket, regiao='SE'):
    """Processa dados de transferência de renda"""
    try:
        # Lê os arquivos necessários do bucket trusted
        path_bolsa = 'Arquivos_Tratados/programa_bolsafamilia_2024_1_tratado.csv'
        path_bpc = 'Arquivos_Tratados/BPC_Setembro_2024_tratado.csv'
        path_cadunico = 'Arquivos_Tratados/cadunico_familias_jul24_tratado.csv'
        path_observa = 'Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv'
        
        # Lê e concatena os dados de benefícios
        dfs_beneficios = []
        
        # Bolsa Família
        df_bolsa = read_and_clean_csv(s3, trusted_bucket, path_bolsa, ['Total_Familias'])
        if df_bolsa is not None:
            df_bolsa['Programa'] = 'BOLSA FAMILIA'
            dfs_beneficios.append(df_bolsa)
        
        # BPC
        df_bpc = read_and_clean_csv(s3, trusted_bucket, path_bpc, ['Total'])
        if df_bpc is not None:
            df_bpc['Programa'] = 'BPC'
            dfs_beneficios.append(df_bpc)
        
        # CadÚnico
        df_cad = read_and_clean_csv(s3, trusted_bucket, path_cadunico, ['Total_Familias'])
        if df_cad is not None:
            df_cad['Programa'] = 'CADUNICO'
            dfs_beneficios.append(df_cad)

        if not dfs_beneficios:
            raise FileNotFoundError("Nenhum arquivo de benefícios encontrado")

        dfs = {}
        dfs['beneficios'] = pd.concat(dfs_beneficios, ignore_index=True)
        dfs['observa'] = read_and_clean_csv(s3, trusted_bucket, path_observa, ['Resultado'])
        
        if dfs['observa'] is None:
            print(f"AVISO: ObservaSampa não encontrado: {path_observa}")

        # Indicadores relacionados à transferência de renda
        indicadores_transferencia = [
            '010302 QUANTIDADE DE FAMILIAS BENEFICIARIAS DO PROGRAMA BOLSA FAMILIA',
            '010301 QUANTIDADE DE FAMILIAS QUE RECEBEM RECURSOS DOS PROGRAMAS DE TRANSFERENCIA DE RENDA',
            'V0205 FAMILIAS BENEFICIADAS PELO BOLSA FAMILIA',
            'V0206 FAMILIAS QUE RECEBEM RECURSOS DOS PROGRAMAS DE TRANSFERENCIA DE RENDA'
        ]

        # Função auxiliar para achar as colunas (usa find_column global como fallback)
        def achar_col(df, candidates):
            col = None
            try:
                cols = list(df.columns)
                for c in candidates:
                    if c in cols:
                        return c
                lc = {c.lower(): c for c in cols}
                for cand in candidates:
                    if cand.lower() in lc:
                        return lc[cand.lower()]
            except Exception:
                pass
            # fallback mais flexível
            return find_column(df, candidates)

        col_subpref = achar_col(dfs['beneficios'], ['Subprefeitura', 'Subprefeitura', 'SubPrefeitura'])
        col_distr = achar_col(dfs['beneficios'], ['Distrito', 'distrito', 'Area', 'Regiao'])
        col_prog = achar_col(dfs['beneficios'], ['Programa', 'programa', 'PROGRAMA'])
        col_cat = achar_col(dfs['beneficios'], ['Categoria', 'categoria', 'CATEGORIA'])
        col_qt = achar_col(dfs['beneficios'], ['Quantidade_Beneficiados', 'Quantidade', 'Quantidade_Beneficiario', 'Total_Beneficiarios', 'Total'])

        # Se não encontrou coluna de quantidade, tenta detectar automaticamente
        if col_qt is None:
            detected = detect_quantity_column(dfs['beneficios'])
            if detected:
                col_qt = detected
                print(f"Coluna de quantidade detectada automaticamente: {col_qt}")

        if col_prog is None or col_distr is None:
            raise RuntimeError('Arquivo de benefícios não contém as colunas obrigatórias (Programa/Distrito).')

        # Converter coluna de quantidade para numérico, se houver
        if col_qt is not None:
            dfs['beneficios'][col_qt] = pd.to_numeric(dfs['beneficios'][col_qt], errors='coerce').fillna(0).astype(int)
        else:
            raise RuntimeError('Não foi possível identificar a coluna de quantidade em benefícios.')

        # Filtar pela região da SE
        if col_subpref is not None:
            df_benef_region = dfs['beneficios'][dfs['beneficios'][col_subpref].astype(str).str.upper() == str(regiao).upper()].copy()
        else:
            df_benef_region = dfs['beneficios'].copy()

        # Separar os dados por programa e categoria
        df_resumo_beneficios = df_benef_region.groupby([col_distr, col_prog, col_cat], as_index=False)[col_qt].sum()
        df_resumo_beneficios = df_resumo_beneficios.rename(columns={
            col_distr: 'Distrito', 
            col_prog: 'Programa', 
            col_cat: 'Categoria', 
            col_qt: 'Quantidade_Beneficiados'
        })

        # Normalizando as colunas
        df_resumo_beneficios['Programa_up'] = df_resumo_beneficios['Programa'].astype(str).str.upper()
        df_resumo_beneficios['Categoria_up'] = df_resumo_beneficios['Categoria'].astype(str).str.upper()

        # Calcular os totais por programa
        # Bolsa Família
        mask_bolsa = df_resumo_beneficios['Programa_up'].str.contains('BOLSA')
        df_bolsa = df_resumo_beneficios[mask_bolsa].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum()
        df_bolsa = df_bolsa.rename(columns={'Quantidade_Beneficiados': 'BOLSA_FAMILIA'})

        # BPC
        mask_bpc_prog = df_resumo_beneficios['Programa_up'].str.contains('BPC')
        mask_bpc_cat = df_resumo_beneficios['Categoria_up'].isin(['PCD', 'IDOSA'])
        df_bpc = df_resumo_beneficios[mask_bpc_prog & mask_bpc_cat].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum()
        df_bpc = df_bpc.rename(columns={'Quantidade_Beneficiados': 'BPC'})

        # CadUnico
        mask_cad = df_resumo_beneficios['Programa_up'].str.contains('CADUNICO')
        df_cad = df_resumo_beneficios[mask_cad].groupby('Distrito', as_index=False)['Quantidade_Beneficiados'].sum()
        df_cad = df_cad.rename(columns={'Quantidade_Beneficiados': 'CADUNICO'})

        # DataFrame por distrito com os totais
        df_pivot = df_bolsa.merge(df_bpc, on='Distrito', how='outer').merge(df_cad, on='Distrito', how='outer').fillna(0)
        df_pivot['BOLSA_FAMILIA'] = df_pivot['BOLSA_FAMILIA'].astype(int)
        df_pivot['BPC'] = df_pivot['BPC'].astype(int)
        df_pivot['CADUNICO'] = df_pivot['CADUNICO'].astype(int)
        
        # Processar dados do ObservaSampa se disponível
        if dfs['observa'] is not None:
            df_observa_filtrado = dfs['observa'][
                (dfs['observa']['Nome'].isin(indicadores_transferencia)) & 
                (dfs['observa']['Período'] == 2024)
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
        else:
            df_observa_resumo = pd.DataFrame(columns=['Distrito', 'Media_Familias_Indicadores'])
        
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

        # Salva o resultado no bucket client
        output_buffer = StringIO()
        df_final.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
        
        s3.put_object(
            Bucket=client_bucket,
            Key='resultados/dados_pergunta_5_transferencia_renda.csv',
            Body=output_buffer.getvalue().encode('utf-8-sig')
        )

        return True

    except Exception as e:
        print(f"Erro ao processar dados de transferência de renda: {str(e)}")
        raise

def process_educacao(s3, trusted_bucket, client_bucket):
    """Processa dados de educação"""
    try:
        # Lê os arquivos necessários do bucket trusted
        path_observa = 'Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv'
        path_mapa = 'Arquivos_Tratados/mapa_da_desigualdade_2024_dados_tratado.csv'
        
        # Lista para armazenar os DataFrames carregados
        dfs = {}
        
        # Lê os arquivos necessários
        dfs['observa'] = read_and_clean_csv(s3, trusted_bucket, path_observa, ['Resultado'])
        dfs['mapa'] = read_and_clean_csv(s3, trusted_bucket, path_mapa)

        if dfs['observa'] is None:
            raise FileNotFoundError(f"Arquivo não encontrado: {path_observa}")

        # localizar colunas flexivelmente
        col_nome = find_column(dfs['observa'], ['Nome', 'INDICADOR', 'Indicador', 'nome'])
        col_distr = find_column(dfs['observa'], ['Distrito', 'distrito', 'Area', 'Regiao', 'Subprefeitura'])
        col_periodo = find_column(dfs['observa'], ['Período', 'Periodo', 'ANO', 'Ano'])
        col_result = find_column(dfs['observa'], ['Resultado', 'Valor', 'resultado', 'Valor Resultado'])

        if None in (col_nome, col_distr, col_periodo, col_result):
            raise RuntimeError(f"Arquivo ObservaSampa não contém as colunas esperadas. Colunas encontradas: {list(dfs['observa'].columns)}")

        dfs['observa'][col_nome] = dfs['observa'][col_nome].astype(str).str.strip()
        dfs['observa'][col_distr] = dfs['observa'][col_distr].astype(str).str.strip()

        # Indicadores relacionados à educação
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

        # Filtra os dados do ObservaSampa para 2024
        df_educacao = dfs['observa'][dfs['observa'][col_periodo].astype(str).str.contains('2024')].copy()

        # Função para mapear o tipo de indicador
        def get_tipo_indicador(nome):
            for codigo, tipo in indicadores_educacao_map.items():
                if codigo in str(nome):
                    return tipo
            for complementar in indicadores_complementares:
                if complementar in str(nome):
                    return 'Complementar'
            return None

        # Aplica o mapeamento
        df_educacao['Tipo_Indicador'] = df_educacao[col_nome].apply(get_tipo_indicador)
        df_educacao = df_educacao[df_educacao['Tipo_Indicador'].notna()]

        # Converte resultado para numérico
        df_educacao[col_result] = pd.to_numeric(df_educacao[col_result], errors='coerce')

        # Calcula médias por tipo de indicador
        df_resumo = df_educacao.groupby([col_distr, 'Tipo_Indicador'])[col_result].mean().reset_index()

        # Pivota para ter os tipos como colunas
        df_final = df_resumo.pivot(
            index=col_distr,
            columns='Tipo_Indicador',
            values=col_result
        ).reset_index()

        # Preenche valores ausentes com zero
        df_final = df_final.fillna(0)

        # Garante que todas as colunas esperadas existam
        colunas_esperadas = [
            'Taxa_Universalizacao',
            'Alunos_por_Turma',
            'Distorcao_Idade_Serie',
            'Demanda_Atendida',
            'Educacao_Especial',
            'Complementar'
        ]
        for col in colunas_esperadas:
            if col not in df_final.columns:
                df_final[col] = 0

        # Arredonda os valores
        for col in df_final.columns:
            if col != col_distr:
                df_final[col] = df_final[col].round(2)

        # Ordena por distrito
        df_final = df_final.sort_values(col_distr).reset_index(drop=True)

        # Salva o resultado no bucket client
        output_buffer = StringIO()
        df_final.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
        
        s3.put_object(
            Bucket=client_bucket,
            Key='resultados/dados_pergunta_8_educacao.csv',
            Body=output_buffer.getvalue().encode('utf-8-sig')
        )

        return True

    except Exception as e:
        print(f"Erro ao processar dados de educação: {str(e)}")
        raise

def process_habitacao(s3, trusted_bucket, client_bucket):
    """Processa dados de habitação"""
    try:
        # Lê os arquivos necessários do bucket trusted
        path_observa = 'Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv'
        
        # Lê o arquivo do ObservaSampa com tratamento numérico
        df_observa = read_and_clean_csv(s3, trusted_bucket, path_observa, ['Resultado'])
        if df_observa is None:
            raise FileNotFoundError(f"Arquivo não encontrado: {path_observa}")

        # Indicadores relacionados à habitação
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

        # localizar colunas flexivelmente
        col_nome = find_column(df_observa, ['Nome', 'INDICADOR', 'Indicador', 'nome'])
        col_distr = find_column(df_observa, ['Distrito', 'distrito', 'Area', 'Regiao', 'Subprefeitura'])
        col_periodo = find_column(df_observa, ['Período', 'Periodo', 'ANO', 'Ano'])

        if None in (col_nome, col_distr, col_periodo):
            raise RuntimeError(f"Arquivo ObservaSampa não contém as colunas esperadas. Colunas encontradas: {list(df_observa.columns)}")

        # Processa os dados do ObservaSampa filtrando 2024
        df_2024 = df_observa[df_observa[col_periodo].astype(str).str.contains('2024')].copy()

        # Normalizar campos
        df_2024[col_nome] = df_2024[col_nome].astype(str).str.strip()
        df_2024[col_distr] = df_2024[col_distr].astype(str).str.strip()
        df_2024['code'] = ''
        df_2024['code'] = ''
        
        for code in indicadores_habitacao_codes.keys():
            mask = df_2024[col_nome].str.contains(code, na=False)
            df_2024.loc[mask, 'code'] = code
        
        missing = df_2024['code'] == ''
        df_2024.loc[missing, 'code'] = df_2024.loc[missing, col_nome].str.split().str[0].str.upper()

        # Filtrar os indicadores importantes
        df_habitacao = df_2024[df_2024['code'].isin(indicadores_habitacao_codes.keys())].copy()

        # Converter resultado para numérico
        df_habitacao['Resultado'] = pd.to_numeric(df_habitacao['Resultado'], errors='coerce')
        
        # Tratar os valores inválidos
        df_habitacao.loc[df_habitacao['Resultado'] > 100000, 'Resultado'] = np.nan
        
        # Mapear por categoria
        df_habitacao['Categoria'] = df_habitacao['code'].map(indicadores_habitacao_codes)
        
        # Juntar por categoria e distrito
        df_favelas = df_habitacao[df_habitacao['Categoria'] == 'Domicilios_Favelas'].groupby(col_distr)['Resultado'].sum().reset_index()
        df_favelas = df_favelas.rename(columns={'Resultado': 'Total_Domicilios_Favelas', col_distr: 'Distrito'})

        df_auxilio = df_habitacao[df_habitacao['Categoria'] == 'Auxilio_Aluguel'].groupby(col_distr)['Resultado'].sum().reset_index()
        df_auxilio = df_auxilio.rename(columns={'Resultado': 'Familias_Auxilio_Aluguel', col_distr: 'Distrito'})

        df_atendimento = df_habitacao[df_habitacao['Categoria'] == 'Atendimento_Habitacional'].groupby(col_distr)['Resultado'].sum().reset_index()
        df_atendimento = df_atendimento.rename(columns={'Resultado': 'Atendimento_Habitacional_Provisorio', col_distr: 'Distrito'})

        df_unidades = df_habitacao[df_habitacao['Categoria'] == 'Unidades_Entregues'].groupby(col_distr)['Resultado'].sum().reset_index()
        df_unidades = df_unidades.rename(columns={'Resultado': 'Unidades_Habitacionais_Entregues', col_distr: 'Distrito'})
        
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

        # Salva o resultado no bucket client
        output_buffer = StringIO()
        df_final.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
        
        s3.put_object(
            Bucket=client_bucket,
            Key='resultados/dados_pergunta_10_habitacao.csv',
            Body=output_buffer.getvalue().encode('utf-8-sig')
        )

        return True

    except Exception as e:
        print(f"Erro ao processar dados de habitação: {str(e)}")
        raise

def consolidar_dados(s3, trusted_bucket):
    """Consolida os dados necessários antes do processamento"""
    try:
        # Verificar se os arquivos consolidados existem
        consolidados = {
            'tabelao_beneficios.csv': False,
            'tabelao_indicadores_observa.csv': False,
            'tabelao_indicadores_mapa.csv': False
        }
        
        # Lista arquivos no diretório consolidados
        try:
            response = s3.list_objects_v2(
                Bucket=trusted_bucket,
                Prefix='Arquivos_Tratados/Consolidados/'
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    for arquivo in consolidados:
                        if arquivo in obj['Key']:
                            consolidados[arquivo] = True
        except Exception as e:
            print(f"Erro ao listar arquivos consolidados: {str(e)}")
        
        # Se algum arquivo consolidado não existe, criar
        if not all(consolidados.values()):
            print("Criando arquivos consolidados...")
            
            # Ler arquivos necessários
            def read_s3_csv(key):
                try:
                    obj = s3.get_object(Bucket=trusted_bucket, Key=key)
                    return pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))
                except Exception as e:
                    print(f"Erro ao ler {key}: {str(e)}")
                    return None

            # Consolidar benefícios se necessário
            if not consolidados['tabelao_beneficios.csv']:
                print("Consolidando benefícios...")
                dfs_beneficios = []
                
                # Bolsa Família
                df_bolsa = read_s3_csv('Arquivos_Tratados/programa_bolsafamilia_2024_1_tratado.csv')
                if df_bolsa is not None:
                    df_bolsa['Programa'] = 'BOLSA FAMILIA'
                    dfs_beneficios.append(df_bolsa)
                
                # BPC
                df_bpc = read_s3_csv('Arquivos_Tratados/BPC_Setembro_2024_tratado.csv')
                if df_bpc is not None:
                    df_bpc['Programa'] = 'BPC'
                    dfs_beneficios.append(df_bpc)
                
                # CadÚnico
                df_cad = read_s3_csv('Arquivos_Tratados/cadunico_familias_jul24_tratado.csv')
                if df_cad is not None:
                    df_cad['Programa'] = 'CADUNICO'
                    dfs_beneficios.append(df_cad)
                
                if dfs_beneficios:
                    df_beneficios = pd.concat(dfs_beneficios, ignore_index=True)
                    
                    # Salvar tabelão de benefícios
                    output_buffer = StringIO()
                    df_beneficios.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
                    s3.put_object(
                        Bucket=trusted_bucket,
                        Key='Arquivos_Tratados/Consolidados/tabelao_beneficios.csv',
                        Body=output_buffer.getvalue().encode('utf-8-sig')
                    )
                    print("Tabelão de benefícios criado com sucesso!")
            
            # Consolidar indicadores do ObservaSampa se necessário
            if not consolidados['tabelao_indicadores_observa.csv']:
                print("Consolidando indicadores do ObservaSampa...")
                df_obs = read_s3_csv('Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv')
                if df_obs is not None:
                    output_buffer = StringIO()
                    df_obs.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
                    s3.put_object(
                        Bucket=trusted_bucket,
                        Key='Arquivos_Tratados/Consolidados/tabelao_indicadores_observa.csv',
                        Body=output_buffer.getvalue().encode('utf-8-sig')
                    )
                    print("Tabelão de indicadores do ObservaSampa criado com sucesso!")
            
            # Consolidar indicadores do Mapa da Desigualdade se necessário
            if not consolidados['tabelao_indicadores_mapa.csv']:
                print("Consolidando indicadores do Mapa da Desigualdade...")
                df_mapa = read_s3_csv('Arquivos_Tratados/mapa_da_desigualdade_2024_dados_tratado.csv')
                if df_mapa is not None:
                    output_buffer = StringIO()
                    df_mapa.to_csv(output_buffer, index=False, encoding='utf-8-sig', sep=';')
                    s3.put_object(
                        Bucket=trusted_bucket,
                        Key='Arquivos_Tratados/Consolidados/tabelao_indicadores_mapa.csv',
                        Body=output_buffer.getvalue().encode('utf-8-sig')
                    )
                    print("Tabelão de indicadores do Mapa criado com sucesso!")
        
        return True
    except Exception as e:
        print(f"Erro ao consolidar dados: {str(e)}")
        return False

def process_files():
    """Processa os arquivos do bucket trusted e salva no bucket client"""
    try:
        # Obtém nomes dos buckets
        trusted_bucket, client_bucket = get_bucket_names()
        
        # Configuração do cliente S3
        s3 = boto3.client('s3')
        
        processed_files = []
        errors = []
        
        # Processa dados de extrema pobreza
        try:
            if process_extrema_pobreza(s3, trusted_bucket, client_bucket):
                processed_files.append('dados_pergunta_2_extrema_pobreza.csv')
        except Exception as e:
            errors.append(f"Erro ao processar extrema pobreza: {str(e)}")

        # Processa dados de transferência de renda
        try:
            if process_transferencia_renda(s3, trusted_bucket, client_bucket):
                processed_files.append('dados_pergunta_5_transferencia_renda.csv')
        except Exception as e:
            errors.append(f"Erro ao processar transferência de renda: {str(e)}")
            
        # Processa dados de educação
        try:
            if process_educacao(s3, trusted_bucket, client_bucket):
                processed_files.append('dados_pergunta_8_educacao.csv')
        except Exception as e:
            errors.append(f"Erro ao processar educação: {str(e)}")

        # Processa dados de habitação
        try:
            if process_habitacao(s3, trusted_bucket, client_bucket):
                processed_files.append('dados_pergunta_10_habitacao.csv')
        except Exception as e:
            errors.append(f"Erro ao processar habitação: {str(e)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processamento concluído',
                'processed_files': processed_files,
                'errors': errors
            })
        }
        
    except Exception as e:
        error_msg = f"Erro durante o processamento: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg
            })
        }

def lambda_handler(event, context):
    """
    Função handler da Lambda
    :param event: Evento que trigou a Lambda
    :param context: Contexto de execução da Lambda
    """
    try:
        # Obtém nomes dos buckets
        trusted_bucket, client_bucket = get_bucket_names()
        s3 = boto3.client('s3')
        
        # Lista os arquivos necessários e verifica quais estão disponíveis
        required_files = [
            'Arquivos_Tratados/ObservaSampaDadosAbertosIndicadoresCSV_tratado.csv',
            'Arquivos_Tratados/mapa_da_desigualdade_2024_dados_tratado.csv',
            'Arquivos_Tratados/cadunico_familias_jul24_tratado.csv',
            'Arquivos_Tratados/programa_bolsafamilia_2024_1_tratado.csv',
            'Arquivos_Tratados/BPC_Setembro_2024_tratado.csv'
        ]
        
        print("Verificando arquivos necessários:")
        available_files = []
        missing_files = []
        for file in required_files:
            try:
                s3.head_object(Bucket=trusted_bucket, Key=file)
                available_files.append(file)
                print(f"✓ {file} - Encontrado")
            except Exception:
                missing_files.append(file)
                print(f"✗ {file} - Não encontrado")
        
        if missing_files:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Arquivos necessários não encontrados',
                    'missing_files': missing_files,
                    'available_files': available_files
                }, ensure_ascii=False)
            }
        
        # Se todos os arquivos estão disponíveis, processa
        result = process_files()
        result['body'] = json.loads(result['body'])
        result['body']['available_files'] = available_files
        result['body'] = json.dumps(result['body'], ensure_ascii=False)
        
        return result
        
    except Exception as e:
        error_msg = f"Erro na execução da Lambda: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg
            }, ensure_ascii=False)
        }