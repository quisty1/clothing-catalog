import { test, expect } from '@playwright/test';

const product = {id:'6e9b0f80-1845-4df8-a4bc-0615616fa148',name:'Пальто',image_url:'/api/products/6e9b0f80-1845-4df8-a4bc-0615616fa148/image',created_at:'2026-10-22T00:00:00Z'};
const image = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64');

test('empty database shows an empty collection without demo products',async({page})=>{
  await page.route('**/api/products',r=>r.fulfill({json:[]}));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Каталог',exact:true})).toBeVisible();
  await expect(page.getByText('Пока ничего нет')).toBeVisible();
  await expect(page.locator('.product-card')).toHaveCount(0);
});

test('failed API can be retried and displays the real product',async({page})=>{
  let failed=true;
  await page.route('**/api/products',r=>failed?r.fulfill({status:503,json:{detail:'Unavailable'}}):r.fulfill({json:[product]}));
  await page.route('**/api/products/*/image',r=>r.fulfill({contentType:'image/png',body:image}));
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Повторить'})).toBeVisible();
  failed=false;
  await page.getByRole('button',{name:'Повторить'}).click();
  await expect(page.getByRole('button',{name:'Посмотреть: Пальто'})).toBeVisible();
});

test('keyboard opens product and Escape restores focus; broken image has fallback',async({page})=>{
  await page.route('**/api/products',r=>r.fulfill({json:[product]}));
  await page.route('**/api/products/*/image',r=>r.fulfill({status:404}));
  await page.goto('/');
  const card=page.getByRole('button',{name:'Посмотреть: Пальто'});
  await card.focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByText('Фото пока недоступно')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(card).toBeFocused();
});

for(const width of [375,768,1440]){
  test(`layout at ${width}px has correct columns and no horizontal overflow`,async({page})=>{
    await page.setViewportSize({width,height:1000});
    await page.route('**/api/products',r=>r.fulfill({json:[product,{...product,id:'2'},{...product,id:'3'}]}));
    await page.route('**/api/products/*/image',r=>r.fulfill({contentType:'image/png',body:image}));
    await page.goto('/');
    await expect(page.locator('.product-card')).toHaveCount(3);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const columns=await page.locator('.product-grid').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length);
    expect(columns).toBe(width===375?1:width===768?2:3);
    await page.getByRole('button',{name:'Посмотреть: Пальто'}).first().click();
    if(width===375){
      const bounds=await page.getByRole('dialog').boundingBox();
      expect(bounds?.width).toBe(375);expect(bounds?.height).toBe(1000);
    }
    await page.getByRole('button',{name:'Закрыть просмотр товара'}).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
}

test('Telegram bridge handles safe areas and BackButton while browser needs no Telegram',async({page})=>{
  await page.route('https://telegram.org/js/telegram-web-app.js',r=>r.fulfill({contentType:'text/javascript',body:`
    window.tgEvents={};window.tgBackVisible=false;
    window.Telegram={WebApp:{initData:'test',ready(){},expand(){},
      safeAreaInset:{top:12,bottom:20,left:0,right:0},contentSafeAreaInset:{top:0,bottom:0,left:0,right:0},
      onEvent(name,fn){window.tgEvents[name]=fn},offEvent(name){delete window.tgEvents[name]},
      BackButton:{show(){window.tgBackVisible=true},hide(){window.tgBackVisible=false},
        onClick(fn){window.tgBack=fn},offClick(){window.tgBack=null}}}};` }));
  await page.route('**/api/products',r=>r.fulfill({json:[product]}));
  await page.route('**/api/products/*/image',r=>r.fulfill({contentType:'image/png',body:image}));
  await page.goto('/');
  await expect.poll(()=>page.evaluate(()=>document.documentElement.style.getPropertyValue('--tg-safe-top'))).toBe('12px');
  await page.getByRole('button',{name:'Посмотреть: Пальто'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as unknown as {tgBackVisible:boolean}).tgBackVisible)).toBe(true);
  await page.evaluate(()=>(window as unknown as {tgBack:()=>void}).tgBack());
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('reduced motion removes dialog and image transitions',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.route('**/api/products',r=>r.fulfill({json:[product]}));
  await page.route('**/api/products/*/image',r=>r.fulfill({contentType:'image/png',body:image}));
  await page.goto('/');await page.getByRole('button',{name:'Посмотреть: Пальто'}).click();
  expect(await page.getByRole('dialog').evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
});
