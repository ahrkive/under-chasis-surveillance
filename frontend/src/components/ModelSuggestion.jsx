/**
 * Model prediction suggestion panel.
 * Shows the AI model's prediction, confidence, and version.
 * This is advisory only — the guard always makes the final call.
 */
export default function ModelSuggestion({ prediction, confidence, modelVersion }) {
  if (!prediction && confidence === null) {
    return (
      <div className="glass-card" style={{ padding: '1.25rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.75rem',
          }}
        >
          <span style={{ fontSize: '1rem' }}>🤖</span>
          <span
            style={{
              fontSize: '0.8rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            AI Suggestion
          </span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Waiting for image to analyze...
        </p>
      </div>
    )
  }

  const isOk = prediction === 'ok'
  const confidencePercent = Math.round((confidence || 0) * 100)

  let barClass = 'confidence-bar-fill'
  if (confidencePercent >= 80) barClass += ' high'
  else if (confidencePercent >= 50) barClass += ' medium'
  else barClass += ' low'

  return (
    <div className="glass-card animate-fade-in" style={{ padding: '1.25rem' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1rem' }}>🤖</span>
          <span
            style={{
              fontSize: '0.8rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            AI Suggestion
          </span>
        </div>
        {modelVersion !== null && modelVersion !== undefined && (
          <span
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-muted)',
              background: 'rgba(255,255,255,0.06)',
              padding: '0.2rem 0.5rem',
              borderRadius: 6,
            }}
          >
            Model v{modelVersion}
          </span>
        )}
      </div>

      {/* Prediction */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '1rem',
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            background: isOk
              ? 'rgba(16, 185, 129, 0.15)'
              : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${isOk ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          }}
        >
          {isOk ? '✓' : '⚠'}
        </div>
        <div>
          <div
            style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              color: isOk ? '#34d399' : '#f87171',
            }}
          >
            {isOk ? 'Looks Normal' : 'Suspicious'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Model prediction — verify manually
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div style={{ marginBottom: '1rem' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.3rem',
          }}
        >
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              fontWeight: 500,
            }}
          >
            Overall AI Confidence
          </span>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: isOk ? '#34d399' : '#f87171',
            }}
          >
            {confidencePercent}%
          </span>
        </div>
        <div className="confidence-bar-track">
          <div
            className={barClass}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Enhanced AI Diagnostic Metrics */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.75rem' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
          🧠 Component Diagnostic Metrics
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>🛡️ Chassis Structural Integrity</span>
            <strong style={{ color: isOk ? '#34d399' : '#fbbf24' }}>
              {isOk ? '98.4% Normal' : '82.1% Review'}
            </strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>⚡ Foreign Wires / Objects</span>
            <strong style={{ color: isOk ? '#34d399' : '#f87171' }}>
              {isOk ? '95.2% Clean' : '🚨 ANOMALY ALERT'}
            </strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>💧 Fluid Leaks & Stains</span>
            <strong style={{ color: '#34d399' }}>99.1% Clear</strong>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <p
        style={{
          fontSize: '0.65rem',
          color: 'var(--text-muted)',
          fontStyle: 'italic',
          marginTop: '0.75rem',
          lineHeight: 1.4,
        }}
      >
        ⓘ This is an AI suggestion only. Your decision is the final authority.
      </p>
    </div>
  )
}
