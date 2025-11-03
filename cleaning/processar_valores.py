import pandas as pd
import os

def clean_cell(value):
    if pd.isna(value):
        return 'NAO INFORMADO'
    
    value_str = str(value).strip()
    # Remove espaços múltiplos
    value_str = ' '.join(value_str.split())
    # Converte para maiúsculas
    value_str = value_str.upper()
    return value_str

def extrair_nome_alimento(caminho_arquivo):
    # Pegar apenas o nome do arquivo sem extensão
    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    
    # Dicionário de mapeamento para nomes corretos
    mapeamento = {
        'acucar': 'Açúcar',
        'arroz': 'Arroz',
        'cafe': 'Café',
        'farinha': 'Farinha',
        'feijao': 'Feijão',
        'leite': 'Leite',
        'oleo': 'Óleo'
    }
    
    # Retorna o nome mapeado ou o nome do arquivo em título
    return mapeamento.get(nome_base.lower(), nome_base.title())

def processar_arquivo_alimento(caminho_arquivo):
    try:
        print(f"Processando: {os.path.basename(caminho_arquivo)}")
        
        # Extrair nome do alimento
        nome_alimento = extrair_nome_alimento(caminho_arquivo)
        
        # Ler arquivo pulando as 2 primeiras linhas
        df = pd.read_excel(caminho_arquivo, header=None, skiprows=2)
        
        # Verificar se o arquivo tem pelo menos 2 colunas
        if df.shape[1] < 2:
            print(f"Arquivo com estrutura inadequada (menos de 2 colunas)")
            return None
        
        # Renomear colunas
        df.columns = ['data', 'preco']
        
        # Remover linhas com valores nulos na data ou preço
        df = df.dropna(subset=['data', 'preco'])
        
        if len(df) == 0:
            print(f"Nenhum dado válido encontrado")
            return None
        
        # Processar coluna de data
        df['data'] = df['data'].astype(str).str.strip()
        
        # Separar mês e ano
        df[['data_mes', 'data_ano']] = df['data'].str.split('-', expand=True)
        
        # Converter para inteiros
        df['data_mes'] = pd.to_numeric(df['data_mes'], errors='coerce').astype('Int64')
        df['data_ano'] = pd.to_numeric(df['data_ano'], errors='coerce').astype('Int64')
        
        # Converter preço para float
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce')
        
        # Remover linhas com valores inválidos após conversão
        df = df.dropna(subset=['data_mes', 'data_ano', 'preco'])
        
        # Adicionar coluna com nome do alimento
        df['nome'] = nome_alimento
        
        # Adicionar coluna com nome do mês por extenso em português
        meses = {
            1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL',
            5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
            9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
        }
        df['mes_nome'] = df['data_mes'].map(meses)
        
        # Selecionar e reordenar colunas finais
        df = df[['nome', 'preco', 'data_mes', 'mes_nome', 'data_ano']]
        
        # Ordenar por ano e mês
        df = df.sort_values(['data_ano', 'data_mes']).reset_index(drop=True)
        
        print(f"Processado: {len(df)} registros de {nome_alimento}")
        print(f"Período: {df['data_mes'].min():02d}/{df['data_ano'].min()} a {df['data_mes'].max():02d}/{df['data_ano'].max()}")
        
        return df
        
    except Exception as e:
        print(f"Erro ao processar {os.path.basename(caminho_arquivo)}: {e}")
        import traceback
        traceback.print_exc()
        return None

def processar_todos_alimentos():
    print("Procurando os arquivos dos valores dos alimentos")
    
    # Obter diretórios
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    base_dir = os.path.dirname(script_dir)
    
    # Caminhos
    input_folder = os.path.join(base_dir, 'Arquivos_Brutos', 'valores_alimentos')
    output_folder = os.path.join(base_dir, 'Arquivos_Tratados')
    
    # Verificar se pasta de entrada existe
    if not os.path.exists(input_folder):
        print(f"Erro: Pasta não encontrada: {input_folder}")
        return
    
    # Criar pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)
    
    # Listar todos os arquivos .xls
    arquivos_xls = [f for f in os.listdir(input_folder) if f.endswith('.xls')]
    
    if not arquivos_xls:
        print(f"Erro: Nenhum arquivo .xls encontrado em {input_folder}")
        return
    
    print(f"Arquivos encontrados: {len(arquivos_xls)}\n")
    print("Processando arquivos")
    
    # Processar cada arquivo
    dataframes = []
    arquivos_sucesso = []
    arquivos_erro = []
    
    for arquivo in sorted(arquivos_xls):
        caminho_completo = os.path.join(input_folder, arquivo)
        
        df = processar_arquivo_alimento(caminho_completo)
        
        if df is not None and len(df) > 0:
            dataframes.append(df)
            arquivos_sucesso.append(arquivo)
        else:
            arquivos_erro.append(arquivo)
            
    # Consolidar todos os DataFrames
    if not dataframes:
        print("Erro: Nenhum dado foi processado com sucesso")
        return
    
    print("Consolidando os dados:")
    
    df_consolidado = pd.concat(dataframes, ignore_index=True)
    
    # Ordenar por alimento, ano e mês
    df_consolidado = df_consolidado.sort_values(['nome', 'data_ano', 'data_mes']).reset_index(drop=True)
    
    # Salvar CSV consolidado
    output_csv = os.path.join(output_folder, 'valores_alimentos_consolidado.csv')
    df_consolidado.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print(f"Arquivo consolidado gerado com sucesso!")
    print(f"Arquivo: valores_alimentos_consolidado.csv")
    print(f"Total de registros: {len(df_consolidado):,}")
    print(f"Alimentos processados: {df_consolidado['nome'].nunique()}")
    print(f"Período: {df_consolidado['data_mes'].min():02d}/{df_consolidado['data_ano'].min()} a {df_consolidado['data_mes'].max():02d}/{df_consolidado['data_ano'].max()}")

def main():
    try:
        processar_todos_alimentos()
    except Exception as e:
        print(f"Erro geral no processamento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()