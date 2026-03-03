import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login }       = useAuth()
  const navigate        = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

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
        <h2 className="auth-title">Iniciar sesión</h2>
        <p className="auth-subtitle">Accedé a tu espacio cinematográfico</p>

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

        <p className="auth-switch">
          ¿No tenés cuenta?{' '}
          <Link to="/register" className="auth-switch-link">Crear cuenta</Link>
        </p>
      </div>
    </div>
  )
}
