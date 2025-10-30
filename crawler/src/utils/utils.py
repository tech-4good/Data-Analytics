import os
import re
import json
import utils.custom_logger as custom_logger

logger = custom_logger.custom_logger(__name__)

def load_urls(file_path):
    if not os.path.exists(file_path):
        logger.error(f"The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, 'r') as file:
        data = file.read()
    
    try:
        data_json = json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {file_path}: {e}")
        raise

    logger.info(f"Successfully loaded data from {file_path}")

    return data_json.get("urls", [])