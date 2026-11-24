import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext'

// Register GSAP plugins once at app root
gsap.registerPlugin(ScrollTrigger)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
