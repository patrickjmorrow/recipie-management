import logging
from contextlib import asynccontextmanager

import aiobotocore.session
from botocore.config import Config

from app.core.config import settings


_S3_CONFIG = Config(signature_version="s3v4", s3={"addressing_style": "path"})


@asynccontextmanager
async def s3_client(endpoint_url: str | None = None):
    session = aiobotocore.session.get_session()
    async with session.create_client(
        "s3",
        endpoint_url=endpoint_url or settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
        config=_S3_CONFIG,
    ) as client:
        yield client


async def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    async with s3_client() as client:
        await client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    return key


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    # Sign using the public endpoint so the Host in the signature matches what the browser sends.
    public_endpoint = settings.S3_PUBLIC_URL or settings.S3_ENDPOINT_URL
    async with s3_client(endpoint_url=public_endpoint) as client:
        return await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )


async def delete_file(key: str) -> None:
    async with s3_client() as client:
        await client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
