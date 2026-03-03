import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

import { API_BASE } from '../config/api'

const WORLD_COLORS = {
  amniotic:        '#8b5cf6',
  cine_lentitud:   '#a8b5c0',
  cuerpo_politico: '#c4a882',
}

function getWorldColor(module) {
  return WORLD_COLORS[module] ?? '#8b5cf6'
}

function CreateModal({ onClose, onCreate, userId }) {
  const [name, setName]     = useState('')
  const [module, setModule] = useState('th3lab')
  const [busy, setBusy]     = useState(false)
  const [err, setErr]       = useState(null)
  const inputRef            = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSubmit = async () => {
    if (!name.trim() || busy) return
    setBusy(true)
    setErr(null)
    try {
      const res = await fetch(`${API_BASE}/api/projects/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          name:     name.trim(),
          module,
          owner_id: userId ?? null,
        }),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      const project = await res.json()
      onCreate(project)
    } catch {
      setErr('Error al crear el proyecto. ¿Está el backend corriendo?')
      setBusy(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter') handleSubmit()
    if (e.key === 'Escape') onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} onKeyDown={handleKey}>
        <div className="modal-header">
          <span className="modal-title">Nuevo proyecto</span>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <label className="modal-label">Nombre</label>
          <input
            ref={inputRef}
            className="modal-input"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="ej. Serie nocturna 01"
          />

          <label className="modal-label" style={{ marginTop: 16 }}>Módulo</label>
          <div className="module-toggle">
            <button
              className={`module-btn${module === 'th3lab' ? ' active' : ''}`}
              onClick={() => setModule('th3lab')}
            >
              th3lab
            </button>
            <button
              className={`module-btn${module === 'visual_cult' ? ' active' : ''}`}
              onClick={() => setModule('visual_cult')}
            >
              VISUAL CULT
            </button>
          </div>

          {err && <p className="modal-error">{err}</p>}
        </div>

        <div className="modal-footer">
          <button className="modal-cancel-btn" onClick={onClose}>cancelar</button>
          <button
            className="modal-confirm-btn"
            onClick={handleSubmit}
            disabled={!name.trim() || busy}
          >
            {busy ? 'creando...' : 'crear proyecto'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ProjectsPage() {
  const { user }   = useAuth()
  const navigate   = useNavigate()
  const [projects, setProjects]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = () => {
    setLoading(true)
    fetch(`${API_BASE}/api/projects/`)
      .then(r => r.json())
      .then(data => {
        setProjects(Array.isArray(data) ? data : (data.projects ?? []))
        setLoading(false)
      })
      .catch(() => {
        setError('No se puede conectar al backend.')
        setLoading(false)
      })
  }

  useEffect(load, [])

  const handleCreated = (project) => {
    navigate(`/projects/${project.id}`)
  }

  if (loading) {
    return (
      <div className="projects-page">
        <div className="page-loading">
          <span className="page-loading-dot">◈</span>
          <span>cargando proyectos...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="projects-page">
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Proyectos</h1>
          {error && <span className="page-error-inline">{error}</span>}
        </div>
        <button className="upload-btn" onClick={() => setShowCreate(true)}>
          + nuevo proyecto
        </button>
      </div>

      {projects.length === 0 && !error ? (
        <div className="page-empty">
          <div className="empty-icon">◻</div>
          <p>Sin proyectos todavía</p>
          <span>Creá un proyecto para comenzar el análisis</span>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map(p => {
            const worldColor = getWorldColor(p.world ?? p.module)
            const date = p.created_at
              ? new Date(p.created_at).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
              : null

            return (
              <Link key={p.id} to={`/projects/${p.id}`} className="project-card">
                <div className="project-card-inner">
                  <div className="project-card-thumb">
                    <div className="geo-circle" />
                    <div className="geo-square" />
                    <span className="project-card-placeholder">◈</span>
                    <span
                      className="project-world-dot"
                      style={{ background: worldColor, boxShadow: `0 0 8px ${worldColor}80` }}
                    />
                  </div>
                  <div className="project-card-info">
                    <span className="project-card-name">{p.name}</span>
                    <div className="project-card-meta">
                      <span className="card-badge">{p.module}</span>
                      {date && <span className="card-badge">{date}</span>}
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
          userId={user?.id}
        />
      )}
    </div>
  )
}
