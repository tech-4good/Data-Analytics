import pandas as pd
import re

def clean_csv(input_path, output_path):
    df = pd.read_csv(input_path, sep=';', dtype=str)  # lê tudo como string

    def clean_cell(cell):
        if pd.isnull(cell):
            return cell
        cell = cell.upper()
        cell = re.sub(r'[^A-ZÀ-ÚÂÊÎÔÛÇ0-9 ]', '', cell)
        cell = re.sub(r'\s+', ' ', cell)  
        cell = cell.strip() 
        return cell

    # Aplica a função a todo o DataFrame
    df = df.applymap(clean_cell)
    df.to_csv(output_path, index=False)

#primeiro csv
clean_csv('./Arquivos_Brutos/ObservaSampaDadosAbertosIndicadoresCSV.csv','./Arquivos_tratados/OSDAI_tratado.csv')
#segundo csv
clean_csv('./Arquivos_Brutos/ObservaSampaDadosAbertosIndicadoresODSCSV.csv','./Arquivos_tratados/OSDAI_ODS_tratado.csv')
#terceiro csv
clean_csv('./Arquivos_Brutos/ObservaSampaDadosAbertosVariaveisCSV.csv','./Arquivos_tratados/OSDAV_tratado.csv')
