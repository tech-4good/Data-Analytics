import os
import io
from dotenv import load_dotenv
import tempfile
import logging
from typing import List

import boto3
from botocore.exceptions import ClientError

from services.s3_service import S3Service
import utils.custom_logger as custom_logger

logger = custom_logger.custom_logger(__name__)


def list_bucket_objects(s3_client, bucket: str, prefix: str = '') -> List[str]:
    paginator = s3_client.get_paginator('list_objects_v2')
    keys = []
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                keys.append(obj['Key'])
    except ClientError as e:
        logger.error(f"Error listing objects in bucket {bucket}: {e}")
        raise
    return keys


def download_object(s3_client, bucket: str, key: str, dest_path: str) -> str:
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3_client.download_file(Bucket=bucket, Key=key, Filename=dest_path)
        logger.info(f"Downloaded s3://{bucket}/{key} -> {dest_path}")
        return dest_path
    except ClientError as e:
        logger.error(f"Failed to download s3://{bucket}/{key}: {e}")
        raise


def extract_text_from_pdf(pdf_path: str) -> str:
    text_parts = []

    # Tentativa 1 → PDFMiner (extrai texto “selecionável”)
    try:
        from pdfminer.high_level import extract_text
        txt = extract_text(pdf_path) or ''
        text_parts.append(txt)
    except Exception as e:
        logger.warning(f"pdfminer extraction failed for {pdf_path}: {e}")

    # Tentativa 2 → OCR com Tesseract (extrai texto de imagens, scans, infográficos)
    try:
        from pdf2image import convert_from_path
        import pytesseract

        # Define Tesseract manualmente (sem depender do PATH do Windows)
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Users\b.santana.reginato\Downloads\pessoal\executaveis\tesseract\tesseract.exe"
        )

        # Caminho do Poppler também fixo
        images = convert_from_path(
            pdf_path,
            poppler_path=r"C:\Users\b.santana.reginato\Downloads\pessoal\executaveis\poppler-25.11.0\Library\bin"
        )

        for img in images:
            try:
                ocr_text = pytesseract.image_to_string(img, lang='por+eng')
                if ocr_text and ocr_text.strip():
                    text_parts.append(ocr_text)
            except Exception as e:
                logger.debug(f"OCR failed for a page of {pdf_path}: {e}")

    except Exception as e:
        logger.info(f"Skipping OCR for {pdf_path} (missing dependencies or failure): {e}")

    # Retorna apenas trechos não vazios
    return "\n\n".join([p for p in text_parts if p])


def save_text(text: str, dest_txt: str) -> str:
    os.makedirs(os.path.dirname(dest_txt), exist_ok=True)
    with open(dest_txt, 'w', encoding='utf-8') as f:
        f.write(text)
    logger.info(f"Saved text to {dest_txt}")
    return dest_txt


def main():
    load_dotenv()
    s3_src = S3Service()  # usa AWS_S3_BUCKET por padrão
    env_trusted = os.getenv('AWS_S3_BUCKET_TRUSTED')
    if not env_trusted:
        raise ValueError('AWS_S3_BUCKET_TRUSTED not set in environment')

    s3_client = s3_src.client
    trusted_svc = S3Service(bucket_name=env_trusted)

    # Lista arquivos do bucket bronze
    keys = list_bucket_objects(s3_client, s3_src.bucket)
    if not keys:
        logger.info('No objects found in source bucket')
        return

    # Diretório temp
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp', 'trusted')
    os.makedirs(tmpdir, exist_ok=True)

    for key in keys:
        if not key.lower().endswith('.pdf'):
            logger.debug(f"Skipping non-pdf key: {key}")
            continue

        local_pdf = os.path.join(tmpdir, os.path.basename(key))

        try:
            # Download
            download_object(s3_client, s3_src.bucket, key, local_pdf)

            # Extrair texto
            text = extract_text_from_pdf(local_pdf)
            if not text.strip():
                logger.warning(f"No text extracted from {local_pdf}")

            # Salvar .txt
            txt_name = os.path.splitext(os.path.basename(local_pdf))[0] + '.txt'
            local_txt = os.path.join(tmpdir, txt_name)
            save_text(text, local_txt)

            # Upload para bucket trusted
            trusted_svc.bucket = env_trusted
            s3_url = trusted_svc.upload_file(local_txt, key=txt_name)
            logger.info(f"Uploaded txt to trusted bucket: {s3_url}")

        except Exception as e:
            logger.error(f"Failed processing {key}: {e}")


if __name__ == '__main__':
    logger.info('Starting main_trusted')
    main()
    logger.info('Finished main_trusted')
