import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const API_BASE = ''

const WORLD_COLORS = {
  amniotic:        '#8b5cf6',
  cine_lentitud:   '#a8b5c0',
  cuerpo_politico: '#c4a882',
}

const WORLD_META = {
  amniotic:        { artClass: 'amniotic',       geoClass: 'amniotic' },
  cine_lentitud:   { artClass: 'cine-lentitud',  geoClass: 'cine-lentitud' },
  cuerpo_politico: { artClass: 'cuerpo-politico', geoClass: 'cuerpo-politico' },
}

// Mock schedule — will connect to project pipeline API
const SCHEDULE = [
  { time: '10:00', title: 'Análisis visual — Amniotic',     color: '#8b5cf6' },
  { time: '11:30', title: 'Carga biblioteca teórica',       color: '#a78bfa', action: 'Ver' },
  { time: '13:00', title: 'CLIP coherence — Cuerpo Político', color: '#c4a882' },
  { time: '15:00', title: 'Pipeline — Cine Lentitud',       color: '#a8b5c0', action: 'Ver' },
  { time: '17:00', title: 'Studio session',                 color: '#8b5cf6' },
]

// Mock activity breakdown — will connect to job type stats
const ACTIVITY = [
  { label: 'Análisis visual',  hours: 121, color: '#8b5cf6' },
  { label: 'Biblioteca RAG',   hours: 68,  color: '#a78bfa' },
  { label: 'Video jobs',       hours: 54,  color: '#c4b5fd' },
  { label: 'Reportes',         hours: 27,  color: '#a8b5c0' },
  { label: 'Studio',           hours: 13,  color: '#c4a882' },
]

// Mock tasks — will connect to /api/jobs per project
const MOCK_TASKS = [
  { name: 'Análisis serie Amniotic',     logged: '2.4h',  due: 'Mar 15' },
  { name: 'CLIP coherence report',       logged: '1.1h',  due: 'Mar 18' },
  { name: 'LoRA training data prep',     logged: '4.8h',  due: 'Abr 1'  },
  { name: 'Biblioteca — textos Belting', logged: '0.5h',  due: 'Mar 22' },
]

export default function DashboardPage() {
  const { user }   = useAuth()
  const [projects, setProjects]   = useState([])
  const [worlds, setWorlds]       = useState([])
  const [jobStats, setJobStats]   = useState(null)
  const [viewMode, setViewMode]   = useState('grid')
  const [searchQuery, setSearch]  = useState('')
  const [schedTab, setSchedTab]   = useState('hoy')
  const [actTab, setActTab]       = useState('dia')

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  useEffect(() => {
    fetch(`${API_BASE}/api/projects/`)
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : (data.projects ?? [])
        setProjects(list.slice(0, 10))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/api/library/worlds`)
      .then(r => r.json())
      .then(data => setWorlds(data.worlds ?? []))
      .catch(() => {
        setWorlds([
          { id: 'amniotic',        name: 'amniotic',        doc_count: 0 },
          { id: 'cine_lentitud',   name: 'cine_lentitud',   doc_count: 0 },
          { id: 'cuerpo_politico', name: 'cuerpo_político', doc_count: 0 },
        ])
      })
  }, [])

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/jobs/?status=completed&limit=1`).then(r => r.json()).catch(() => ({ total: 0 })),
      fetch(`${API_BASE}/api/jobs/?status=processing&limit=1`).then(r => r.json()).catch(() => ({ total: 0 })),
      fetch(`${API_BASE}/api/jobs/?job_type=video&limit=1`).then(r => r.json()).catch(() => ({ total: 0 })),
    ]).then(([completed, processing, videos]) => {
      setJobStats({
        completed: completed.total ?? 0,
        processing: processing.total ?? 0,
        videos: videos.total ?? 0,
      })
    })
  }, [])

  const filtered = projects.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Build donut segments from activity data
  const totalHours = ACTIVITY.reduce((s, a) => s + a.hours, 0)
  const circumference = 2 * Math.PI * 38
  let offset = 0
  const segments = ACTIVITY.map(a => {
    const dash = (a.hours / totalHours) * circumference
    const seg = { ...a, dash, offset }
    offset += dash
    return seg
  })

  return (
    <div className="dashboard-page">
      {/* Top bar */}
      <header className="dashboard-topbar">
        <div className="dashboard-topbar-left">
          <h1 className="dashboard-title">
            {user?.name ? `Hola, ${user.name.split(' ')[0]}` : 'Dashboard'}
          </h1>
          <span className="dashboard-date">{today}</span>
        </div>

        <div className="dashboard-actions">
          <div className="search-box">
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="14" height="14">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="Buscar proyectos..."
              value={searchQuery}
              onChange={e => setSearch(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="view-toggle">
            <button className={`toggle-btn${viewMode === 'grid' ? ' active' : ''}`} onClick={() => setViewMode('grid')}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
            </button>
            <button className={`toggle-btn${viewMode === 'list' ? ' active' : ''}`} onClick={() => setViewMode('list')}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <rect x="3" y="5" width="18" height="2" rx="1" />
                <rect x="3" y="11" width="18" height="2" rx="1" />
                <rect x="3" y="17" width="18" height="2" rx="1" />
              </svg>
            </button>
          </div>

          <Link to="/projects" className="add-new-btn">+ Proyecto</Link>
        </div>
      </header>

      <main className="dashboard-main">
        {/* Job stats strip */}
        {jobStats && (
          <div className="dashboard-stats-strip">
            <div className="dash-stat">
              <span className="dash-stat-value">{jobStats.completed}</span>
              <span className="dash-stat-label">análisis completados</span>
            </div>
            <div className="dash-stat-sep" />
            <div className="dash-stat">
              <span className="dash-stat-value">{jobStats.processing}</span>
              <span className="dash-stat-label">en proceso</span>
            </div>
            <div className="dash-stat-sep" />
            <div className="dash-stat">
              <span className="dash-stat-value">{jobStats.videos}</span>
              <span className="dash-stat-label">videos analizados</span>
            </div>
            <div className="dash-stat-sep" />
            <div className="dash-stat">
              <span className="dash-stat-value">{projects.length}</span>
              <span className="dash-stat-label">proyectos</span>
            </div>
          </div>
        )}

        {/* Recent Projects */}
        <section className="projects-section">
          <div className="projects-header">
            <span className="projects-title">Proyectos recientes</span>
            <Link to="/projects" className="all-tasks">
              Ver todos
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="12" height="12">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
          </div>

          {projects.length === 0 ? (
            <div className="dashboard-empty-projects">
              <span>Sin proyectos todavía — </span>
              <Link to="/projects" className="auth-switch-link">creá el primero</Link>
            </div>
          ) : (
            <div className={`projects-grid ${viewMode}`}>
              {filtered.map(project => (
                <Link key={project.id} to={`/projects/${project.id}`} className="project-thumb-card">
                  <div className="thumb-image">
                    <div className="project-dash-thumb-bg" />
                    <span className="project-dash-thumb-icon">◈</span>
                  </div>
                  <div className="thumb-info">
                    <span className="thumb-name">{project.name}</span>
                    <span className="thumb-status completed">
                      <span className="card-badge">{project.module}</span>
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Worlds */}
        <section className="worlds-section">
          <div className="worlds-section-header">
            <span className="worlds-section-title">Mundos</span>
          </div>
          <div className="worlds-grid">
            {worlds.map(w => {
              const wid   = w.id ?? w.world_id
              const meta  = WORLD_META[wid] ?? { artClass: wid, geoClass: wid }
              const color = WORLD_COLORS[wid] ?? '#8b5cf6'
              const docs  = w.doc_count ?? w.total_chunks ?? w.docs ?? 0
              const label = w.name ?? wid

              return (
                <div key={wid} className="world-card">
                  <div className={`world-card-art ${meta.artClass}`}>
                    <div className={`world-geo ${meta.geoClass}`} />
                  </div>
                  <div className="world-card-body">
                    <div className="world-name">{label}</div>
                    <div className="world-meta">
                      <span className="world-accent-dot" style={{ background: color }} />
                      <span className="world-meta-text">{docs} documentos</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* ── Schedule · Activity · Tasks ─────────────────────── */}
        <section className="dash-bottom">

          {/* Schedule */}
          <div className="sched-panel">
            <div className="sched-head">
              <span className="sched-title">Schedule</span>
              <div className="sched-tabs">
                {['hoy', 'semana', 'mes'].map(t => (
                  <button key={t} className={`sched-tab${schedTab === t ? ' active' : ''}`} onClick={() => setSchedTab(t)}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="sched-list">
              {SCHEDULE.map((item, i) => (
                <div key={i} className="sched-item">
                  <span className="sched-time">{item.time}</span>
                  <span className="sched-dot-small" style={{ background: item.color }} />
                  <span className="sched-name">{item.title}</span>
                  {item.action && <span className="sched-action">{item.action}</span>}
                </div>
              ))}
            </div>

            <button className="sched-add-btn">+ Agregar</button>
          </div>

          {/* Activity */}
          <div className="act-panel">
            <div className="act-head">
              <span className="act-title">Activity</span>
              <div className="act-nav">
                <button className="act-nav-btn">‹</button>
                <span className="act-nav-label">Hoy</span>
                <button className="act-nav-btn">›</button>
              </div>
            </div>

            <div className="act-tabs">
              {['dia', 'semana', 'mes'].map(t => (
                <button key={t} className={`act-tab${actTab === t ? ' active' : ''}`} onClick={() => setActTab(t)}>
                  {t === 'dia' ? 'Día' : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            <div className="act-chart-wrap">
              <svg viewBox="0 0 100 100" width="110" height="110">
                {segments.map((s, i) => (
                  <circle key={i} cx="50" cy="50" r="38" fill="none"
                    stroke={s.color} strokeWidth="16"
                    strokeDasharray={`${s.dash} ${circumference - s.dash}`}
                    strokeDashoffset={-s.offset}
                    transform="rotate(-90 50 50)"
                  />
                ))}
                <circle cx="50" cy="50" r="30" fill="#111111" />
              </svg>
            </div>

            <div className="act-legend">
              {ACTIVITY.map((a, i) => (
                <div key={i} className="act-legend-item">
                  <span className="act-legend-dot" style={{ background: a.color }} />
                  <span className="act-legend-label">{a.label}</span>
                  <span className="act-legend-hours">{a.hours}h</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tasks */}
          <div className="task-panel">
            <div className="task-head">
              <span className="task-title">Tasks</span>
              <div className="task-head-actions">
                <span className="task-filter">Filter</span>
                <span className="task-filter">Sort by</span>
                <Link to="/projects" className="task-all">All Tasks →</Link>
              </div>
            </div>

            <div className="task-cols-header">
              <span className="task-col-name">Nombre</span>
              <span className="task-col-logged">Tiempo</span>
              <span className="task-col-due">Fecha</span>
            </div>

            <div className="task-rows">
              {MOCK_TASKS.map((t, i) => (
                <div key={i} className="task-row">
                  <span className="task-col-name">{t.name}</span>
                  <span className="task-col-logged">{t.logged}</span>
                  <span className="task-col-due">{t.due}</span>
                </div>
              ))}
            </div>
          </div>

        </section>
      </main>
    </div>
  )
}
