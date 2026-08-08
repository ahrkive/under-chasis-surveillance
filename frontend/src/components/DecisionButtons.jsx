import { useState } from 'react'

/**
 * Large Approve (✓) and Reject (✗) buttons.
 * The guard's primary interaction for making inspection decisions.
 */
export default function DecisionButtons({ inspectionId, onDecision, disabled }) {
  const [submitting, setSubmitting] = useState(null) // 'approved' | 'rejected' | null

  const handleDecision = async (decision) => {
    if (!inspectionId || disabled || submitting) return

    setSubmitting(decision)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/inspections/${inspectionId}/decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ decision }),
      })

      if (!res.ok) {
        const err = await res.json()
        alert(`Decision failed: ${err.detail || 'Unknown error'}`)
        return
      }

      onDecision?.(decision)
    } catch (e) {
      alert(`Network error: ${e.message}`)
    } finally {
      setSubmitting(null)
    }
  }

  const isDisabled = !inspectionId || disabled

  return (
    <div
      style={{
        display: 'flex',
        gap: '1.5rem',
        justifyContent: 'center',
        flexWrap: 'wrap',
        padding: '1rem 0',
      }}
    >
      {/* APPROVE BUTTON */}
      <button
        id="btn-approve"
        className={`btn-approve ${submitting === 'approved' ? 'animate-pulse-green' : ''}`}
        onClick={() => handleDecision('approved')}
        disabled={isDisabled || submitting !== null}
        style={{
          minWidth: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.75rem',
          opacity: isDisabled ? 0.4 : 1,
          cursor: isDisabled ? 'not-allowed' : 'pointer',
        }}
      >
        <span style={{ fontSize: '1.5rem' }}>✓</span>
        <span>{submitting === 'approved' ? 'Approving...' : 'Approve'}</span>
      </button>

      {/* REJECT BUTTON */}
      <button
        id="btn-reject"
        className={`btn-reject ${submitting === 'rejected' ? 'animate-pulse-red' : ''}`}
        onClick={() => handleDecision('rejected')}
        disabled={isDisabled || submitting !== null}
        style={{
          minWidth: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.75rem',
          opacity: isDisabled ? 0.4 : 1,
          cursor: isDisabled ? 'not-allowed' : 'pointer',
        }}
      >
        <span style={{ fontSize: '1.5rem' }}>✗</span>
        <span>{submitting === 'rejected' ? 'Rejecting...' : 'Reject'}</span>
      </button>
    </div>
  )
}
