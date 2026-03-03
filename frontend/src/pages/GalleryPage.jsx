import { useState, useEffect } from 'react'
import ScaleBadge from '../components/ScaleBadge'
import { useAuth } from '../context/AuthContext'

import { API_BASE } from '../config/api'

function uploadUrl(localPath) {
  if (!localPath) return null
  const basename = localPath.split('/').pop()
  return `${API_BASE}/static/uploads/${basename}`
}

export default function GalleryPage() {
  const { user }  = useAuth()
  const [images, setImages]   = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const userParam = user?.id ? `&user_id=${user.id}` : ''
        const listRes = await fetch(
          `${API_BASE}/api/jobs/?status=completed&job_type=images&limit=20${userParam}`
        )
        const listData = await listRes.json()
        const jobs = listData.jobs ?? []

        if (!jobs.length) { setLoading(false); return }

        const details = await Promise.all(
          jobs.map(j =>
            fetch(`${API_BASE}/api/jobs/${j.job_id}`)
              .then(r => r.json())
              .catch(() => null)
          )
        )

        const allImages = []
        for (const job of details) {
          if (!job?.result || !job.input_data?.filenames) continue
          const filenames = job.input_data.filenames ?? []
          const paths     = job.input_data.image_paths ?? []
          const semantics = job.result.semantic_analysis ?? []
          filenames.forEach((name, i) => {
            const url = uploadUrl(paths[i])
            if (url) {
              allImages.push({
                id:         `${job.job_id}-${i}`,
                name,
                url,
                shot_scale:  semantics[i]?.shot_scale ?? null,
                atmosphere:  semantics[i]?.atmosphere ?? null,
                light:       semantics[i]?.light_quality ?? null,
              })
            }
          })
        }
        setImages(allImages)
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user?.id])

  return (
    <div className="gallery-page">
      <div className="page-header">
        <h1 className="page-title">Galería</h1>
        {images.length > 0 && (
          <span className="page-count">{images.length} imágenes</span>
        )}
      </div>

      {loading ? (
        <div className="page-loading">
          <span className="page-loading-dot">◈</span>
          <span>cargando...</span>
        </div>
      ) : images.length === 0 ? (
        <div className="page-empty">
          <div className="empty-icon">◻</div>
          <p>Sin imágenes todavía</p>
          <span>Subí imágenes en un proyecto para verlas acá</span>
        </div>
      ) : (
        <div className="gallery-scroll">
          <div className="masonry-grid">
            {[0, 1, 2].map(col => (
              <div key={col} className="masonry-col">
                {images.filter((_, i) => i % 3 === col).map(img => (
                  <div
                    key={img.id}
                    className={`masonry-item${selected?.id === img.id ? ' selected' : ''}`}
                    onClick={() => setSelected(selected?.id === img.id ? null : img)}
                  >
                    <img src={img.url} alt={img.name} loading="lazy" />
                    <div className="masonry-overlay">
                      {img.shot_scale && (
                        <ScaleBadge scale={img.shot_scale} />
                      )}
                      <span className="masonry-name">{img.name}</span>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {selected && (
            <div className="gallery-detail-panel">
              <div className="gallery-detail-header">
                <span className="gallery-detail-title">{selected.name}</span>
                <button className="gallery-detail-close" onClick={() => setSelected(null)}>×</button>
              </div>
              <img src={selected.url} alt={selected.name} className="gallery-detail-img" />
              <div className="gallery-detail-meta">
                {selected.shot_scale && (
                  <div className="gallery-meta-row">
                    <span className="gallery-meta-label">Escala</span>
                    <ScaleBadge scale={selected.shot_scale} />
                  </div>
                )}
                {selected.atmosphere && (
                  <div className="gallery-meta-row">
                    <span className="gallery-meta-label">Atmósfera</span>
                    <span className="gallery-meta-value">{selected.atmosphere}</span>
                  </div>
                )}
                {selected.light && (
                  <div className="gallery-meta-row">
                    <span className="gallery-meta-label">Luz</span>
                    <span className="gallery-meta-value">{selected.light}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
