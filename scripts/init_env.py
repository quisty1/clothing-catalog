"""Create local secrets once; never overwrite a configured environment."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
path = root / '.env'
if path.exists():
    print('.env already exists; left unchanged')
else:
    path.write_text(
        f'POSTGRES_PASSWORD={secrets.token_hex(24)}\n'
        'MINIO_ROOT_USER=catalog-admin\n'
        f'MINIO_ROOT_PASSWORD={secrets.token_hex(24)}\n'
        'BOT_TOKEN=\nADMIN_IDS=\n'
        f'WEBHOOK_SECRET={secrets.token_hex(32)}\nPUBLIC_URL=\n'
    )
    path.chmod(0o600)
    print('Created .env. Add BOT_TOKEN, ADMIN_IDS and PUBLIC_URL locally.')
