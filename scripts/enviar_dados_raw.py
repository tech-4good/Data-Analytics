import boto3
import os
from pathlib import Path

def get_bucket_name():
    """Obtém o nome do bucket raw do arquivo de estado do Terraform"""
    try:
        s3 = boto3.client('s3')
        response = s3.list_buckets()
        # Procura o bucket que começa com 'analise-dados-raw-'
        for bucket in response['Buckets']:
            if bucket['Name'].startswith('analise-dados-raw-'):
                return bucket['Name']
        raise Exception("Bucket raw não encontrado")
    except Exception as e:
        print(f"Erro ao obter nome do bucket: {str(e)}")
        raise

def upload_files_to_s3():
    """Envia todos os arquivos do diretório Arquivos_Brutos para o bucket S3"""
    try:
        # Obtém o nome do bucket
        bucket_name = get_bucket_name()
        
        # Configuração do cliente S3
        s3 = boto3.client('s3')
        
        # Caminho para o diretório Arquivos_Brutos
        script_dir = Path(__file__).parent
        base_dir = script_dir.parent
        brutos_dir = base_dir / 'Arquivos_Brutos'
        
        # Verifica se o diretório existe
        if not brutos_dir.exists():
            raise Exception(f"Diretório não encontrado: {brutos_dir}")
        
        # Upload de cada arquivo no diretório
        for file_path in brutos_dir.glob('*'):
            if file_path.is_file():
                print(f"Enviando arquivo: {file_path.name}")
                try:
                    s3.upload_file(
                        str(file_path),
                        bucket_name,
                        file_path.name
                    )
                    print(f"Arquivo enviado com sucesso: {file_path.name}")
                except Exception as e:
                    print(f"Erro ao enviar arquivo {file_path.name}: {str(e)}")
        
        print("Processo de upload concluído!")
        
    except Exception as e:
        print(f"Erro durante o processo de upload: {str(e)}")
        raise

if __name__ == "__main__":
    upload_files_to_s3()
