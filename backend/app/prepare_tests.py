"""Create a separate test database without touching the application database."""
from sqlalchemy import create_engine, text
from app.config import Settings

engine=create_engine(Settings().database_url,isolation_level='AUTOCOMMIT')
with engine.connect() as connection:
    exists=connection.scalar(text("SELECT 1 FROM pg_database WHERE datname='catalog_test'"))
    if not exists:
        connection.execute(text('CREATE DATABASE catalog_test'))
engine.dispose()
print('catalog_test is ready')
