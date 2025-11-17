import os
import pandas as pd
import numpy as np


def analisar_desigualdade_genero():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    path_mapa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_mapa.csv')
    path_observa = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_indicadores_observa.csv')
    path_output = os.path.join(base_dir, 'dados_pergunta_7_desigualdade_genero.csv')

    if not os.path.exists(path_mapa):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_mapa}")
    if not os.path.exists(path_observa):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_observa}")

    df_mapa = pd.read_csv(path_mapa, encoding='utf-8')
    df_observa = pd.read_csv(path_observa, encoding='utf-8')

    # Distritos da região da igreja
    distritos_igreja = [
        'BELA VISTA', 'BOM RETIRO', 'CAMBUCI', 'CONSOLACAO',
        'LIBERDADE', 'REPUBLICA', 'SANTA CECILIA', 'SE'
    ]

    # Filtrar dados do Mapa da Desigualdade para os distritos da região
    df_mapa_filtrado = df_mapa[df_mapa['Distrito'].isin(distritos_igreja)].copy()

    # Selecionar e renomear as coluna de violência
    if 'Violência contra a mulher (todas)' not in df_mapa_filtrado.columns:
        df_mapa_filtrado['Violência contra a mulher (todas)'] = np.nan

    df_violencia = df_mapa_filtrado[['Distrito', 'Violência contra a mulher (todas)']].copy()
    df_violencia = df_violencia.rename(columns={'Violência contra a mulher (todas)': 'Taxa_Violencia_Mulher'})
    df_violencia['Taxa_Violencia_Mulher'] = pd.to_numeric(df_violencia['Taxa_Violencia_Mulher'], errors='coerce')

    # Indicadores de alunos por gênero no ano de referência
    ano_ref = 2024

    df_fem = df_observa[
        (df_observa['Nome'] == 'ALUNOS DA REDE MUNICIPAL DE ENSINO DO SEXO FEMININO') &
        (df_observa['Distrito'].isin(distritos_igreja)) &
        (df_observa['Período'] == ano_ref)
    ].copy()

    df_masc = df_observa[
        (df_observa['Nome'] == 'ALUNOS DA REDE MUNICIPAL DE ENSINO DO SEXO MASCULINO') &
        (df_observa['Distrito'].isin(distritos_igreja)) &
        (df_observa['Período'] == ano_ref)
    ].copy()

    # Consolidar os dados de alunos
    df_alunos = pd.DataFrame()
    if not df_fem.empty or not df_masc.empty:
        if not df_fem.empty:
            df_fem_resumo = df_fem.groupby('Distrito')['Resultado'].sum().reset_index().rename(columns={'Resultado': 'Alunos_Feminino'})
        else:
            df_fem_resumo = pd.DataFrame({'Distrito': distritos_igreja, 'Alunos_Feminino': 0})

        if not df_masc.empty:
            df_masc_resumo = df_masc.groupby('Distrito')['Resultado'].sum().reset_index().rename(columns={'Resultado': 'Alunos_Masculino'})
        else:
            df_masc_resumo = pd.DataFrame({'Distrito': distritos_igreja, 'Alunos_Masculino': 0})

        df_alunos = df_fem_resumo.merge(df_masc_resumo, on='Distrito', how='outer').fillna(0)
        df_alunos['Alunos_Feminino'] = pd.to_numeric(df_alunos['Alunos_Feminino'], errors='coerce').fillna(0).astype(int)
        df_alunos['Alunos_Masculino'] = pd.to_numeric(df_alunos['Alunos_Masculino'], errors='coerce').fillna(0).astype(int)
        df_alunos['Total_Alunos'] = df_alunos['Alunos_Feminino'] + df_alunos['Alunos_Masculino']
        df_alunos['Perc_Feminino'] = np.where(df_alunos['Total_Alunos'] > 0, (df_alunos['Alunos_Feminino'] / df_alunos['Total_Alunos']) * 100, 0)
        df_alunos['Perc_Masculino'] = np.where(df_alunos['Total_Alunos'] > 0, (df_alunos['Alunos_Masculino'] / df_alunos['Total_Alunos']) * 100, 0)

    # Consolidar as análises
    if not df_alunos.empty:
        df_resultado = df_violencia.merge(df_alunos, on='Distrito', how='left')
    else:
        df_resultado = df_violencia.copy()
        df_resultado['Alunos_Feminino'] = 0
        df_resultado['Alunos_Masculino'] = 0
        df_resultado['Total_Alunos'] = 0
        df_resultado['Perc_Feminino'] = 0
        df_resultado['Perc_Masculino'] = 0

    # Arredondar e ordenar
    df_resultado['Taxa_Violencia_Mulher'] = df_resultado['Taxa_Violencia_Mulher'].round(2)
    df_resultado['Perc_Feminino'] = df_resultado['Perc_Feminino'].round(2)
    df_resultado['Perc_Masculino'] = df_resultado['Perc_Masculino'].round(2)
    df_resultado = df_resultado.sort_values('Taxa_Violencia_Mulher', ascending=False).reset_index(drop=True)

    # Identificar o distrito mais impactado (se houver dados)
    if not df_resultado.empty and df_resultado['Taxa_Violencia_Mulher'].notna().any():
        primeiro = df_resultado.iloc[0]
        distrito_mais_impactado = primeiro['Distrito']
        taxa_max = float(primeiro['Taxa_Violencia_Mulher']) if not np.isnan(primeiro['Taxa_Violencia_Mulher']) else None
    else:
        distrito_mais_impactado = None
        taxa_max = None

    resposta = {
        'genero_mais_afetado': 'FEMININO',
        'distrito_mais_impactado': distrito_mais_impactado,
        'taxa_violencia_max': taxa_max
    }

    return df_resultado, path_output, resposta


if __name__ == "__main__":
    try:
        df_resultado, output_path, resposta = analisar_desigualdade_genero()

        # salvar CSV resumo (comportamento padrão do projeto)
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')

        # saída mínima e estruturada (útil para integração)
        if resposta['distrito_mais_impactado'] is not None:
            print(f"{resposta['genero_mais_afetado']} - {resposta['distrito_mais_impactado']} - {resposta['taxa_violencia_max']:.2f}")
        else:
            print(resposta['genero_mais_afetado'])

    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()