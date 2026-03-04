import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth()
  const navigate        = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  useEffect(() => {
    if (!googleClientId) return

    let cancelled = false

    const setupGoogle = () => {
      if (cancelled) return
      const g = window.google
      if (!g?.accounts?.id) return

      g.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          if (!response?.credential) return
          setError('')
          setLoading(true)
          try {
            await loginWithGoogle(response.credential)
            navigate('/projects', { replace: true })
          } catch (err) {
            setError(err.message)
          } finally {
            setLoading(false)
          }
        },
      })

      const target = document.getElementById('google-signin-button')
      if (!target) return
      target.innerHTML = ''
      g.accounts.id.renderButton(target, {
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        shape: 'pill',
        width: 320,
      })
    }

    const existing = document.querySelector('script[data-google-identity="1"]')
    if (existing) {
      setupGoogle()
    } else {
      const script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.dataset.googleIdentity = '1'
      script.onload = setupGoogle
      document.body.appendChild(script)
    }

    return () => {
      cancelled = true
    }
  }, [googleClientId, loginWithGoogle, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/projects', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page auth-page--login">

      <Link to="/" className="auth-logo">
        <span className="landing-logo-mark">◈</span>
        <span className="landing-logo-text">th3lab</span>
      </Link>

      <div className="auth-card">
        <h2 className="auth-title">TH3LAB PRIVATE ACCESS</h2>
        <p className="auth-subtitle">secure</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="auth-label">Email</label>
            <input
              type="email"
              className="auth-input"
              placeholder="tu@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label className="auth-label">Contraseña</label>
            <input
              type="password"
              className="auth-input"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? 'Entrando...' : 'Iniciar sesión'}
          </button>
        </form>

        {googleClientId ? (
          <>
            <div className="auth-divider"><span>o</span></div>
            <div id="google-signin-button" className="auth-google-wrap" />
          </>
        ) : null}

        <p className="auth-switch">
          ¿No tenés cuenta?{' '}
          <Link to="/register" className="auth-switch-link">Crear cuenta</Link>
        </p>
      </div>
    </div>
  )
}
