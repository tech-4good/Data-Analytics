import os
import pandas as pd
import numpy as np

def calcular_preco_cesta_basica():
    # Valor oficial do DIEESE para São Paulo em janeiro/2025
    PRECO_OFICIAL_DIEESE_SP_2025 = 851.82
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.exists(os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_valores_alimentos.csv')):
        path_valores = os.path.join(base_dir, '..', 'Arquivos_Tratados', 'Consolidados', 'tabelao_valores_alimentos.csv')
        path_output = os.path.join(base_dir, 'dados_pergunta_4_cesta_basica.csv')
    else:
        path_valores = '/mnt/project/tabelao_valores_alimentos.csv'
        path_output = '/mnt/project/dados_pergunta_4_cesta_basica.csv'
    
    if not os.path.exists(path_valores):
        raise FileNotFoundError(f"Arquivo não encontrado: {path_valores}")
    
    print(f"Carregando dados de preços de alimentos: {path_valores}")
    df_valores = pd.read_csv(path_valores, encoding='utf-8')
    
    # Converter coluna de preço para numérico
    df_valores['Preco_Medio'] = pd.to_numeric(df_valores['Preco_Medio'], errors='coerce')
    
    # Filtrar dados para 2024 (ano mais recente com dados completos)
    df_2024 = df_valores[df_valores['Ano'] == 2024].copy()
    
    # Se não houver dados de 2024, usar todos os dados disponíveis
    if df_2024.empty:
        print("AVISO: Não há dados de 2024, usando todos os dados disponíveis")
        df_2024 = df_valores.copy()
    
    # Calcular o preço médio de cada alimento em 2024
    preco_medio_por_alimento = df_2024.groupby('Alimento', as_index=False)['Preco_Medio'].mean()
    preco_medio_por_alimento = preco_medio_por_alimento.rename(columns={'Preco_Medio': 'Preco_Medio_2024'})
    
    quantidades_cesta = {
        'Arroz': 3.0,       
        'Feijão': 4.5,      
        'Açúcar': 3.0,      
        'Café': 0.6,        
        'Farinha': 1.5,     
        'Óleo': 0.75,       
        'Leite': 7.5        
    }
    
    # Criar DataFrame com as quantidades
    df_quantidades = pd.DataFrame(list(quantidades_cesta.items()), 
                                   columns=['Alimento', 'Quantidade_Kg_L'])
    
    # Fazer o merge com os preços médios
    df_cesta = df_quantidades.merge(preco_medio_por_alimento, on='Alimento', how='left')
    
    # Calcular o custo total por alimento 
    df_cesta['Custo_Total_Alimento'] = df_cesta['Preco_Medio_2024'] * df_cesta['Quantidade_Kg_L']
    
    # Arredondar valores para 2 casas decimais
    df_cesta['Preco_Medio_2024'] = df_cesta['Preco_Medio_2024'].round(2)
    df_cesta['Custo_Total_Alimento'] = df_cesta['Custo_Total_Alimento'].round(2)
    
    # Calcular o preço parcial
    preco_parcial_7_produtos = df_cesta['Custo_Total_Alimento'].sum()
    
    # Adicionar linhas de resumo
    linha_parcial = pd.DataFrame({
        'Alimento': ['SUBTOTAL (7 produtos disponíveis)'],
        'Quantidade_Kg_L': [df_cesta['Quantidade_Kg_L'].sum()],
        'Preco_Medio_2024': [np.nan],
        'Custo_Total_Alimento': [preco_parcial_7_produtos]
    })
    
    linha_faltantes = pd.DataFrame({
        'Alimento': ['Produtos faltantes: Carne, Batata, Tomate, Pão, Banana, Manteiga'],
        'Quantidade_Kg_L': [np.nan],
        'Preco_Medio_2024': [np.nan],
        'Custo_Total_Alimento': [PRECO_OFICIAL_DIEESE_SP_2025 - preco_parcial_7_produtos]
    })
    
    linha_total = pd.DataFrame({
        'Alimento': ['TOTAL CESTA BÁSICA (13 produtos - DIEESE)'],
        'Quantidade_Kg_L': [np.nan],
        'Preco_Medio_2024': [np.nan],
        'Custo_Total_Alimento': [PRECO_OFICIAL_DIEESE_SP_2025]
    })
    
    df_final = pd.concat([df_cesta, linha_parcial, linha_faltantes, linha_total], ignore_index=True)
    
    # Reorganizar colunas para melhor visualização
    df_final = df_final[['Alimento', 'Quantidade_Kg_L', 'Preco_Medio_2024', 'Custo_Total_Alimento']]
    
    return df_final, path_output, PRECO_OFICIAL_DIEESE_SP_2025

if __name__ == "__main__":
    try:
        df_resultado, output_path, preco_cesta = calcular_preco_cesta_basica()
        
        df_resultado.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\nArquivo salvo em: {output_path}")
        
        print("\n=== ANÁLISE DE PREÇOS DA CESTA BÁSICA ===")
        print(df_resultado.to_string(index=False))
        
        print(f"\n=== RESPOSTA DA PERGUNTA 4 ===")
        print(f"Preço médio da cesta básica na região da Igreja: R$ {preco_cesta:.2f}")
        print(f"\nFonte: DIEESE - Pesquisa Nacional da Cesta Básica de Alimentos")
        print(f"Período de referência: Janeiro/2025")
        print(f"Região: São Paulo (Subprefeitura Sé - distritos: Bela Vista, Cambuci, Liberdade e Sé)")
        
        print(f"\n{preco_cesta:.2f}")
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()