import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileText, Trash2, UploadCloud } from 'lucide-react'
import { usePolicyInfo } from '../../../hooks/useTenant'
import { uploadPolicy, deletePolicy } from '../../../api/tenant'
import { Button } from '../../../components/ui/Button'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'

export function Policy() {
  const { data: info, isLoading } = usePolicyInfo()
  const { toast } = useToast()
  const qc = useQueryClient()

  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [lastChunks, setLastChunks] = useState<number | null>(null)

  const handlePick = () => inputRef.current?.click()

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast('error', 'Unsupported file', 'Only PDF policy documents are supported.')
      return
    }
    setUploading(true)
    setLastChunks(null)
    try {
      const result = await uploadPolicy(file)
      setLastChunks(result.chunks_indexed)
      qc.invalidateQueries({ queryKey: ['policy-info'] })
      toast('success', 'Policy indexed',
        `${result.original_filename} — ${result.chunks_indexed} chunks embedded into your knowledge base.`)
    } catch {
      toast('error', 'Upload failed', 'The policy could not be indexed. Check the file and try again.')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deletePolicy()
      setLastChunks(null)
      qc.invalidateQueries({ queryKey: ['policy-info'] })
      toast('success', 'Policy removed', 'The policy and its indexed chunks were deleted.')
    } catch {
      toast('error', 'Delete failed', 'The policy could not be removed.')
    } finally {
      setDeleting(false)
    }
  }

  const present = info?.policy_present
  const chunks = lastChunks ?? info?.chunks_indexed ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      <div className="card anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 4 }}>
          AML Policy Document
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 24 }}>
          Upload your institution's AML/CFT policy (PDF). It is chunked and embedded into your
          private knowledge base, then cited by the SAR narratives generated for your alerts.
        </p>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Skeleton height={24} width={280} />
            <Skeleton height={92} />
          </div>
        ) : (
          <>
            {/* Current status */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 14px',
                borderRadius: 'var(--r-md)',
                background: present ? 'var(--success-subtle)' : 'var(--bg-overlay)',
                border: `1px solid ${present ? 'var(--success)' : 'var(--border-subtle)'}`,
                marginBottom: 20,
              }}
            >
              {present ? (
                <CheckCircle2 size={18} color="var(--success)" />
              ) : (
                <FileText size={18} color="var(--text-3)" />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 500 }}>
                  {present ? 'Policy active' : 'No policy uploaded yet'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
                  {present
                    ? `${chunks} chunk${chunks === 1 ? '' : 's'} indexed and searchable.`
                    : 'SARs will fall back to general PMLA/SEBI guidance until a policy is indexed.'}
                </div>
              </div>
              {present && (
                <Button variant="ghost" size="sm" icon={<Trash2 size={14} />} onClick={handleDelete} loading={deleting}>
                  Remove
                </Button>
              )}
            </div>

            {/* Dropzone / picker */}
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <button
              type="button"
              onClick={handlePick}
              disabled={uploading}
              className="anim-fade-in"
              style={{
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                padding: '28px 16px',
                borderRadius: 'var(--r-md)',
                border: '1px dashed var(--border-strong)',
                background: 'var(--bg-elevated)',
                cursor: uploading ? 'wait' : 'pointer',
                color: 'var(--text-2)',
              }}
            >
              <UploadCloud size={22} color="var(--text-3)" />
              <span style={{ fontSize: 14, fontWeight: 500 }}>
                {uploading ? 'Indexing policy…' : present ? 'Replace policy PDF' : 'Upload policy PDF'}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-4)' }}>
                PDF only · click to choose a file
              </span>
            </button>

            {lastChunks != null && (
              <p
                className="anim-fade-in-up"
                style={{ fontSize: 12, color: 'var(--success)', marginTop: 12, display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <CheckCircle2 size={14} /> Indexed {lastChunks} chunk{lastChunks === 1 ? '' : 's'} into your knowledge base.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
