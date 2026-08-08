/**
 * Status banner that shows after a guard makes a decision.
 * Green for approved, red for rejected, indigo for pending.
 */
export default function StatusBanner({ status, message }) {
  if (!status) return null

  const bannerClass = `status-banner ${status} animate-fade-in`

  const icons = {
    approved: '✅',
    rejected: '🚫',
    pending: '⏳',
  }

  return (
    <div className={bannerClass} style={{ marginBottom: '1rem' }}>
      <span style={{ marginRight: '0.5rem', fontSize: '1.2rem' }}>
        {icons[status] || '📋'}
      </span>
      {message || `Inspection ${status}`}
    </div>
  )
}
