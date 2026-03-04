import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../config/api'

const WORLD_COLORS = {
  amniotic: '#8b5cf6',
  cine_lentitud: '#a8b5c0',
  cuerpo_politico: '#c4a882',
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

export default function DashboardPage() {
  const canvasRef = useRef(null)
  const dragRef = useRef({ dragging: false, startX: 0, startY: 0, baseX: 0, baseY: 0 })

  const [projects, setProjects] = useState([])
  const [worlds, setWorlds] = useState([])
  const [query, setQuery] = useState('')

  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const mainAgentUrl = import.meta.env.VITE_MAIN_AGENT_URL || 'https://th3lab-superinterface.vercel.app'

  useEffect(() => {
    fetch(`${API_BASE}/api/projects/`)
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : (data.projects ?? [])
        setProjects(list.slice(0, 24))
      })
      .catch(() => setProjects([]))

    fetch(`${API_BASE}/api/library/worlds`)
      .then((r) => r.json())
      .then((data) => setWorlds(data.worlds ?? []))
      .catch(() => setWorlds([]))
  }, [])

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
  }, [projects, query])

  function onWheel(event) {
    event.preventDefault()
    const delta = event.deltaY > 0 ? -0.08 : 0.08
    setZoom((z) => clamp(Number((z + delta).toFixed(2)), 0.6, 2.1))
  }

  function onMouseDown(event) {
    dragRef.current = {
      dragging: true,
      startX: event.clientX,
      startY: event.clientY,
      baseX: offset.x,
      baseY: offset.y,
    }
  }

  function onMouseMove(event) {
    if (!dragRef.current.dragging) return
    const dx = event.clientX - dragRef.current.startX
    const dy = event.clientY - dragRef.current.startY
    setOffset({
      x: dragRef.current.baseX + dx,
      y: dragRef.current.baseY + dy,
    })
  }

  function onMouseUp() {
    dragRef.current.dragging = false
  }

  function resetView() {
    setZoom(1)
    setOffset({ x: 0, y: 0 })
  }

  return (
    <div className="canvas-page">
      <header className="canvas-topbar">
        <div className="canvas-brand">
          <span className="canvas-title">TH3LAB CANVAS</span>
          <span className="canvas-subtitle">narrative surface</span>
        </div>

        <div className="canvas-controls">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="canvas-search"
            placeholder="buscar escena / proyecto"
          />
          <button className="canvas-btn" onClick={resetView}>reset</button>
          <a className="canvas-btn" href={mainAgentUrl} target="_blank" rel="noreferrer">
            main agent
          </a>
          <Link className="canvas-btn canvas-btn-solid" to="/projects">+ proyecto</Link>
        </div>
      </header>

      <div
        ref={canvasRef}
        className="canvas-stage"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <div className="canvas-grid" />

        <div
          className="canvas-world"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`
          }}
        >
          <section className="canvas-ribbon">
            {worlds.map((w) => {
              const wid = w.id ?? w.world_id
              const name = w.name ?? wid
              const color = WORLD_COLORS[wid] ?? '#8b5cf6'
              const docs = w.doc_count ?? w.total_chunks ?? 0
              return (
                <article key={wid} className="world-chip" style={{ borderColor: `${color}55` }}>
                  <span className="world-dot" style={{ background: color }} />
                  <span>{name}</span>
                  <span className="world-count">{docs}</span>
                </article>
              )
            })}
          </section>

          <section className="scene-field">
            {filteredProjects.length === 0 ? (
              <div className="canvas-empty">sin proyectos en este filtro</div>
            ) : (
              filteredProjects.map((p, idx) => {
                const x = (idx % 6) * 280 + (idx % 2 ? 40 : 0)
                const y = Math.floor(idx / 6) * 220 + (idx % 3) * 12
                return (
                  <Link
                    key={p.id}
                    to={`/projects/${p.id}`}
                    className="scene-card"
                    style={{ left: x, top: y }}
                  >
                    <div className="scene-thumb" />
                    <div className="scene-meta">
                      <div className="scene-name">{p.name}</div>
                      <div className="scene-info">{p.module || 'narrativa visual'}</div>
                    </div>
                  </Link>
                )
              })
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
