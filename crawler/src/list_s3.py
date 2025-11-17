import os
from dotenv import load_dotenv
from services.s3_service import S3Service
import utils.custom_logger as custom_logger

logger = custom_logger.custom_logger(__name__)


def main():
    load_dotenv()
    s3 = S3Service()
    client = s3.client
    bucket = s3.bucket
    paginator = client.get_paginator('list_objects_v2')
    logger.info(f"Listing objects in bucket: {bucket}")
    count = 0
    try:
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get('Contents', []):
                print(obj['Key'])
                count += 1
    except Exception as e:
        logger.error(f"Failed to list objects: {e}")
    logger.info(f"Total objects: {count}")


if __name__ == '__main__':
    main()
