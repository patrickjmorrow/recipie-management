from contextlib import asynccontextmanager

import aiobotocore.session

from app.core.config import settings


@asynccontextmanager
async def s3_client():
    session = aiobotocore.session.get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
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
    async with s3_client() as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
    return url
