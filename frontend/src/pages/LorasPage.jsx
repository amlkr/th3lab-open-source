const WORLDS = [
  {
    id: 'amniotic',
    name: 'amniotic',
    desc: 'Espacios líquidos y estados limínales. Texturas orgánicas, luz difusa, bordes disueltos.',
    icon: '◈',
    status: 'En desarrollo',
    tags: ['texturas fluidas', 'luz etérea', 'soft focus'],
  },
  {
    id: 'cine_lentitud',
    name: 'cine_lentitud',
    desc: 'La gramática del tiempo detenido. Planos largos, contemplación, movimiento mínimo.',
    icon: '⬡',
    status: 'En desarrollo',
    tags: ['slow cinema', 'plano secuencia', 'contemplativo'],
  },
  {
    id: 'cuerpo_politico',
    name: 'cuerpo_político',
    desc: 'El cuerpo como campo de tensión social. Contrastes duros, encuadres precisos, mirada directa.',
    icon: '◧',
    status: 'En desarrollo',
    tags: ['documental', 'retratos', 'contraste alto'],
  },
]

export default function LorasPage() {
  return (
    <div className="loras-page">
      <div className="page-header">
        <h1 className="page-title">LoRAs</h1>
        <span className="page-subtitle">Modelos visuales por mundo</span>
      </div>

      <div className="loras-grid">
        {WORLDS.map(w => (
          <div key={w.id} className={`lora-card world-${w.id}`}>
            <div className="lora-card-art">
              <span className="lora-world-icon">{w.icon}</span>
              <div className="lora-geo" />
            </div>

            <div className="lora-card-body">
              <div className="lora-card-header">
                <span className="lora-world-name">{w.name}</span>
                <span className="lora-status-badge">{w.status}</span>
              </div>

              <p className="lora-card-desc">{w.desc}</p>

              <div className="lora-tags">
                {w.tags.map(t => (
                  <span key={t} className="lora-tag">{t}</span>
                ))}
              </div>

              <button className="lora-train-btn" disabled>
                Entrenar LoRA
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
