from __future__ import annotations

import json
from typing import Dict
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )

    def presign_put_object(self, key: str, content_type: str) -> Dict[str, str]:
        raw_url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,
        )
        return {
            "upload_url": self._with_public_host(raw_url),
            "object_key": key,
            "fields": {},
        }

    def presign_get_object(self, key: str, expires: int = 3600) -> str:
        raw_url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires,
        )
        return self._with_public_host(raw_url)

    def ensure_bucket(self) -> None:
        existing = [b["Name"] for b in self.client.list_buckets().get("Buckets", [])]
        if settings.s3_bucket not in existing:
            try:
                self.client.create_bucket(
                    Bucket=settings.s3_bucket,
                    CreateBucketConfiguration={"LocationConstraint": settings.s3_region},
                )
            except ClientError:
                pass
            policy = json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": f"arn:aws:s3:::{settings.s3_bucket}/*",
                        }
                    ],
                }
            )
            self.client.put_bucket_policy(Bucket=settings.s3_bucket, Policy=policy)

    def put_object(self, key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    def _with_public_host(self, url: str) -> str:
        public = urlparse(settings.s3_public_url)
        parsed = urlparse(url)
        return urlunparse(
            (
                public.scheme,
                public.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )


storage_service = StorageService()
