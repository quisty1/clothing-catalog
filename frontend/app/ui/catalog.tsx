'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import TelegramBridge, { type TelegramApp } from './telegram';

type Product={id:string;name:string;image_url:string;created_at:string};

function ProductImage({product,priority=false}:{product:Product;priority?:boolean}){
  const [failed,setFailed]=useState(false);
  return failed?<span className="image-fallback" role="status">Фото пока недоступно</span>:
    // The API streams the original JPEG; no per-instance image optimization cache.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={product.image_url} alt={product.name} width={800} height={1000}
      loading={priority?'eager':'lazy'} decoding="async" fetchPriority={priority?'high':'auto'}
      onError={()=>setFailed(true)}/>;
}

function Plus(){return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;}

export default function Catalog(){
  const [products,setProducts]=useState<Product[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState(false);
  const [selected,setSelected]=useState<Product|null>(null);
  const [telegram,setTelegram]=useState<TelegramApp>();
  const dialog=useRef<HTMLDialogElement>(null);
  const trigger=useRef<HTMLButtonElement|null>(null);
  const request=useRef<AbortController|null>(null);

  const refresh=useCallback(async()=>{
    request.current?.abort();
    const controller=new AbortController();request.current=controller;
    try{
      const response=await fetch('/api/products',{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw new Error('API unavailable');
      const data:unknown=await response.json();
      if(!Array.isArray(data)||!data.every(p=>p&&typeof p.id==='string'&&typeof p.name==='string'&&typeof p.image_url==='string'))throw new Error('Invalid API response');
      setProducts(data);setError(false);
    }catch{
      if(!controller.signal.aborted)setError(true);
    }finally{
      if(!controller.signal.aborted)setLoading(false);
    }
  },[]);

  useEffect(()=>{
    void refresh();
    const visibleRefresh=()=>{if(document.visibilityState==='visible')void refresh();};
    window.addEventListener('focus',visibleRefresh);
    document.addEventListener('visibilitychange',visibleRefresh);
    const timer=window.setInterval(visibleRefresh,10000);
    return()=>{request.current?.abort();window.clearInterval(timer);window.removeEventListener('focus',visibleRefresh);document.removeEventListener('visibilitychange',visibleRefresh);};
  },[refresh]);

  useEffect(()=>{
    if(selected){dialog.current?.showModal();document.body.classList.add('dialog-open');}
    else{dialog.current?.close();document.body.classList.remove('dialog-open');}
    return()=>document.body.classList.remove('dialog-open');
  },[selected]);

  useEffect(()=>{
    if(!telegram)return;
    const close=()=>setSelected(null);
    if(selected){telegram.BackButton.show();telegram.BackButton.onClick(close);}
    else telegram.BackButton.hide();
    return()=>{telegram.BackButton.offClick(close);telegram.BackButton.hide();};
  },[selected,telegram]);

  function close(){setSelected(null);trigger.current?.focus({preventScroll:true});}
  return <>
    <TelegramBridge onReady={setTelegram}/>
    <a className="skip-link" href="#collection">К коллекции</a>
    <header className="site-header"><div className="header-inner"><a className="wordmark" href="#" aria-label="Каталог — начало страницы">Каталог<span className="wordmark-dot" aria-hidden="true">.</span></a><span className="header-caption">Одежда на каждый день</span></div></header>
    <main className="page">
      <section className="intro" aria-labelledby="page-title"><h1 id="page-title">Каталог</h1><p className="intro-tagline">Повседневные вещи.<br/><span>Продуманные детали.</span></p></section>
      <section className="collection" id="collection" aria-labelledby="collection-title">
        <div className="collection-heading"><h2 id="collection-title">Вся коллекция</h2><span className="collection-count" aria-live="polite">{!loading&&!error?`${products.length} ${products.length%10===1&&products.length%100!==11?'вещь':products.length%10>=2&&products.length%10<=4&&(products.length%100<12||products.length%100>14)?'вещи':'вещей'}`:''}</span></div>
        {error?<div className="collection-state" role="alert"><h3>Не удалось загрузить коллекцию</h3><p>Проверьте соединение и попробуйте ещё раз.</p><button className="retry-button" type="button" onClick={()=>void refresh()}>Повторить</button></div>:null}
        {loading?<div className="collection-state" role="status">Загружаем коллекцию…</div>:null}
        {!loading&&!error&&products.length===0?<div className="collection-state empty-state"><svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M16 12a4 4 0 1 1 4 4v4l14 8a2 2 0 0 1-1 4H7a2 2 0 0 1-1-4l14-8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg><h3>Пока ничего нет</h3><p>Новые вещи появятся здесь.</p></div>:null}
        <div className="product-grid">{products.map((product,index)=><article className="product-card" key={product.id}><button className="product-button" type="button" aria-haspopup="dialog" aria-label={`Посмотреть: ${product.name}`} onClick={event=>{trigger.current=event.currentTarget;setSelected(product);}}><div className="product-image"><ProductImage product={product} priority={index<3}/><span className="product-plus" aria-hidden="true"><Plus/></span></div><div className="product-info"><h3>{product.name}</h3></div></button></article>)}</div>
      </section>
    </main>
    <footer className="site-footer"><div className="footer-inner"><span className="footer-wordmark">Каталог.</span><span>Меньше лишнего. Больше вашего.</span></div></footer>
    <dialog ref={dialog} className="product-dialog" aria-labelledby="dialog-title" onClose={close} onClick={event=>{
      if(event.target!==dialog.current)return;const bounds=event.currentTarget.getBoundingClientRect();
      if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)setSelected(null);
    }}>
      {selected?<div className="dialog-layout"><button className="close-button" type="button" aria-label="Закрыть просмотр товара" autoFocus onClick={()=>setSelected(null)}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg></button><div className="dialog-image-wrap"><ProductImage key={selected.id} product={selected} priority/></div><div className="dialog-information"><span className="dialog-collection">Коллекция на каждый день</span><h2 id="dialog-title">{selected.name}</h2></div></div>:null}
    </dialog>
  </>;
}
