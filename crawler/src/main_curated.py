import os
import re
import logging
from typing import List, Dict

import spacy
from dotenv import load_dotenv
import pandas as pd
import boto3
from botocore.exceptions import ClientError

from services.s3_service import S3Service
import utils.custom_logger as custom_logger

logger = custom_logger.custom_logger(__name__)

try:
    nlp = spacy.load("pt_core_news_md")
    logger.info("spaCy model pt_core_news_md loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load spaCy model: {e}")
    raise


def list_txt_files(s3_client, bucket: str) -> List[str]:
    paginator = s3_client.get_paginator("list_objects_v2")
    keys = []
    try:
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.lower().endswith(".txt"):
                    keys.append(key)
    except ClientError as e:
        logger.error(f"Failed to list objects in {bucket}: {e}")
        raise
    return keys


def download_txt(s3_client, bucket: str, key: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(key))
    try:
        s3_client.download_file(Bucket=bucket, Key=key, Filename=dest_path)
        logger.info(f"Downloaded {key} to {dest_path}")
        return dest_path
    except ClientError as e:
        logger.error(f"Failed to download {key}: {e}")
        raise


def detect_location(text: str) -> Dict[str, str]:
    country = "Brazil"  
    state = ""
    city = ""
    region = ""
    neighborhood = ""
    municipality = ""

    states_names = [
        "São Paulo", "SP", "Rio de Janeiro", "RJ", "Bahia", "BA",
        "Minas Gerais", "MG", "Paraná", "PR"
    ]
    if any(re.search(rf"\b{st}\b", text, re.IGNORECASE) for st in states_names):
        state = "São Paulo"  

    zones = {
        "zona leste": ["leste", "zl"],
        "zona oeste": ["oeste", "zo"],
        "zona norte": ["norte", "zn"],
        "zona sul": ["sul", "zs"],
        "centro": ["centro"]
    }

    for zone_name, zone_aliases in zones.items():
        for alias in zone_aliases:
            if re.search(rf"\b{alias}\b", text, re.IGNORECASE):
                region = zone_name
                city = "São Paulo"
                break

    municipalities_list = [
        "Guarulhos", "Osasco", "Barueri", "Carapicuíba", "Cotia", "Itaquaquecetuba",
        "Santo André", "São Bernardo", "São Caetano", "Mauá", "Diadema",
        "Suzano", "Mogi das Cruzes", "Taboão da Serra", "Embu", "Ribeirão Pires"
    ]

    for m in municipalities_list:
        if re.search(rf"\b{m}\b", text, re.IGNORECASE):
            municipality = m
            state = "São Paulo"
            break

    bairros_sp = [
        "Pinheiros", "Moema", "Itaquera", "Tatuapé", "Sapopemba", "Vila Mariana",
        "Casa Verde", "Santana", "Sé", "Liberdade", "Butantã"
    ]
    for b in bairros_sp:
        if re.search(rf"\b{b}\b", text, re.IGNORECASE):
            neighborhood = b
            city = "São Paulo"
            state = "São Paulo"
            break

    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ("LOC", "GPE"):
            if state == "" and "São Paulo" in ent.text:
                state = "São Paulo"
            if city == "" and ent.text.lower() == "são paulo":
                city = "São Paulo"

    return {
        "country": country,
        "state": state,
        "city": city,
        "region": region,
        "municipality": municipality,
        "neighborhood": neighborhood
    }


def extract_social_indicators(text: str, source_file: str) -> List[pd.DataFrame]:
    frames = []
    rows = []

    patterns = [
        (r"(taxa[s]? de pobreza|pobreza)[:\s]*([0-9]{1,2}[\.,]?[0-9]?%?)", "pobreza"),
        (r"(gini|índice gini|índice de gini)[:\s]*([0-9]\.[0-9]+)", "desigualdade"),
        (r"(insegurança alimentar (grave|moderada|leve))[:\s]*([0-9]{1,2}[\.,]?[0-9]?%?)",
         "inseguranca_alimentar"),
        (r"(fome)[:\s]*([0-9]{1,3}[\.,]?[0-9]* (mil|milhares|pessoas|famílias|familias)|"
         r"[0-9]{1,2}[\.,]?[0-9]?%?)", "fome"),
        (r"(renda média|salário médio|salario medio|rendimento médio)[:\s]*([0-9\.,]+)",
         "renda"),
        (r"([0-9\.,]+)\s*(familias|famílias|pessoas|habitantes)", "populacao"),
    ]

    for pat, category in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            metric = m.group(1)
            value = m.group(2)
            context = text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
            loc = detect_location(context)

            unit = "%"
            if re.search(r"famil", value, re.IGNORECASE):
                unit = "familias"
            elif re.search(r"pessoas|habitantes", value, re.IGNORECASE):
                unit = "pessoas"

            rows.append({
                "metric_name": metric.strip(),
                "value": value.strip(),
                "unit": unit,
                "context": context.strip(),
                "category": category,
                "source_file": source_file,
                "country": loc["country"],
                "state": loc["state"],
                "city": loc["city"],
                "region": loc["region"],
                "municipality": loc["municipality"],
                "neighborhood": loc["neighborhood"]
            })

    if rows:
        frames.append(pd.DataFrame(rows))
    else:
        frames.append(pd.DataFrame([{
            "source_file": source_file,
            "message": "no social indicators detected",
            "line_count": text.count("\n") + 1
        }]))

    return frames


def save_csv(df: pd.DataFrame, filename: str) -> str:
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename, index=False, encoding="utf-8")
    logger.info(f"Saved CSV {filename}")
    return filename


def upload_csv_to_s3(s3_client, path: str, bucket: str, key: str) -> str:
    try:
        s3_client.upload_file(Filename=path, Bucket=bucket, Key=key)
        region = s3_client.meta.region_name
        if region != "us-east-1":
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    except ClientError as e:
        logger.error(f"Failed to upload {path}: {e}")
        raise


def main():
    load_dotenv()

    src_bucket = os.getenv("AWS_S3_BUCKET_TRUSTED")
    curated_bucket = os.getenv("AWS_S3_BUCKET_CURATED")

    if not src_bucket or not curated_bucket:
        raise ValueError("AWS_S3_BUCKET_TRUSTED and AWS_S3_BUCKET_CURATED must be set")

    s3 = S3Service(bucket_name=src_bucket)
    client = s3.client

    keys = list_txt_files(client, src_bucket)
    logger.info(f"Found {len(keys)} .txt files in trusted bucket")

    tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp", "curated")
    os.makedirs(tmpdir, exist_ok=True)

    for key in keys:
        try:
            local_txt = download_txt(client, src_bucket, key, tmpdir)

            with open(local_txt, "r", encoding="utf-8") as f:
                text = f.read()

            frames = extract_social_indicators(text, os.path.basename(local_txt))

            part = 1
            for df in frames:
                base = os.path.splitext(os.path.basename(local_txt))[0]
                csv_name = f"{base}-part{part}.csv"
                local_csv = os.path.join(tmpdir, csv_name)

                save_csv(df, local_csv)
                upload_csv_to_s3(client, local_csv, curated_bucket, csv_name)

                part += 1

        except Exception as e:
            logger.error(f"Failed processing {key}: {e}")


if __name__ == "__main__":
    logger.info("Starting main_curated")
    main()
    logger.info("Finished main_curated")
