import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

interface CopyButtonProps {
  value: string
  size?: number
}

export function CopyButton({ value, size = 16 }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      // Clipboard API unavailable (non-secure context) — fall back
      const ta = document.createElement('textarea')
      ta.value = value
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <span className="tip">
      <button
        onClick={copy}
        aria-label="Copy to clipboard"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: copied ? 'var(--success)' : 'var(--text-3)',
          display: 'flex',
          alignItems: 'center',
          padding: 4,
          borderRadius: 'var(--r-sm)',
          transition: 'color var(--t-fast)',
        }}
        onMouseEnter={(e) => {
          if (!copied) e.currentTarget.style.color = 'var(--text-1)'
        }}
        onMouseLeave={(e) => {
          if (!copied) e.currentTarget.style.color = 'var(--text-3)'
        }}
      >
        {copied ? <Check size={size} /> : <Copy size={size} />}
      </button>
      {copied && <span className="tip-content" style={{ opacity: 1 }}>Copied!</span>}
    </span>
  )
}
