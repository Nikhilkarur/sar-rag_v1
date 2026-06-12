
export function CodeBlock({ code, language = 'json', maxHeight }: { code: string; language?: string; maxHeight?: number }) {
  // Ultra-simple syntax highlighter for JSON
  const highlightJSON = (jsonString: string) => {
    return jsonString
      .replace(/(".*?"|null|true|false|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'text-ink-3'; // null/bool
        if (/^"/.test(match)) {
          if (/:$/.test(match)) cls = 'text-electric-text'; // keys
          else cls = 'text-risk-low'; // strings
        } else if (/true|false/.test(match)) {
          cls = 'text-ink-3'; // booleans
        } else if (/null/.test(match)) {
          cls = 'text-ink-3'; // null
        } else {
          cls = 'text-risk-med'; // numbers
        }
        return `<span class="${cls}">${match}</span>`;
      })
      .replace(/"(.*?)"\s*:/g, '<span class="text-electric-text">"$1"</span>:'); // Fix keys
  };

  const highlighted = language === 'json' ? highlightJSON(code) : code;

  return (
    <pre
      className="border border-border-dim rounded-md p-3.5 overflow-x-auto text-[12px] font-mono leading-relaxed whitespace-pre-wrap"
      style={{ background: 'var(--bg-elevated)', ...(maxHeight ? { maxHeight, overflowY: 'auto' } : null) }}
    >
      <code dangerouslySetInnerHTML={{ __html: highlighted }} />
    </pre>
  );
}
