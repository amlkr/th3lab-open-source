import { useState, useRef, useEffect } from 'react'

export default function ChatPanel({ chatHistory, onSend, chatLoading }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatLoading])

  const handleSend = () => {
    if (!input.trim() || chatLoading) return
    onSend(input.trim())
    setInput('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">OpenClaw</span>
        <span className="chat-subtitle">AI cinematographic assistant</span>
      </div>

      <div className="chat-messages">
        {chatHistory.length === 0 && (
          <div className="chat-empty">
            <p>Upload images and ask OpenClaw about your visual language.</p>
          </div>
        )}

        {chatHistory.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <span className="msg-role">
              {msg.role === 'user' ? 'you' : msg.role === 'assistant' ? 'openclaw' : 'análisis'}
            </span>
            <p className="msg-content">{msg.content}</p>
          </div>
        ))}

        {chatLoading && (
          <div className="chat-msg assistant">
            <span className="msg-role">openclaw</span>
            <p className="msg-content typing">···</p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about your visual language..."
          rows={2}
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={chatLoading || !input.trim()}
        >
          send
        </button>
      </div>
    </div>
  )
}
