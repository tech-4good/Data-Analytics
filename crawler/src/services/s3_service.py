import os
import boto3
import logging
from dotenv import load_dotenv
from typing import Optional, Dict
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, bucket_name: Optional[str] = None, region_name: Optional[str] = None):
        load_dotenv()

        self.bucket = bucket_name or os.getenv("AWS_S3_BUCKET")
        region = region_name or os.getenv("AWS_REGION")

        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.getenv("AWS_SESSION_TOKEN")

        session_kwargs = {}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            session_kwargs["aws_session_token"] = aws_session_token
        if region:
            session_kwargs["region_name"] = region

        session = boto3.session.Session(**session_kwargs)

        if not self.bucket:
            raise ValueError("S3 bucket name not provided. Defina bucket_name ou a variável de ambiente S3_BUCKET/AWS_S3_BUCKET.")

        self.client = session.client("s3")

    def upload_file(self, file_path: str, key: str, extra_args: Optional[Dict] = None) -> str:
        try:
            self.client.upload_file(Filename=file_path, Bucket=self.bucket, Key=key, ExtraArgs=extra_args or {})
            return self._object_url(key)
        except ClientError as e:
            logger.exception(f"Failed to upload file to S3: {e}")
            raise

    def upload_bytes(self, data: bytes, key: str, content_type: Optional[str] = None, extra_args: Optional[Dict] = None) -> str:
        put_kwargs = {"Bucket": self.bucket, "Key": key, "Body": data}
        if content_type:
            put_kwargs["ContentType"] = content_type
        if extra_args:
            put_kwargs.update(extra_args)
        try:
            self.client.put_object(**put_kwargs)
            return self._object_url(key)
        except ClientError as e:
            logger.exception(f"Failed to upload bytes to S3: {e}")
            raise

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        
        except ClientError as e:
            logger.exception(f"Failed to generate presigned URL: {e}")
            raise

    def _object_url(self, key: str) -> str:
        region = self.client.meta.region_name
        if region and region != "us-east-1":
            return f"https://{self.bucket}.s3.{region}.amazonaws.com/{key}"
        
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"