import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './store/theme' // applies persisted theme before first paint

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
