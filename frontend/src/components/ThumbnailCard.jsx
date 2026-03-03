import ScaleBadge from './ScaleBadge'

export default function ThumbnailCard({ image, selected, onClick }) {
  return (
    <div
      className={`thumb-card${selected ? ' thumb-selected' : ''}`}
      onClick={() => onClick(image)}
    >
      <img src={image.url} alt={image.name} loading="lazy" />
      <div className="thumb-overlay">
        <span className="thumb-overlay-name" title={image.name}>{image.name}</span>
        <ScaleBadge scale={image.shot_scale} />
      </div>
    </div>
  )
}
