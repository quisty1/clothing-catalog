from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://catalog:catalog@localhost:55432/catalog'
    minio_endpoint: str = 'localhost:59000'
    minio_access_key: str = ''
    minio_secret_key: str = ''
    minio_bucket: str = 'catalog'
    minio_secure: bool = False
    bot_token: str = ''
    admin_ids: str = ''
    webhook_secret: str = ''
    public_url: str = ''

    @field_validator('public_url')
    @classmethod
    def normalize_url(cls, value):
        value = value.strip().rstrip('/')
        if value and not value.startswith('https://'):
            raise ValueError('PUBLIC_URL must use HTTPS')
        return value

    @property
    def administrators(self) -> set[int]:
        return {int(value.strip()) for value in self.admin_ids.split(',') if value.strip()}
