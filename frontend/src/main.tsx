import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { CurrencyProvider } from './context/CurrencyContext.tsx'
import { registerServiceWorker } from './utils/push.ts'

// Inline cast (not a variable) so Vite can statically replace import.meta.env.
if ((import.meta as ImportMeta & { env?: { PROD?: boolean } }).env?.PROD) registerServiceWorker()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CurrencyProvider>
      <App />
    </CurrencyProvider>
  </React.StrictMode>,
)
