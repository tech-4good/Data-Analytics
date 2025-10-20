import pandas as pd
import re
import unicodedata
import os

def clean_csv(input_path, output_path):
    df = pd.read_csv(input_path, sep=';', dtype=str)  # lê tudo como string

    def clean_cell(cell):
        if pd.isnull(cell):
            return cell
        
        # Converter para maiúsculas
        cell = cell.upper()
        
        # REMOVER ACENTUAÇÕES
        cell = unicodedata.normalize('NFD', cell)
        cell = ''.join(c for c in cell if unicodedata.category(c) != 'Mn')
        
        # Remover caracteres especiais
        cell = re.sub(r'[^A-Z0-9 ]', '', cell)
        
        # Normalizar espaços
        cell = re.sub(r'\s+', ' ', cell)  
        cell = cell.strip() 
        
        return cell

    # Aplica a função a todo o DataFrame
    df = df.map(clean_cell)  # Mudança: applymap → map
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

# Obter diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)

# Primeiro csv
clean_csv(
    os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosIndicadoresCSV.csv'),
    os.path.join(base_dir, 'Arquivos_Tratados', 'OSDAI_tratado.csv')
)

# Segundo csv
clean_csv(
    os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosIndicadoresODSCSV.csv'),
    os.path.join(base_dir, 'Arquivos_Tratados', 'OSDAI_ODS_tratado.csv')
)

# Terceiro csv
clean_csv(
    os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosVariaveisCSV.csv'),
    os.path.join(base_dir, 'Arquivos_Tratados', 'OSDAV_tratado.csv')
)