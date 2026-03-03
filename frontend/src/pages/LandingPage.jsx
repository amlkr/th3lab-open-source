import { Link } from 'react-router-dom'

export default function LandingPage() {
  return (
    <div className="landing-page">

      <header className="landing-header">
        <div className="landing-logo">
          <span className="landing-logo-mark">◈</span>
          <span className="landing-logo-text">th3lab</span>
        </div>
        <Link to="/login" className="landing-login-link">Iniciar sesión</Link>
      </header>

      <section className="landing-hero">
        <p className="landing-hero-tag">VISUAL CULT · Cinematography T00ls</p>
        <h1 className="landing-hero-title">th3lab</h1>
        <Link to="/login" className="landing-cta-btn">
          Entrar <span className="landing-cta-arrow">→</span>
        </Link>
      </section>

      <div className="landing-float-features">
        <span className="landing-float-item">◈ Análisis Visual</span>
        <span className="landing-float-item">⬡ Biblioteca Teórica</span>
        <span className="landing-float-item">◧ Colaborador IA</span>
      </div>

      <footer className="landing-footer">
        <span>© 2026 amlkr · th3lab</span>
      </footer>
    </div>
  )
}
