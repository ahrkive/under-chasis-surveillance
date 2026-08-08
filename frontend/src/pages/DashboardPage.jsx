import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { useWebSocket } from '../hooks/useWebSocket'
import Navbar from '../components/Navbar'
import ImageViewer from '../components/ImageViewer'
import DecisionButtons from '../components/DecisionButtons'
import ModelSuggestion from '../components/ModelSuggestion'
import StatusBanner from '../components/StatusBanner'
import InspectionHistory from '../components/InspectionHistory'

/**
 * Main guard dashboard — the primary working view.
 * Shows live images, AI suggestion, and approve/reject controls.
 */
export default function DashboardPage() {
  const { token } = useAuth()
  const { isConnected, lastMessage } = useWebSocket(token)

  // Current inspection state
  const [currentImage, setCurrentImage] = useState(null)
  const [currentInspectionId, setCurrentInspectionId] = useState(null)
  const [modelPrediction, setModelPrediction] = useState(null)
  const [modelConfidence, setModelConfidence] = useState(null)
  const [modelVersion, setModelVersion] = useState(null)
  const [statusBanner, setStatusBanner] = useState(null)
  const [inspectionCount, setInspectionCount] = useState(0)
  const [isDecided, setIsDecided] = useState(false)

  // Phase 2 states
  const [licensePlate, setLicensePlate] = useState('KA-01-MJ-4892')
  const [searchPlateInput, setSearchPlateInput] = useState('')
  const [baselineScan, setBaselineScan] = useState(null)
  const [splitViewMode, setSplitViewMode] = useState(false)
  const [threatLevel, setThreatLevel] = useState('normal')
  const [guardNotes, setGuardNotes] = useState('')

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return

    if (lastMessage.type === 'new_image') {
      // New image from the bot
      setCurrentImage(lastMessage.image_data_b64)
      setCurrentInspectionId(lastMessage.inspection_id)
      setModelPrediction(lastMessage.model_prediction)
      setModelConfidence(lastMessage.model_confidence)
      setModelVersion(lastMessage.model_version)
      setStatusBanner(null) // Clear previous status
      setIsDecided(false)
      setInspectionCount((c) => c + 1)

      // ALPR extraction
      const detectedPlate = lastMessage.license_plate || 'KA-01-MJ-4892'
      setLicensePlate(detectedPlate)
      setSearchPlateInput(detectedPlate)

      // Auto-set threat level if high-confidence anomaly
      if (lastMessage.model_prediction === 'suspicious' && (lastMessage.model_confidence || 0) > 0.85) {
        setThreatLevel('critical')
      } else if (lastMessage.model_prediction === 'suspicious') {
        setThreatLevel('warning')
      } else {
        setThreatLevel('normal')
      }

      // Fetch baseline history for this plate
      fetchVehicleHistory(detectedPlate)
    } else if (lastMessage.type === 'decision_ack') {
      setStatusBanner({
        status: lastMessage.decision,
        message: lastMessage.message,
      })
    }
  }, [lastMessage])

  // Fetch baseline vehicle scans
  const fetchVehicleHistory = async (plate) => {
    if (!plate) return
    try {
      const res = await fetch(`/api/inspections/vehicle/${encodeURIComponent(plate)}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        if (data.baseline && data.baseline.id !== currentInspectionId) {
          setBaselineScan(data.baseline)
          setSplitViewMode(true)
        } else {
          setBaselineScan(null)
          setSplitViewMode(false)
        }
      }
    } catch (e) {
      console.error('Failed to fetch vehicle baseline history:', e)
    }
  }

  const handleDecision = useCallback((decision) => {
    setIsDecided(true)
    setStatusBanner({
      status: decision,
      message: `Inspection ${decision}. Waiting for next image...`,
    })
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar isConnected={isConnected} />

      <main
        style={{
          flex: 1,
          padding: '1.5rem',
          maxWidth: 1400,
          margin: '0 auto',
          width: '100%',
        }}
      >
        {/* Stats bar */}
        <div
          style={{
            display: 'flex',
            gap: '1rem',
            marginBottom: '1.5rem',
            flexWrap: 'wrap',
          }}
        >
          {[
            {
              label: 'Session Inspections',
              value: inspectionCount,
              icon: '📊',
            },
            {
              label: 'Connection',
              value: isConnected ? 'Live' : 'Offline',
              icon: isConnected ? '🟢' : '🔴',
            },
            {
              label: 'Model',
              value: modelVersion ? `v${modelVersion}` : 'N/A',
              icon: '🤖',
            },
            {
              label: 'Vehicle ALPR',
              value: licensePlate || 'Scanning...',
              icon: '🚗',
            },
          ].map(({ label, value, icon }) => (
            <div
              key={label}
              className="glass-card"
              style={{
                padding: '0.75rem 1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                flex: '1 1 auto',
                minWidth: 150,
              }}
            >
              <span style={{ fontSize: '1.2rem' }}>{icon}</span>
              <div>
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                  }}
                >
                  {value}
                </div>
              </div>
            </div>
          ))}

          {/* Export Audit Log Button */}
          <button
            onClick={() => window.open('/api/inspections/export/csv', '_blank')}
            className="glass-card"
            style={{
              padding: '0.75rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#60a5fa',
              fontWeight: 700,
              cursor: 'pointer',
              borderRadius: 12,
            }}
          >
            📥 Export Audit CSV
          </button>

          {/* Export Dataset ZIP Button */}
          <button
            onClick={() => window.open('/api/admin/export-dataset-zip', '_blank')}
            className="glass-card"
            style={{
              padding: '0.75rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontWeight: 700,
              cursor: 'pointer',
              borderRadius: 12,
            }}
          >
            📦 Download Dataset ZIP
          </button>
        </div>

        {/* Critical Threat Escalation Alarm Banner */}
        {threatLevel === 'critical' && (
          <div
            className="animate-pulse"
            style={{
              padding: '1rem 1.5rem',
              borderRadius: 12,
              marginBottom: '1.5rem',
              background: 'linear-gradient(135deg, rgba(220, 38, 38, 0.9), rgba(185, 28, 28, 0.9))',
              color: 'white',
              boxShadow: '0 0 25px rgba(239, 68, 68, 0.6)',
              display: 'flex',
              justify: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🚨</span>
              <div>
                <strong style={{ fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Critical Security Threat Detected!
                </strong>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                  AI Confidence: {Math.round((modelConfidence || 0) * 100)}% Suspicious — Inspect vehicle undercarriage thoroughly before gate approval.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ALPR & Vehicle History Lookup Bar */}
        <div
          className="glass-card"
          style={{
            padding: '1rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justify: 'space-between',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.3rem' }}>🚘</span>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Vehicle License Plate Tag
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#34d399', letterSpacing: '0.05em', fontFamily: 'monospace' }}>
                {licensePlate || 'NO PLATE DETECTED'}
              </div>
            </div>
          </div>

          {/* Plate Search Controls */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              className="input-field"
              placeholder="Enter License Plate..."
              value={searchPlateInput}
              onChange={(e) => setSearchPlateInput(e.target.value)}
              style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', textTransform: 'uppercase', width: 180 }}
            />
            <button
              onClick={() => fetchVehicleHistory(searchPlateInput)}
              className="button-primary"
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            >
              🔍 Lookup Baseline
            </button>
            {baselineScan && (
              <button
                onClick={() => setSplitViewMode(!splitViewMode)}
                style={{
                  fontSize: '0.8rem',
                  padding: '0.4rem 0.8rem',
                  background: splitViewMode ? 'rgba(129, 140, 248, 0.2)' : 'rgba(255,255,255,0.05)',
                  border: '1px solid #818cf8',
                  color: '#818cf8',
                  borderRadius: 8,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {splitViewMode ? '🖼️ Single View' : '🔀 Split Diff Baseline View'}
              </button>
            )}
          </div>
        </div>

        {/* Status Banner */}
        {statusBanner && (
          <StatusBanner
            status={statusBanner.status}
            message={statusBanner.message}
          />
        )}

        {/* Main Layout: Image + Controls */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 320px',
            gap: '1.5rem',
            marginBottom: '2rem',
          }}
          className="dashboard-grid"
        >
          {/* Left: Image Viewer (Single or Side-by-Side Baseline Diff) */}
          <div>
            {splitViewMode && baselineScan ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 700 }}>
                  <span style={{ color: '#34d399' }}>📸 Current Undercarriage Scan ({licensePlate})</span>
                  <span style={{ color: '#818cf8' }}>⏮️ Baseline Historical Scan ({new Date(baselineScan.captured_at).toLocaleDateString()})</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <ImageViewer
                    imageBase64={currentImage}
                    inspectionId={currentInspectionId}
                    prediction={modelPrediction}
                  />
                  <div className="glass-card" style={{ padding: '0.5rem', borderRadius: 12, overflow: 'hidden', height: 400, background: '#000' }}>
                    <img
                      src={baselineScan.image_url}
                      alt="Baseline Historical Scan"
                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <ImageViewer
                imageBase64={currentImage}
                inspectionId={currentInspectionId}
                prediction={modelPrediction}
              />
            )}

            <div style={{ marginTop: '1.25rem' }}>
              <DecisionButtons
                inspectionId={currentInspectionId}
                onDecision={handleDecision}
                disabled={isDecided}
              />
            </div>
          </div>

          {/* Right: AI Suggestion */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <ModelSuggestion
              prediction={modelPrediction}
              confidence={modelConfidence}
              modelVersion={modelVersion}
            />

            {/* Quick instructions */}
            <div
              className="glass-card"
              style={{ padding: '1.25rem' }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.75rem',
                }}
              >
                <span style={{ fontSize: '1rem' }}>📖</span>
                <span
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Instructions
                </span>
              </div>
              <ul
                style={{
                  listStyle: 'none',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.8,
                }}
              >
                <li>
                  <span style={{ color: '#34d399', marginRight: '0.5rem' }}>✓</span>
                  Click image to zoom in/out
                </li>
                <li>
                  <span style={{ color: '#34d399', marginRight: '0.5rem' }}>✓</span>
                  Review the AI suggestion
                </li>
                <li>
                  <span style={{ color: '#34d399', marginRight: '0.5rem' }}>✓</span>
                  Press <strong style={{ color: '#10b981' }}>Approve</strong> if normal
                </li>
                <li>
                  <span style={{ color: '#f87171', marginRight: '0.5rem' }}>✗</span>
                  Press <strong style={{ color: '#ef4444' }}>Reject</strong> if suspicious
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* History Table */}
        <InspectionHistory />
      </main>

      {/* Responsive grid override */}
      <style>{`
        @media (max-width: 768px) {
          .dashboard-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}
