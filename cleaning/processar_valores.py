import pandas as pd
import os
import unicodedata

def clean_text(text):
    if pd.isna(text):
        return text
    
    text = str(text).strip()
    
    # Remove os acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Converte o texto para maiúscula
    text = text.upper()
    
    return text

def extrair_nome_alimento(caminho_arquivo):
    try:
        # Lê a segunda linha do arquivo que tem o nome do alimento
        df_header = pd.read_excel(caminho_arquivo, header=None, nrows=2)
        nome_alimento = str(df_header.iloc[1, 1]).strip()
        
        # Se conseguir ler o nome do arquivo, retorna ele limpo
        if nome_alimento and nome_alimento != 'nan':
            return clean_text(nome_alimento)
    except Exception:
        pass

    # Usa o nome do arquivo com mapeamento
    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    
    # Dicionário de mapeamento para os nomes corretos
    mapeamento = {
        'acucar': 'ACUCAR',
        'arroz': 'ARROZ',
        'cafe': 'CAFE',
        'farinha': 'FARINHA',
        'feijao': 'FEIJAO',
        'leite': 'LEITE',
        'oleo': 'OLEO'
    }
    
    # Retorna o nome mapeado ou o nome do arquivo limpo
    nome_limpo = clean_text(nome_base)
    return mapeamento.get(nome_base.lower(), nome_limpo)

def processar_arquivo_alimento(caminho_arquivo):
    try:
        print(f"Processando: {os.path.basename(caminho_arquivo)}")
        
        # Extrair o nome do alimento
        nome_alimento = extrair_nome_alimento(caminho_arquivo)
        
        # Lê o arquivo pulando as 2 primeiras linhas
        df = pd.read_excel(caminho_arquivo, header=None, skiprows=2)
        
        # Verifica se o arquivo tem pelo menos duas colunas
        if df.shape[1] < 2:
            print(f"Arquivo com estrutura inadequada (menos de 2 colunas)")
            return None
        
        # Renomeia as colunas
        df.columns = ['data', 'preco']
        
        # Remove as linhas com valores nulos na data ou preço
        df = df.dropna(subset=['data', 'preco'])
        
        if len(df) == 0:
            print(f"Nenhum dado válido encontrado")
            return None
        
        # Processa a coluna de data
        df['data'] = df['data'].astype(str).str.strip()
        
        # Separa mês e ano
        df[['data_mes', 'data_ano']] = df['data'].str.split('-', expand=True)
        
        # Converte mês e ano para inteiros
        df['data_mes'] = pd.to_numeric(df['data_mes'], errors='coerce').astype('Int64')
        df['data_ano'] = pd.to_numeric(df['data_ano'], errors='coerce').astype('Int64')

        # Converte preço para float
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce')
        
        # Remove linhas com valores inválidos após conversão
        df = df.dropna(subset=['data_mes', 'data_ano', 'preco'])
        
        # Adiciona coluna com nome do alimento (já padronizado)
        df['nome'] = nome_alimento
        
        # Adiciona coluna com nome do mês por extenso (em maiúsculas sem acentos)
        meses = {
            1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARCO', 4: 'ABRIL',
            5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
            9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
        }
        df['mes_nome'] = df['data_mes'].map(meses)
        
        # Seleciona e reordena colunas finais
        df = df[['nome', 'preco', 'data_mes', 'mes_nome', 'data_ano']]
        
        # Ordena por ano e mês
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
    print("Procurando os arquivos de valores dos alimentos")
    
    # Obtém diretórios
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    
    # Caminhos
    input_folder = os.path.join(base_dir, 'Arquivos_Brutos', 'valores_alimentos')
    output_folder = os.path.join(base_dir, 'Arquivos_Tratados')
    
    # Verifica se pasta de entrada existe
    if not os.path.exists(input_folder):
        print(f"Erro: Pasta não encontrada: {input_folder}")
        return
    
    # Cria pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)
    
    # Lista todos os arquivos .xls
    arquivos_xls = [f for f in os.listdir(input_folder) if f.endswith('.xls')]
    
    if not arquivos_xls:
        print(f"Erro: Nenhum arquivo .xls encontrado em {input_folder}")
        return
    
    print(f"Arquivos encontrados: {len(arquivos_xls)}\n")
    print("Processando arquivos")
    
    # Processa cada arquivo
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

    # Consolida todos os DataFrames
    if not dataframes:
        print("Erro: Nenhum dado foi processado com sucesso")
        return
    
    print("\nConsolidando os dados:")
    
    df_consolidado = pd.concat(dataframes, ignore_index=True)

    # Ordena por alimento, ano e mês
    df_consolidado = df_consolidado.sort_values(['nome', 'data_ano', 'data_mes']).reset_index(drop=True)
    
    # Salva CSV consolidado
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