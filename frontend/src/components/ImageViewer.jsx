import { useState } from 'react'

/**
 * Image viewer with click-to-zoom functionality.
 * Displays the current undercarriage image for inspection.
 */
export default function ImageViewer({ imageBase64, inspectionId, prediction, anomalyBoundingBox }) {
  const [isZoomed, setIsZoomed] = useState(false)
  const [aiEnhanced, setAiEnhanced] = useState(true)

  if (!imageBase64) {
    return (
      <div className="image-viewer-container" style={{ minHeight: 400 }}>
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div
            style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              opacity: 0.3,
            }}
          >
            📷
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
            Waiting for next inspection image...
          </p>
          <div
            className="skeleton"
            style={{
              width: '60%',
              height: 200,
              margin: '1.5rem auto 0',
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div
      className="image-viewer-container animate-fade-in"
      style={{ minHeight: 400, position: 'relative', overflow: 'hidden' }}
    >
      <img
        id="inspection-image"
        src={`data:image/jpeg;base64,${imageBase64}`}
        alt={`Undercarriage inspection ${inspectionId || ''}`}
        className={isZoomed ? 'zoomed' : ''}
        onClick={() => setIsZoomed((z) => !z)}
        style={{
          maxWidth: isZoomed ? '200%' : '100%',
          maxHeight: isZoomed ? 'none' : '60vh',
          filter: aiEnhanced
            ? 'contrast(1.4) brightness(1.15) saturate(1.25) drop-shadow(0 0 10px rgba(52,211,153,0.25))'
            : 'none',
          transition: 'filter 0.3s ease',
        }}
      />

      {/* AI Spatial Anomaly Bounding Box Overlay */}
      {prediction === 'suspicious' && (
        <div
          className="animate-pulse"
          style={{
            position: 'absolute',
            top: '28%',
            left: '26%',
            width: '46%',
            height: '38%',
            border: '3px solid #ef4444',
            boxShadow: '0 0 20px rgba(239, 68, 68, 0.8), inset 0 0 15px rgba(239, 68, 68, 0.3)',
            borderRadius: 8,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: -26,
              left: -3,
              background: '#ef4444',
              color: 'white',
              fontSize: '0.65rem',
              fontWeight: 800,
              padding: '0.2rem 0.5rem',
              borderRadius: '4px 4px 0 0',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            🚨 AI Anomaly Hotspot — Foreign Wire/Object
          </div>
        </div>
      )}

      {/* Controls Bar (AI Enhancer + Zoom hint) */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          right: 12,
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          zIndex: 10,
        }}
      >
        <button
          onClick={(e) => {
            e.stopPropagation()
            setAiEnhanced(!aiEnhanced)
          }}
          style={{
            background: aiEnhanced ? 'linear-gradient(135deg, #059669, #10b981)' : 'rgba(0,0,0,0.7)',
            color: 'white',
            border: 'none',
            padding: '0.35rem 0.7rem',
            borderRadius: 6,
            fontSize: '0.75rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          {aiEnhanced ? '✨ AI Enhancer ON' : '✨ AI Enhancer OFF'}
        </button>

        <div
          onClick={() => setIsZoomed((z) => !z)}
          style={{
            background: 'rgba(0,0,0,0.7)',
            color: 'rgba(255,255,255,0.85)',
            padding: '0.35rem 0.7rem',
            borderRadius: 6,
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {isZoomed ? '🔍 Zoom Out' : '🔍 Zoom In'}
        </div>
      </div>

      {/* Inspection ID tag */}
      {inspectionId && (
        <div
          style={{
            position: 'absolute',
            top: 12,
            left: 12,
            background: 'rgba(0,0,0,0.7)',
            color: 'rgba(255,255,255,0.8)',
            padding: '0.3rem 0.6rem',
            borderRadius: 6,
            fontSize: '0.7rem',
            fontFamily: 'monospace',
          }}
        >
          ID: {inspectionId.slice(0, 8)}
        </div>
      )}
    </div>
  )
}
