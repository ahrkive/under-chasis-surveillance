import { useState, useEffect } from 'react'

/**
 * Inspection history table with pagination.
 * Shows past inspections with decision badges and timestamps.
 */
export default function InspectionHistory() {
  const [inspections, setInspections] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const pageSize = 15

  const fetchHistory = async (p = 1) => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(
        `/api/inspections?page=${p}&page_size=${pageSize}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      if (res.ok) {
        const data = await res.json()
        setInspections(data.inspections)
        setTotal(data.total)
      }
    } catch (e) {
      console.error('Failed to fetch history:', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchHistory(page)
  }, [page])

  const totalPages = Math.ceil(total / pageSize)

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="glass-card" style={{ overflow: 'hidden' }}>
      {/* Header */}
      <div
        style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1rem' }}>📋</span>
          <h2
            style={{
              fontSize: '0.9rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
            }}
          >
            Inspection History
          </h2>
        </div>
        <span
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
          }}
        >
          {total} total
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <div className="skeleton" style={{ width: '100%', height: 200 }} />
          </div>
        ) : inspections.length === 0 ? (
          <div
            style={{
              padding: '3rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
            }}
          >
            No inspections yet.
          </div>
        ) : (
          <table className="inspection-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Bot</th>
                <th>Decision</th>
                <th>AI Prediction</th>
                <th>Confidence</th>
                <th>Captured</th>
                <th>Decided</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((insp) => (
                <tr key={insp.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {insp.id.slice(0, 8)}
                  </td>
                  <td>{insp.bot_id}</td>
                  <td>
                    <span className={`badge badge-${insp.decision}`}>
                      {insp.decision}
                    </span>
                  </td>
                  <td style={{ color: insp.model_prediction === 'ok' ? '#34d399' : insp.model_prediction === 'suspicious' ? '#f87171' : 'var(--text-muted)' }}>
                    {insp.model_prediction || '—'}
                  </td>
                  <td>
                    {insp.model_confidence !== null
                      ? `${Math.round(insp.model_confidence * 100)}%`
                      : '—'}
                  </td>
                  <td>{formatDate(insp.captured_at)}</td>
                  <td>{formatDate(insp.decided_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            padding: '0.75rem 1.5rem',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
          }}
        >
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              padding: '0.3rem 0.8rem',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 6,
              color: page === 1 ? 'var(--text-muted)' : 'var(--text-secondary)',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-family)',
            }}
          >
            ← Prev
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={{
              padding: '0.3rem 0.8rem',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 6,
              color: page === totalPages ? 'var(--text-muted)' : 'var(--text-secondary)',
              cursor: page === totalPages ? 'not-allowed' : 'pointer',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-family)',
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
