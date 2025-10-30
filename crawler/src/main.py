import os
import re
import uuid
import requests
import unicodedata
from urllib.parse import urlparse, unquote

import utils.utils as utils
import utils.custom_logger as logger
from services.s3_service import S3Service

logger = logger.custom_logger(__name__)


def main():
    config()

    s3_service = S3Service()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(root_dir, '..', 'input')

    logger.info(f"Root directory: {root_dir}")
    logger.info(f"Input directory: {input_dir}")

    urls = utils.load_urls(os.path.join(input_dir, 'data.json'))
    logger.debug(f"Loaded URLs: {urls}")

    downloaded_files = download_urls(urls, os.path.join(root_dir, '..', 'temp'))
    logger.info(f"Downloaded files: {downloaded_files}")

    for file in downloaded_files:
        logger.info(f"Processing file: {file}")
        try:
            s3_url = s3_service.upload_file(file_path=file, key=os.path.basename(file))
            logger.info(f"Uploaded {file} to S3: {s3_url}")

            if s3_url:
                try:
                    if os.path.exists(file):
                        os.remove(file)
                        logger.info(f"Deleted local file: {file}")
                    else:
                        logger.warning(f"Local file not found for deletion: {file}")

                except OSError as e:
                    logger.error(f"Could not delete local file {file}: {e}")

        except Exception as e:
            logger.error(f"Failed to upload {file} to S3: {e}")


def config():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(root_dir, '..', 'input')
    temp_dir = os.path.join(root_dir, '..', 'temp')

    for path, name in ((input_dir, 'input'), (temp_dir, 'temp')):
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Ensured '{name}' directory exists at: {os.path.abspath(path)}")
    
        except OSError as e:
            logger.error(f"Could not create '{name}' directory at {path}: {e}")
            raise

def download_urls(urls: list, temp_dir: str) -> list:
    downloaded = []
    if not urls:
        logger.info("No URLs provided for download.")
        return downloaded

    for raw in urls:
        try:
            if not raw:
                continue
            url = raw.strip()
            if not url:
                continue

            path = request_url(url, temp_dir)
            if path:
                downloaded.append(path)
            else:
                logger.warning(f"Failed to download: {url}")

        except Exception as exc:
            logger.error(f"Error processing URL '{raw}': {exc}")

    return downloaded

def request_url(url: str, temp_dir: str) -> str:
    try:

        os.makedirs(temp_dir, exist_ok=True)
        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()

            cd = response.headers.get('content-disposition', '') or ''
            filename = None
            if cd:
                m = re.search(r"filename\*=([^']+)''(.+)", cd)
                if m:
                    filename = unquote(m.group(2))
                else:
                    m = re.search(r'filename="?([^\";]+)"?', cd)
                    if m:
                        filename = m.group(1)

            if not filename:
                path = urlparse(url).path
                filename = os.path.basename(path) or str(uuid.uuid4())

            filename = unquote(filename)
            filename = unicodedata.normalize('NFKD', filename)
            filename = ''.join(ch for ch in filename if not unicodedata.combining(ch))

            filename = filename.replace(' ', '_')
            filename = re.sub(r'[^\w\.-]', '_', filename)
            filename = re.sub(r'_+', '_', filename)
            filename = filename.strip('._-').lower()

            name_root, ext = os.path.splitext(filename)
            if not ext:
                ct = response.headers.get('content-type', '').split(';')[0].strip().lower()
                ct_map = {
                    'application/pdf': '.pdf',
                    'application/msword': '.doc',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'text/html': '.html',
                }
                ext = ct_map.get(ct, '.bin')
                filename = f"{name_root or str(uuid.uuid4())}{ext}"

            max_len = 200
            if len(filename) > max_len:
                root, ext = os.path.splitext(filename)
                filename = root[: max_len - len(ext)] + ext

            if not filename:
                filename = f"{str(uuid.uuid4())}{ext if ext else '.bin'}"

            dest_path = os.path.join(temp_dir, filename)
            base, extension = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = f"{base}_{counter}{extension}"
                counter += 1

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded {url} -> {os.path.abspath(dest_path)}")
            return os.path.abspath(dest_path)

    except requests.RequestException as e:
        logger.error(f"Error downloading URL {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error for URL {url}: {e}")
        return ""


if __name__ == "__main__":
    logger.info("Starting Process")
    main()
    logger.info("Process Finished")