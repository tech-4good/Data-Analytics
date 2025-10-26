import os
import pandas as pd
import numpy as np

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

if __name__ == "__main__":
    try:
        df_resultado, output_path = preparar_dados_educacao()
        
        # Salvar o CSV de resumo por distrito
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')
        
        # Resposta da pergunta 8: total de matrículas na rede municipal
        total_matriculas = int(df_resultado['Total_Matriculas'].replace('NAO INFORMADO', 0).astype(float).sum()) if 'Total_Matriculas' in df_resultado.columns else 0
        print(total_matriculas)
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()