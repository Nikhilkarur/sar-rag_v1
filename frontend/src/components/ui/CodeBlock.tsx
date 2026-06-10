import React, { useMemo } from 'react'
import { CopyButton } from './CopyButton'

interface CodeBlockProps {
  code: string
  language?: 'json' | 'bash' | 'python' | 'javascript'
  maxHeight?: number
}

/** Regex-based syntax highlighting, no library. */
function highlightJSON(code: string): React.ReactNode[] {
  const tokenRe =
    /("(?:\\.|[^"\\])*")(\s*:)?|(-?\d+\.?\d*(?:[eE][+-]?\d+)?)|(\btrue\b|\bfalse\b|\bnull\b)|([{}[\],])/g
  const nodes: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  let key = 0
  while ((m = tokenRe.exec(code)) !== null) {
    if (m.index > last) nodes.push(<span key={key++}>{code.slice(last, m.index)}</span>)
    if (m[1] !== undefined) {
      if (m[2] !== undefined) {
        nodes.push(
          <span key={key++} style={{ color: 'var(--accent-text)' }}>
            {m[1]}
          </span>,
        )
        nodes.push(
          <span key={key++} style={{ color: 'var(--text-3)' }}>
            {m[2]}
          </span>,
        )
      } else {
        nodes.push(
          <span key={key++} style={{ color: 'var(--success)' }}>
            {m[1]}
          </span>,
        )
      }
    } else if (m[3] !== undefined) {
      nodes.push(
        <span key={key++} style={{ color: 'var(--warning)' }}>
          {m[3]}
        </span>,
      )
    } else if (m[4] !== undefined) {
      nodes.push(
        <span key={key++} style={{ color: 'var(--info)' }}>
          {m[4]}
        </span>,
      )
    } else if (m[5] !== undefined) {
      nodes.push(
        <span key={key++} style={{ color: 'var(--text-3)' }}>
          {m[5]}
        </span>,
      )
    }
    last = tokenRe.lastIndex
  }
  if (last < code.length) nodes.push(<span key={key++}>{code.slice(last)}</span>)
  return nodes
}

function highlightCode(code: string, language: string): React.ReactNode[] {
  if (language === 'json') return highlightJSON(code)
  // Light-touch highlighting for shell/python/js snippets
  return code.split('\n').map((line, i) => {
    const isComment = line.trimStart().startsWith('#') || line.trimStart().startsWith('//')
    return (
      <span key={i} style={{ color: isComment ? 'var(--text-4)' : undefined, display: 'block' }}>
        {line
          .split(/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g)
          .map((part, j) =>
            part.startsWith('"') || part.startsWith("'") ? (
              <span key={j} style={{ color: 'var(--success)' }}>
                {part}
              </span>
            ) : (
              <span key={j}>{part}</span>
            ),
          )}
      </span>
    )
  })
}

export function CodeBlock({ code, language = 'json', maxHeight }: CodeBlockProps) {
  const highlighted = useMemo(() => highlightCode(code, language), [code, language])
  return (
    <div style={{ position: 'relative' }}>
      <pre
        style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-md)',
          padding: 16,
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          lineHeight: 1.7,
          overflowX: 'auto',
          color: 'var(--text-1)',
          maxHeight,
          overflowY: maxHeight ? 'auto' : undefined,
        }}
      >
        {highlighted}
      </pre>
      <div style={{ position: 'absolute', top: 8, right: 8 }}>
        <CopyButton value={code} size={14} />
      </div>
    </div>
  )
}
