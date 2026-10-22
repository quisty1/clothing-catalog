import asyncio
from io import BytesIO
from minio import Minio
from minio.error import S3Error
import urllib3


class ObjectStorage:
    def __init__(self, settings):
        self.bucket = settings.minio_bucket
        self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key,
                            secret_key=settings.minio_secret_key, secure=settings.minio_secure,
                            http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=3, read=15), retries=False))

    async def initialize(self):
        def ensure_bucket():
            if not self.client.bucket_exists(self.bucket):
                try:
                    self.client.make_bucket(self.bucket)
                except S3Error as error:
                    if error.code not in {'BucketAlreadyExists', 'BucketAlreadyOwnedByYou'}:
                        raise
        await asyncio.to_thread(ensure_bucket)

    async def put(self, key: str, data: bytes, content_type='image/jpeg'):
        await asyncio.to_thread(self.client.put_object, self.bucket, key, BytesIO(data),
                                len(data), content_type=content_type)

    def open(self, key):
        return self.client.get_object(self.bucket, key)

    async def ready(self):
        return await asyncio.to_thread(self.client.bucket_exists, self.bucket)
