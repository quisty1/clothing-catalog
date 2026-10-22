"""Real PostgreSQL + MinIO; only the external Telegram download is substituted."""
import asyncio
import os
from pathlib import Path
import uuid
import pytest
import httpx
from aiogram import Bot
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Settings
from app.main import create_app
from app.models import Base

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv('RUN_INTEGRATION') != '1', reason='Set RUN_INTEGRATION=1 with PostgreSQL and MinIO running')]
ROOT = Path(__file__).resolve().parents[2]
PHOTO = (ROOT / 'dist/assets/coat.jpg').read_bytes() if (ROOT / 'dist').exists() else Path('/demo-assets/coat.jpg').read_bytes()


def update(update_id=1, *, user=42, message_id=10, caption='  Новое пальто  ', **extra):
    message = {'message_id':message_id,'date':1700000000,
        'chat':{'id':user,'type':'private'},'from':{'id':user,'is_bot':False,'first_name':'Test'},
        'photo':[{'file_id':'small','file_unique_id':'s','width':100,'height':100,'file_size':500},
                 {'file_id':'large','file_unique_id':'l','width':1000,'height':1500,'file_size':len(PHOTO)}],
        'caption':caption, **extra}
    return {'update_id':update_id,'message':message}


@pytest.fixture
async def stack():
    env = dotenv_values(ROOT / '.env') if (ROOT / '.env').exists() else os.environ
    database = os.getenv('TEST_DATABASE_URL') or f"postgresql+psycopg://catalog:{env['POSTGRES_PASSWORD']}@localhost:55432/catalog_test"
    if not database.endswith('/catalog_test'):
        raise RuntimeError('Tests require a separate catalog_test database')
    settings = Settings(database_url=database,
        minio_endpoint=os.getenv('TEST_MINIO_ENDPOINT','localhost:59000'),
        minio_access_key=env.get('MINIO_ROOT_USER',''),minio_secret_key=env.get('MINIO_ROOT_PASSWORD',''),
        minio_bucket='test-'+uuid.uuid4().hex,
        bot_token='',admin_ids='42',webhook_secret='test-secret',public_url='https://catalog.example')
    engine = create_async_engine(database)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    bot = Bot('123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk')

    async def download(file, destination, **kwargs):
        assert file.file_id == 'large', 'Must download the highest resolution photo'
        destination.write(PHOTO)
        destination.seek(0)
        return destination
    bot.download = download
    app1 = create_app(settings, bot=bot)
    # Separate aiogram dispatcher and SQL pool simulate independent instances.
    # The second Bot must also use the fake external download.
    bot2 = Bot('123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk')
    bot2.download = download
    app2 = create_app(settings, bot=bot2)
    async with app1.router.lifespan_context(app1), app2.router.lifespan_context(app2):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app1, raise_app_exceptions=False),base_url='http://test') as one, \
                   httpx.AsyncClient(transport=httpx.ASGITransport(app=app2, raise_app_exceptions=False),base_url='http://test') as two:
            yield one, two, app1
    storage = app1.state.storage
    for obj in storage.client.list_objects(storage.bucket, recursive=True):
        storage.client.remove_object(storage.bucket,obj.object_name)
    storage.client.remove_bucket(storage.bucket)


async def send(client, data, secret='test-secret'):
    return await client.post('/telegram/webhook',json=data,
        headers={'X-Telegram-Bot-Api-Secret-Token':secret})


async def test_photo_persisted_and_visible_from_another_instance(stack):
    one,two,_ = stack
    response = await send(one,update())
    assert response.status_code == 200
    assert 'добавлен' in response.json()['text']
    products = (await two.get('/api/products')).json()
    assert len(products) == 1 and products[0]['name'] == 'Новое пальто'
    photo = await two.get(products[0]['image_url'])
    assert photo.status_code == 200 and photo.content == PHOTO
    assert photo.headers['content-type'] == 'image/jpeg'


async def test_concurrent_duplicate_deliveries_create_one_product(stack):
    one,two,_ = stack
    results = await asyncio.gather(*(send(client,update()) for client in [one,two,one,two]))
    assert all(response.status_code == 200 for response in results)
    assert len((await two.get('/api/products')).json()) == 1
    assert results[0].json() == results[1].json()
    # Same Telegram message in a different update also cannot create a duplicate.
    assert (await send(two,update(update_id=2))).status_code == 200
    assert len((await one.get('/api/products')).json()) == 1


async def test_storage_failure_does_not_acknowledge_update_and_retry_succeeds(stack, monkeypatch):
    one,two,app = stack
    real_put = app.state.storage.put
    async def unavailable(*args,**kwargs):
        raise OSError('simulated storage outage')
    monkeypatch.setattr(app.state.storage,'put',unavailable)
    assert (await send(one,update())).status_code == 503
    assert (await two.get('/api/products')).json() == []
    monkeypatch.setattr(app.state.storage,'put',real_put)
    assert (await send(two,update())).status_code == 200
    assert len((await one.get('/api/products')).json()) == 1


async def test_failed_sql_transaction_after_upload_can_retry(stack, monkeypatch):
    one,two,app = stack
    original = app.state.storage.put
    async def upload_then_fail(*args,**kwargs):
        await original(*args,**kwargs)
        raise RuntimeError('crash after object upload before SQL commit')
    monkeypatch.setattr(app.state.storage,'put',upload_then_fail)
    assert (await send(one,update())).status_code == 503
    assert (await send(two,update())).status_code == 200
    assert len((await two.get('/api/products')).json()) == 1
    objects=list(app.state.storage.client.list_objects(app.state.storage.bucket,recursive=True))
    assert len(objects)==1


async def test_authorization_validation_and_no_public_write_api(stack):
    one,two,_=stack
    assert (await send(one,update(),secret='wrong')).status_code == 403
    assert (await send(one,update(user=99))).status_code == 200
    assert (await send(one,update(update_id=2,caption=''))).status_code == 200
    assert (await send(one,update(update_id=3,media_group_id='album'))).status_code == 200
    assert (await two.get('/api/products')).json() == []
    assert (await one.post('/api/products',json={'name':'forged'})).status_code == 405
    assert (await one.get('/api/products/'+str(uuid.uuid4())+'/image')).status_code == 404


async def test_welcome_returns_mini_app_and_admin_action(stack):
    one,_,_=stack
    data=update()
    data['message'].pop('photo');data['message'].pop('caption');data['message']['text']='/start'
    response=await send(one,data)
    body=response.json()
    assert body['method']=='sendMessage' and body['text']=='У меня есть товар'
    assert body['reply_markup']['inline_keyboard'][0][0]['web_app']['url']=='https://catalog.example'
    assert body['reply_markup']['inline_keyboard'][1][0]['callback_data']=='create_product'


async def test_admin_text_welcomes_and_pending_upload_survives_instance_switch(stack):
    one,two,_=stack
    def text_update(number,text):
        data=update(update_id=number,message_id=number)
        data['message'].pop('photo');data['message'].pop('caption');data['message']['text']=text
        return data
    assert (await send(one,text_update(1,'Привет'))).json()['text']=='У меня есть товар'
    assert 'подписи' in (await send(one,text_update(2,'/create_product'))).json()['text']
    assert 'подписи' in (await send(two,text_update(3,'Пальто'))).json()['text']
    assert (await two.get('/api/products')).json()==[]
    assert 'добавлен' in (await send(two,update(update_id=4,message_id=4))).json()['text']
    assert (await send(one,text_update(5,'Спасибо'))).json()['text']=='У меня есть товар'


async def test_operational_errors_are_sanitized_without_escaping_request(stack,monkeypatch):
    _,_,app=stack
    async def outage(*args,**kwargs):
        raise OSError('private infrastructure details')
    monkeypatch.setattr(app.state.storage,'put',outage)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await send(client,update())
    assert response.status_code==503
    assert 'private infrastructure details' not in response.text


async def test_unhandled_update_is_acknowledged_instead_of_retried_forever(stack):
    one,_,_=stack
    response=await send(one,{'update_id':100,'edited_message':update()['message']})
    assert response.status_code==200 and response.json()=={}


async def test_create_button_checks_sender_and_persists_prompt(stack):
    one,two,_=stack
    def callback(number,user):
        return {'update_id':number,'callback_query':{'id':str(number),
            'from':{'id':user,'is_bot':False,'first_name':'Test'},
            'chat_instance':'test','data':'create_product'}}
    denied=(await send(one,callback(1,99))).json()
    assert denied['method']=='answerCallbackQuery' and 'администратору' in denied['text']
    accepted=(await send(one,callback(2,42))).json()
    assert accepted['method']=='answerCallbackQuery' and 'подписи' in accepted['text']
    data=update(update_id=3)
    data['message'].pop('photo');data['message'].pop('caption');data['message']['text']='Пальто'
    assert 'подписи' in (await send(two,data)).json()['text']
