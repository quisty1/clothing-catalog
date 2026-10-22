import hashlib
from sqlalchemy import select, text
from app.models import Product


async def lock_key(session, key):
    # Transaction-scoped and shared by all processes. A crash releases the lock.
    await session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'), {'key': key})


async def create_product(session, storage, *, title, source_key, load_photo):
    await lock_key(session, 'product:' + source_key)
    existing = await session.scalar(select(Product).where(Product.source_key == source_key))
    if existing:
        return existing
    data = await load_photo()
    key = 'products/' + hashlib.sha256(source_key.encode()).hexdigest() + '.jpg'
    # Deterministic keys make retries safe even after a crash between S3 and SQL.
    # Never delete on rollback: a concurrent retry may already reference the key.
    await storage.put(key, data)
    product = Product(name=title, source_key=source_key, object_key=key)
    session.add(product)
    await session.flush()
    return product
