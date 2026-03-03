import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import ThumbnailCard from '../components/ThumbnailCard'
import AnalysisBar from '../components/AnalysisBar'
import ChatPanel from '../components/ChatPanel'
import { useAuth } from '../context/AuthContext'

import { API_BASE } from '../config/api'

function uploadUrl(localPath) {
  if (!localPath) return null
  const basename = localPath.split('/').pop()
  return `${API_BASE}/static/uploads/${basename}`
}

function imagesFromJob(job) {
  if (!job?.result) return []
  if (job.job_type === 'video' && job.result.shots) {
    return job.result.shots.map(s => ({
      id:              `shot-${s.shot_number}`,
      name:            `${s.shot_scale} · ${s.start_time.toFixed(1)}s · ${s.camera_movement}`,
      url:             `${API_BASE}${s.thumbnail_url}`,
      shot_scale:      s.shot_scale,
      camera_movement: s.camera_movement,
      brightness:      s.brightness,
      start_time:      s.start_time,
      duration:        s.duration,
    }))
  }
  if (job.input_data?.filenames) {
    const filenames  = job.input_data.filenames ?? []
    const paths      = job.input_data.image_paths ?? []
    const semantics  = job.result?.semantic_analysis ?? []
    return filenames.map((name, i) => ({
      id:         `${job.job_id}-${i}`,
      name,
      url:        uploadUrl(paths[i]) ?? '',
      shot_scale: semantics[i]?.shot_scale ?? null,
    }))
  }
  return []
}

// ── Biblioteca tab ────────────────────────────────────────────
function BibliotecaTab({ projectId, userId }) {
  const [files, setFiles]         = useState([])
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    if (!userId) return
    fetch(`${API_BASE}/api/library/?user_id=${userId}`)
      .then(r => r.json())
      .then(data => setFiles(data.items ?? []))
      .catch(() => {})
  }, [userId])

  const handleLibUpload = async (e) => {
    const picked = Array.from(e.target.files)
    if (!picked.length) return
    e.target.value = ''
    setUploading(true)
    const newItems = []
    for (const f of picked) {
      try {
        const form = new FormData()
        form.append('user_id', userId ?? projectId)
        form.append('file', f)
        const res = await fetch(`${API_BASE}/api/library/upload`, { method: 'POST', body: form })
        if (res.ok) newItems.push(await res.json())
      } catch { /* continue */ }
    }
    setFiles(prev => [...newItems, ...prev])
    setUploading(false)
  }

  const fileIcon = (type) => type === 'pdf' ? '⬡' : type === 'epub' ? '◧' : '◻'
  const sizeLabel = (b) => b
    ? (b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`)
    : ''

  return (
    <div className="biblioteca">
      <div className="biblioteca-header">
        <span className="biblioteca-title">Biblioteca</span>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.epub"
          onChange={handleLibUpload}
          style={{ display: 'none' }}
        />
        <button
          className="biblioteca-add-btn"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'subiendo...' : '+ agregar'}
        </button>
      </div>
      {files.length === 0 ? (
        <div className="biblioteca-empty">
          <span>PDFs, textos, EPUBs — teoría del proyecto</span>
        </div>
      ) : (
        <div className="biblioteca-list">
          {files.map((f, i) => (
            <div key={f.id ?? i} className="biblioteca-file">
              <span className="biblioteca-file-icon">{fileIcon(f.file_type)}</span>
              <span className="biblioteca-file-name" title={f.name}>{f.name}</span>
              <span className="biblioteca-file-size">{sizeLabel(f.file_size_bytes)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Analysis tab ──────────────────────────────────────────────
function AnalysisTab({ results, isVideoJob }) {
  if (!results) {
    return (
      <div className="tab-empty">
        <div className="empty-icon">◻</div>
        <p>Sin análisis todavía</p>
        <span>Subí imágenes o video en la pestaña Galería</span>
      </div>
    )
  }

  const coherence = results.coherence?.score
  const semantic  = results.semantic_analysis ?? []
  const scales    = results.scale_distribution ?? {}

  return (
    <div className="analysis-tab">
      {coherence != null && (
        <div className="analysis-section">
          <div className="analysis-section-title">Coherencia CLIP</div>
          <div className="analysis-coherence-score">{coherence.toFixed(1)}</div>
        </div>
      )}

      {Object.keys(scales).length > 0 && (
        <div className="analysis-section">
          <div className="analysis-section-title">Distribución de escalas</div>
          <div className="analysis-scale-bars">
            {Object.entries(scales).map(([k, v]) => (
              <div key={k} className="analysis-scale-row">
                <span className="analysis-scale-label">{k}</span>
                <div className="analysis-scale-track">
                  <div className="analysis-scale-fill" style={{ width: `${v}%` }} />
                </div>
                <span className="analysis-scale-pct">{v}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {semantic.length > 0 && (
        <div className="analysis-section">
          <div className="analysis-section-title">Análisis semántico ({semantic.length} imágenes)</div>
          <div className="analysis-semantic-list">
            {semantic.slice(0, 8).map((item, i) => (
              <div key={i} className="analysis-semantic-item">
                <span className="analysis-semantic-idx">#{i + 1}</span>
                <div className="analysis-semantic-tags">
                  {item.shot_scale    && <span className="report-tag">{item.shot_scale}</span>}
                  {item.atmosphere    && <span className="report-tag">{item.atmosphere}</span>}
                  {item.light_quality && <span className="report-tag">{item.light_quality}</span>}
                </div>
                {item.composition_notes && (
                  <div className="analysis-semantic-note">{item.composition_notes}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {results.report && (
        <div className="analysis-section">
          <div className="analysis-section-title">Reporte narrativo</div>
          <div className="analysis-report-text">{results.report}</div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────
const TABS = ['gallery', 'analysis', 'library', 'chat']

export default function ProjectDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const userId = user?.id ?? null
  const [activeTab, setActiveTab] = useState('gallery')

  const [project, setProject]         = useState(null)
  const [images, setImages]           = useState([])
  const [selected, setSelected]       = useState(null)
  const [uploading, setUploading]     = useState(false)
  const [jobId, setJobId]             = useState(null)
  const [jobStatus, setJobStatus]     = useState(null)
  const [jobProgress, setJobProgress] = useState(0)
  const [isVideoJob, setIsVideoJob]   = useState(false)
  const [videoStage, setVideoStage]   = useState('extracting')
  const [results, setResults]         = useState(null)
  const [chatHistory, setChatHistory] = useState([])
  const [chatLoading, setChatLoading] = useState(false)

  const fileInputRef    = useRef(null)
  const pollRef         = useRef(null)
  const videoStageTimer = useRef(null)

  useEffect(() => {
    if (!id) return
    fetch(`${API_BASE}/api/projects/${id}`)
      .then(r => r.json())
      .then(setProject)
      .catch(() => setProject({ id, name: `Proyecto ${id.slice(0, 8)}` }))

    fetch(`${API_BASE}/api/jobs/?project_id=${id}&status=completed&limit=1${userId ? `&user_id=${userId}` : ''}`)
      .then(r => r.json())
      .then(async data => {
        const jobs = data.jobs ?? []
        if (!jobs.length) return
        const jobRes = await fetch(`${API_BASE}/api/jobs/${jobs[0].job_id}`)
        const job    = await jobRes.json()
        if (!job.result) return
        setResults(job.result)
        setIsVideoJob(job.job_type === 'video')
        setImages(imagesFromJob(job))
      })
      .catch(() => {})
  }, [id])

  const applyCompletedJob = useCallback((jobResult, jobType) => {
    setResults(jobResult)
    if (jobType === 'video') {
      const shots = jobResult.shots || []
      setImages(shots.map(s => ({
        id:              `shot-${s.shot_number}`,
        name:            `${s.shot_scale} · ${s.start_time.toFixed(1)}s · ${s.camera_movement}`,
        url:             `${API_BASE}${s.thumbnail_url}`,
        shot_scale:      s.shot_scale,
        camera_movement: s.camera_movement,
        brightness:      s.brightness,
        start_time:      s.start_time,
        duration:        s.duration,
      })))
      setSelected(null)
      const n      = shots.length
      const scales = jobResult.scale_distribution
        ? Object.entries(jobResult.scale_distribution).map(([k, v]) => `${k} ${v}%`).join(', ')
        : '—'
      const autoMsg = `Acabo de analizar este video. ${n} planos detectados. Escalas: ${scales}. Movimiento dominante: ${jobResult.dominant_movement ?? '—'}. ¿Qué ves en la gramática visual de esta secuencia?`
      sendAnalysisToChat(autoMsg, jobResult)
    } else {
      if (Array.isArray(jobResult.semantic_analysis)) {
        setImages(prev =>
          prev.map((img, idx) => {
            const r = jobResult.semantic_analysis[idx]
            return r ? { ...img, shot_scale: r.shot_scale ?? null } : img
          })
        )
      }
      const semanticData = jobResult.semantic_analysis || []
      const n            = semanticData.length || (jobResult.image_count ?? 0)
      const coherence    = jobResult.coherence?.score != null ? jobResult.coherence.score.toFixed(1) : '—'
      const imageList    = semanticData.map((img, idx) => {
        const fname  = images[idx]?.name ?? `Imagen ${idx + 1}`
        const colors = Array.isArray(img.dominant_colors) ? img.dominant_colors.join('/') : '—'
        return `${fname}: escala=${img.shot_scale ?? '—'}, atmósfera=${img.atmosphere ?? '—'}, referencia=${img.cinematic_reference ?? '—'}, tensión=${img.emotional_tension ?? '—'}, colores=${colors}`
      }).join('. ')
      const contextMsg = `Contexto del análisis: Se analizaron ${n} imágenes. ${imageList ? `Resultados: ${imageList}.` : ''} Coherencia CLIP: ${coherence}.`
      setChatHistory([{ role: 'system', content: contextMsg }])
    }
  }, [images])

  useEffect(() => {
    if (!jobId) return
    pollRef.current = setInterval(async () => {
      try {
        const res  = await fetch(`${API_BASE}/api/jobs/${jobId}`)
        const data = await res.json()
        setJobStatus(data.status)
        if (data.status === 'completed') {
          clearInterval(pollRef.current)
          clearTimeout(videoStageTimer.current)
          applyCompletedJob(data.result ?? {}, isVideoJob ? 'video' : 'images')
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current)
        }
      } catch {
        clearInterval(pollRef.current)
        setJobStatus('error')
      }
    }, 3000)
    return () => clearInterval(pollRef.current)
  }, [jobId])

  const sendAnalysisToChat = async (message, jobResult) => {
    const next = [{ role: 'user', content: message }]
    setChatHistory(next)
    setChatLoading(true)
    try {
      const res  = await fetch(`${API_BASE}/api/chat/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message, history: [], context: jobResult }),
      })
      const data = await res.json()
      setChatHistory([...next, { role: 'assistant', content: data.response }])
    } catch {
      setChatHistory([...next, { role: 'assistant', content: '[error conectando con OpenClaw]' }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleChat = async (message) => {
    const next = [...chatHistory, { role: 'user', content: message }]
    setChatHistory(next)
    setChatLoading(true)
    try {
      const res  = await fetch(`${API_BASE}/api/chat/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message, history: chatHistory, context: results }),
      })
      const data = await res.json()
      setChatHistory([...next, { role: 'assistant', content: data.response }])
    } catch {
      setChatHistory([...next, { role: 'assistant', content: '[error connecting to OpenClaw]' }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleUpload = async (files) => {
    if (!files || files.length === 0) return
    const firstFile = files[0]
    const isVideo   = firstFile.type.startsWith('video/')
      || /\.(mp4|mov|avi)$/i.test(firstFile.name)

    setIsVideoJob(isVideo)
    setUploading(true)
    setJobStatus('uploading')
    setResults(null)
    setSelected(null)
    setChatHistory([])
    setActiveTab('gallery')

    if (isVideo) {
      setImages([])
      clearTimeout(videoStageTimer.current)
      setVideoStage('extracting')
      videoStageTimer.current = setTimeout(() => setVideoStage('analyzing'), 8000)
    } else {
      setImages(Array.from(files).map(f => ({
        id:         `${f.name}-${Date.now()}-${Math.random()}`,
        name:       f.name,
        url:        URL.createObjectURL(f),
        shot_scale: null,
      })))
    }

    try {
      const form = new FormData()
      if (id)     form.append('project_id', id)
      if (userId) form.append('user_id', userId)
      if (isVideo) {
        form.append('file', firstFile)
        const res  = await fetch(`${API_BASE}/api/analysis/video`, { method: 'POST', body: form })
        if (!res.ok) throw new Error(res.status)
        const data = await res.json()
        setJobId(data.job_id)
      } else {
        Array.from(files).forEach(f => form.append('files', f))
        const res  = await fetch(`${API_BASE}/api/analysis/images`, { method: 'POST', body: form })
        if (!res.ok) throw new Error(res.status)
        const data = await res.json()
        setJobId(data.job_id)
      }
      setJobStatus('processing')
    } catch {
      setJobStatus('error')
    } finally {
      setUploading(false)
    }
  }

  const handleFileChange = (e) => { handleUpload(e.target.files); e.target.value = '' }
  const handleDrop       = (e)  => { e.preventDefault(); handleUpload(e.dataTransfer.files) }

  const statusLabel = jobStatus === 'processing' && isVideoJob
    ? (videoStage === 'extracting' ? 'extrayendo frames...' : 'analizando frames...')
    : ({
        uploading:  'subiendo...',
        processing: 'analizando...',
        completed:  'análisis completo',
        failed:     'análisis fallido',
        error:      'error de conexión',
      }[jobStatus] ?? '')

  const TAB_LABELS = { gallery: 'Galería', analysis: 'Análisis', library: 'Biblioteca', chat: 'Chat' }

  return (
    <div className="project-detail">
      {/* Top bar */}
      <header className="detail-header">
        <div className="detail-header-left">
          <Link to="/projects" className="detail-back">← proyectos</Link>
          <span className="detail-project-name">{project?.name ?? '...'}</span>
          {project?.module && (
            <span className="detail-module-badge">{project.module}</span>
          )}
        </div>
        <div className="header-status">
          {statusLabel && (
            <span className={`status-pill status-${jobStatus}`}>{statusLabel}</span>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,.mov,.avi"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || jobStatus === 'processing'}
          >
            + subir
          </button>
        </div>
      </header>

      {/* Tab nav */}
      <div className="page-tabs">
        {TABS.map(tab => (
          <button
            key={tab}
            className={`tab-btn${activeTab === tab ? ' active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="tab-content">
        {activeTab === 'gallery' && (
          <section
            className="gallery-panel"
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
          >
            {images.length === 0 ? (
              <div className="gallery-empty">
                {isVideoJob && jobStatus === 'processing' ? (
                  <>
                    <div className="empty-icon video-processing">◈</div>
                    <p>{videoStage === 'extracting' ? 'Extrayendo frames...' : 'Analizando frames...'}</p>
                    <span>Procesando video</span>
                  </>
                ) : (
                  <>
                    <div className="empty-icon">◻</div>
                    <p>Subí imágenes o video</p>
                    <span>JPG · PNG · WebP · MP4 · MOV</span>
                  </>
                )}
              </div>
            ) : (
              <div className="image-grid">
                {images.map(img => (
                  <ThumbnailCard
                    key={img.id}
                    image={img}
                    selected={selected?.id === img.id}
                    onClick={setSelected}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === 'analysis' && (
          <div className="tab-scroll">
            <AnalysisTab results={results} isVideoJob={isVideoJob} />
          </div>
        )}

        {activeTab === 'library' && (
          <div className="tab-scroll">
            <BibliotecaTab projectId={id} userId={userId} />
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="tab-chat">
            <ChatPanel
              chatHistory={chatHistory}
              onSend={handleChat}
              chatLoading={chatLoading}
            />
          </div>
        )}
      </div>

      {/* Analysis bar — only in gallery tab */}
      {activeTab === 'gallery' && <AnalysisBar results={results} />}
    </div>
  )
}
