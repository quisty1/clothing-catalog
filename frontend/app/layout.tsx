import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'Каталог — повседневные вещи',description:'Повседневные вещи. Продуманные детали.'};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){
  return <html lang="ru"><body>{children}</body></html>;
}
