import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const API_BASE = ''

const WORLDS = [
  { id: 'amniotic',       label: 'amniotic',        color: '#8b5cf6' },
  { id: 'cine_lentitud',  label: 'cine_lentitud',   color: '#a8b5c0' },
  { id: 'cuerpo_politico',label: 'cuerpo_político',  color: '#c4a882' },
]

export default function StudioPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const userId = user?.id ?? null
  const [images, setImages]       = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [coherence, setCoherence] = useState(null)
  const [world, setWorld]         = useState('amniotic')
  const [jobId, setJobId]         = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [results, setResults]     = useState(null)

  const fileInputRef = useRef(null)
  const pollRef      = useRef(null)

  // Load existing images from API if project id is given
  useEffect(() => {
    if (!id) {
      // Mock data for standalone /studio
      setImages([
        { id: 1, src: 'https://picsum.photos/600/800?random=1', name: 'IMG_001.jpg' },
        { id: 2, src: 'https://picsum.photos/800/600?random=2', name: 'IMG_002.jpg' },
        { id: 3, src: 'https://picsum.photos/600/900?random=3', name: 'IMG_003.jpg' },
        { id: 4, src: 'https://picsum.photos/700/700?random=4', name: 'IMG_004.jpg' },
        { id: 5, src: 'https://picsum.photos/600/750?random=5', name: 'IMG_005.jpg' },
        { id: 6, src: 'https://picsum.photos/800/550?random=6', name: 'IMG_006.jpg' },
      ])
      return
    }
    // Load jobs for this project
    fetch(`${API_BASE}/api/jobs/?project_id=${id}&status=completed&limit=1`)
      .then(r => r.json())
      .then(async data => {
        const jobs = data.jobs ?? []
        if (!jobs.length) return
        const jobRes = await fetch(`${API_BASE}/api/jobs/${jobs[0].job_id}`)
        const job    = await jobRes.json()
        if (!job.result) return
        setResults(job.result)
        const coherenceVal = job.result?.coherence?.score
        if (coherenceVal != null) setCoherence(Math.round(coherenceVal))

        const filenames = job.input_data?.filenames ?? []
        const paths     = job.input_data?.image_paths ?? []
        const loaded    = filenames.map((name, i) => {
          const basename = paths[i]?.split('/').pop()
          return {
            id:   i,
            src:  basename ? `${API_BASE}/static/uploads/${basename}` : null,
            name,
          }
        }).filter(img => img.src)
        if (loaded.length) setImages(loaded)
      })
      .catch(() => {})
  }, [id])

  // Poll job
  useEffect(() => {
    if (!jobId) return
    pollRef.current = setInterval(async () => {
      try {
        const res  = await fetch(`${API_BASE}/api/jobs/${jobId}`)
        const data = await res.json()
        setJobStatus(data.status)
        if (data.status === 'completed') {
          clearInterval(pollRef.current)
          setAnalyzing(false)
          setResults(data.result ?? {})
          const cScore = data.result?.coherence?.score
          if (cScore != null) setCoherence(Math.round(cScore))
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current)
          setAnalyzing(false)
        }
      } catch {
        clearInterval(pollRef.current)
      }
    }, 3000)
    return () => clearInterval(pollRef.current)
  }, [jobId])

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files)
    e.target.value = ''
    if (!files.length) return

    const previews = files.map(f => ({
      id:   `${f.name}-${Date.now()}-${Math.random()}`,
      src:  URL.createObjectURL(f),
      name: f.name,
    }))
    setImages(prev => [...prev, ...previews])
    setAnalyzing(true)

    try {
      const form = new FormData()
      if (id)     form.append('project_id', id)
      if (userId) form.append('user_id', userId)
      files.forEach(f => form.append('files', f))
      const res  = await fetch(`${API_BASE}/api/analysis/images`, { method: 'POST', body: form })
      if (res.ok) {
        const data = await res.json()
        setJobId(data.job_id)
        setJobStatus('processing')
      } else {
        setAnalyzing(false)
      }
    } catch {
      setAnalyzing(false)
    }
  }

  const selectedImg = images.find(img => img.id === selectedId)
  const selectedSemantic = selectedImg
    ? results?.semantic_analysis?.[images.indexOf(selectedImg)]
    : null

  const activeWorld = WORLDS.find(w => w.id === world) ?? WORLDS[0]

  return (
    <div className="studio-page">
      {/* Header */}
      <header className="studio-header">
        <div className="studio-header-left">
          <h1 className="studio-title">{id ? `Serie — ${id.slice(0, 8)}` : 'Serie 01'}</h1>
          {coherence !== null && (
            <span className="studio-coherence">
              Coherencia: {coherence}%
            </span>
          )}
        </div>
        <div className="studio-header-right">
          {analyzing && (
            <span className="studio-analyzing">
              <span className="analyzing-dot" />
              Analizando...
            </span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button
            className="studio-add-btn"
            onClick={() => fileInputRef.current?.click()}
          >
            +
          </button>
        </div>
      </header>

      {/* World selector pills */}
      <div className="world-pills">
        {WORLDS.map(w => (
          <button
            key={w.id}
            className={`world-pill${world === w.id ? ' active' : ''}`}
            style={world === w.id ? { '--pill-color': w.color } : {}}
            onClick={() => setWorld(w.id)}
          >
            {w.label}
          </button>
        ))}
      </div>

      {/* Progress bar */}
      <div className="studio-progress-bar">
        <div
          className="studio-progress-fill"
          style={{ width: coherence != null ? `${coherence}%` : '0%', background: activeWorld.color }}
        />
      </div>

      {/* Masonry gallery */}
      <div className="studio-gallery">
        {images.length === 0 ? (
          <div className="studio-empty">
            <p>Tu serie está vacía</p>
            <span>Subí imágenes para comenzar</span>
          </div>
        ) : (
          <div className="studio-masonry">
            {images.map((img, idx) => (
              <div
                key={img.id}
                className={`studio-card${selectedId === img.id ? ' selected' : ''}`}
                onClick={() => setSelectedId(img.id === selectedId ? null : img.id)}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <img src={img.src} alt={img.name} loading="lazy" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Side panel */}
      {selectedId && (
        <aside className="studio-panel">
          <div className="studio-panel-header">
            <span className="studio-panel-title">Análisis</span>
            <button className="studio-panel-close" onClick={() => setSelectedId(null)}>×</button>
          </div>
          <div className="studio-panel-content">
            <div className="panel-metric">
              <span className="metric-label">Escala</span>
              <span className="metric-value">{selectedSemantic?.shot_scale ?? '—'}</span>
            </div>
            <div className="panel-metric">
              <span className="metric-label">Atmósfera</span>
              <span className="metric-value">{selectedSemantic?.atmosphere ?? '—'}</span>
            </div>
            <div className="panel-metric">
              <span className="metric-label">Luz</span>
              <span className="metric-value">{selectedSemantic?.light_quality ?? '—'}</span>
            </div>
            {selectedSemantic?.dominant_colors?.length > 0 && (
              <div className="panel-colors">
                <span className="metric-label">Colores</span>
                <div className="color-palette">
                  {selectedSemantic.dominant_colors.slice(0, 4).map((c, i) => (
                    <span key={i} className="color-swatch" style={{ background: c }} title={c} />
                  ))}
                </div>
              </div>
            )}
            {selectedSemantic?.composition_notes && (
              <div className="panel-metric">
                <span className="metric-label">Composición</span>
                <span className="metric-value metric-value--small">{selectedSemantic.composition_notes}</span>
              </div>
            )}
            <div className="panel-metric">
              <span className="metric-label">Mundo</span>
              <span className="metric-value" style={{ color: activeWorld.color }}>{activeWorld.label}</span>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}
