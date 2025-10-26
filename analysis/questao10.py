import os
import pandas as pd
import numpy as np

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
    
    # Procesasndo os dados do ObservaSampa
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

if __name__ == "__main__":
    try:
        df_resultado, output_path = preparar_dados_habitacao()
        
        # Salvar o CSV de resumo por distrito
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')
        
        # Resposta da pergunta 10: total de domicílios em favelas
        total_favelas = int(df_resultado['Total_Domicilios_Favelas'].sum()) if 'Total_Domicilios_Favelas' in df_resultado.columns else 0
        print(total_favelas)
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()