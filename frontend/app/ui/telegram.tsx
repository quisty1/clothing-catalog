'use client';
import Script from 'next/script';
import { useEffect, useRef } from 'react';

type Insets = {top:number;bottom:number;left:number;right:number};
export type TelegramApp = {
  initData:string;ready:()=>void;expand:()=>void;
  safeAreaInset?:Insets;contentSafeAreaInset?:Insets;
  onEvent:(name:string,callback:()=>void)=>void;
  offEvent:(name:string,callback:()=>void)=>void;
  BackButton:{show:()=>void;hide:()=>void;onClick:(fn:()=>void)=>void;offClick:(fn:()=>void)=>void};
};
declare global {interface Window {Telegram?:{WebApp:TelegramApp}}}

export default function TelegramBridge({onReady}:{onReady:(app:TelegramApp)=>void}){
  const cleanup=useRef<()=>void>(()=>{});
  useEffect(()=>()=>cleanup.current(),[]);
  function initialize(){
    const app=window.Telegram?.WebApp;
    if(!app?.initData)return;
    app.ready();app.expand();
    const updateInsets=()=>{
      for(const side of ['top','bottom','left','right'] as const){
        const inset=(app.safeAreaInset?.[side] || 0)+(app.contentSafeAreaInset?.[side] || 0);
        document.documentElement.style.setProperty(`--tg-safe-${side}`,`${inset}px`);
      }
    };
    updateInsets();
    app.onEvent('safeAreaChanged',updateInsets);app.onEvent('contentSafeAreaChanged',updateInsets);
    cleanup.current=()=>{app.offEvent('safeAreaChanged',updateInsets);app.offEvent('contentSafeAreaChanged',updateInsets);};
    onReady(app);
  }
  return <Script src="https://telegram.org/js/telegram-web-app.js" strategy="afterInteractive" onReady={initialize}/>;
}
