import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'

/**
 * Creator Command Center Dashboard
 * Provides full system telemetry, AI model management, training triggers,
 * historical execution logs, guard account creation, and inspection deep-dives.
 */
export default function CreatorDashboardPage() {
  const { token, user } = useAuth()
  const [activeTab, setActiveTab] = useState('telemetry') // telemetry | models | training | guards | inspections

  // Data states
  const [stats, setStats] = useState(null)
  const [models, setModels] = useState([])
  const [trainingLogs, setTrainingLogs] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  // Trigger training state
  const [triggering, setTriggering] = useState(false)
  const [triggerResult, setTriggerResult] = useState(null)

  // New Guard Form state
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newFullName, setNewFullName] = useState('')
  const [guardRole, setGuardRole] = useState('guard')
  const [userCreateMsg, setUserCreateMsg] = useState(null)

  // Sandbox AI Testing states
  const [testImageFile, setTestImageFile] = useState(null)
  const [testImagePreview, setTestImagePreview] = useState(null)
  const [testingModel, setTestingModel] = useState(false)
  const [testResult, setTestResult] = useState(null)

  // Handle image file selection for sandbox testing
  const handleSelectTestImage = (e) => {
    const file = e.target.files[0]
    if (file) {
      setTestImageFile(file)
      setTestImagePreview(URL.createObjectURL(file))
      setTestResult(null)
    }
  }

  // Handle sandbox AI inference execution
  const handleRunSandboxInference = async () => {
    if (!testImageFile) return
    setTestingModel(true)
    setTestResult(null)

    const formData = new FormData()
    formData.append('file', testImageFile)

    try {
      const res = await fetch('/api/admin/test-model', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        setTestResult(data)
      } else {
        const err = await res.json()
        alert(`Inference failed: ${err.detail || 'Error running test'}`)
      }
    } catch (e) {
      alert(`Network error: ${e.message}`)
    } finally {
      setTestingModel(false)
    }
  }

  // Handle saving tested image to training dataset
  const [savingDataset, setSavingDataset] = useState(false)
  const [saveFeedback, setSaveFeedback] = useState(null)

  // Dataset Gallery states
  const [galleryItems, setGalleryItems] = useState([])
  const [galleryTotal, setGalleryTotal] = useState(0)
  const [galleryDecisionFilter, setGalleryDecisionFilter] = useState('all')
  const [gallerySourceFilter, setGallerySourceFilter] = useState('all')
  const [galleryLoading, setGalleryLoading] = useState(false)
  const [selectedGalleryImage, setSelectedGalleryImage] = useState(null)

  // Fleet Management states
  const [fleetData, setFleetData] = useState(null)
  const [fleetLoading, setFleetLoading] = useState(false)

  const fetchFleet = async () => {
    setFleetLoading(true)
    try {
      const res = await fetch('/api/admin/fleet', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setFleetData(data)
      }
    } catch (e) {
      console.error('Failed to fetch fleet:', e)
    } finally {
      setFleetLoading(false)
    }
  }

  const fetchGallery = async () => {
    setGalleryLoading(true)
    try {
      const res = await fetch(
        `/api/admin/dataset-gallery?decision=${galleryDecisionFilter}&source=${gallerySourceFilter}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (res.ok) {
        const data = await res.json()
        setGalleryItems(data.items)
        setGalleryTotal(data.total)
      }
    } catch (e) {
      console.error('Failed to fetch dataset gallery:', e)
    } finally {
      setGalleryLoading(false)
    }
  }

  const handleSaveToDataset = async (label) => {
    if (!testImageFile) return
    setSavingDataset(true)
    setSaveFeedback(null)

    const formData = new FormData()
    formData.append('file', testImageFile)

    try {
      const res = await fetch(`/api/admin/save-to-dataset?label=${label}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        setSaveFeedback({
          type: 'success',
          text: `✅ ${data.message} (Total dataset size: ${data.total_approved_images} images)`,
        })
        await reloadData()
      } else {
        const err = await res.json()
        setSaveFeedback({ type: 'error', text: `Failed to save: ${err.detail}` })
      }
    } catch (e) {
      setSaveFeedback({ type: 'error', text: `Error: ${e.message}` })
    } finally {
      setSavingDataset(false)
    }
  }

  // Fetch telemetry and stats
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/admin/stats', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  // Fetch model versions
  const fetchModels = async () => {
    try {
      const res = await fetch('/api/admin/models', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setModels(data)
      }
    } catch (e) {
      console.error('Failed to fetch models:', e)
    }
  }

  // Fetch training logs
  const fetchTrainingLogs = async () => {
    try {
      const res = await fetch('/api/admin/training-logs', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setTrainingLogs(data)
      }
    } catch (e) {
      console.error('Failed to fetch training logs:', e)
    }
  }

  // Fetch user list
  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/admin/users', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(data)
      }
    } catch (e) {
      console.error('Failed to fetch users:', e)
    }
  }

  const reloadData = async () => {
    setLoading(true)
    await Promise.all([fetchStats(), fetchModels(), fetchTrainingLogs(), fetchUsers(), fetchGallery(), fetchFleet()])
    setLoading(false)
  }

  useEffect(() => {
    reloadData()
  }, [])

  useEffect(() => {
    fetchGallery()
  }, [galleryDecisionFilter, gallerySourceFilter])

  // Handle Manual Training Trigger
  const handleTriggerTraining = async () => {
    setTriggering(true)
    setTriggerResult(null)
    try {
      const res = await fetch('/api/training/trigger', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      setTriggerResult(data)
      await reloadData()
    } catch (e) {
      setTriggerResult({ status: 'error', message: e.message })
    } finally {
      setTriggering(false)
    }
  }

  // Handle Model Activation / Hot-swap
  const handleActivateModel = async (version) => {
    try {
      const res = await fetch(`/api/admin/models/${version}/activate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        alert(`Model v${version} is now LIVE!`)
        await reloadData()
      } else {
        const err = await res.json()
        alert(`Failed to activate model: ${err.detail}`)
      }
    } catch (e) {
      alert(`Error: ${e.message}`)
    }
  }

  // Handle New Guard Account Creation
  const handleCreateGuard = async (e) => {
    e.preventDefault()
    setUserCreateMsg(null)
    try {
      const res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
          full_name: newFullName,
          role: guardRole,
        }),
      })
      if (res.ok) {
        setUserCreateMsg({ type: 'success', text: `Account '${newUsername}' created successfully!` })
        setNewUsername('')
        setNewPassword('')
        setNewFullName('')
        await fetchUsers()
      } else {
        const err = await res.json()
        let msg = 'Failed to create user'
        if (typeof err.detail === 'string') {
          msg = err.detail
        } else if (Array.isArray(err.detail)) {
          msg = err.detail.map((e) => `${e.loc?.[e.loc.length - 1] || 'field'}: ${e.msg}`).join('; ')
        }
        setUserCreateMsg({ type: 'error', text: msg })
      }
    } catch (e) {
      setUserCreateMsg({ type: 'error', text: e.message })
    }
  }

  // Handle Guard Account Deletion
  const handleDeleteGuard = async (userId, username) => {
    if (!window.confirm(`Are you sure you want to delete account '${username}'?`)) return
    try {
      const res = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setUserCreateMsg({ type: 'success', text: `Account '${username}' deleted successfully.` })
        await fetchUsers()
      } else {
        const err = await res.json()
        alert(`Delete failed: ${err.detail || 'Error deleting account'}`)
      }
    } catch (e) {
      alert(`Error: ${e.message}`)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar isConnected={true} />

      <main
        style={{
          flex: 1,
          padding: '1.5rem',
          maxWidth: 1400,
          margin: '0 auto',
          width: '100%',
        }}
      >
        {/* Creator Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '1.5rem',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.8rem' }}>⚡</span>
              <div>
                <h1
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: 800,
                    background: 'linear-gradient(135deg, #818cf8, #c084fc)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  Creator Command Center
                </h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  System Telemetry, ResNet50 Controls, Training Pipeline & Guard Access
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={handleTriggerTraining}
              disabled={triggering}
              style={{
                padding: '0.6rem 1.25rem',
                background: triggering
                  ? 'rgba(129, 140, 248, 0.3)'
                  : 'linear-gradient(135deg, #6366f1, #818cf8)',
                border: 'none',
                borderRadius: 10,
                color: 'white',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: triggering ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
              }}
            >
              <span>{triggering ? '⚙️ Fine-tuning...' : '🚀 Trigger AI Training'}</span>
            </button>

            <button
              onClick={reloadData}
              style={{
                padding: '0.6rem 1rem',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 10,
                color: 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Trigger Result Notification */}
        {triggerResult && (
          <div
            className="animate-fade-in"
            style={{
              padding: '1rem',
              marginBottom: '1.5rem',
              borderRadius: 12,
              background:
                triggerResult.status === 'completed'
                  ? 'rgba(16, 185, 129, 0.15)'
                  : 'rgba(245, 158, 11, 0.15)',
              border:
                triggerResult.status === 'completed'
                  ? '1px solid rgba(16, 185, 129, 0.3)'
                  : '1px solid rgba(245, 158, 11, 0.3)',
              color: triggerResult.status === 'completed' ? '#34d399' : '#fbbf24',
              fontSize: '0.9rem',
              fontWeight: 600,
            }}
          >
            {triggerResult.status === 'completed'
              ? `✅ Training run completed! New model version v${triggerResult.new_model_version} deployed.`
              : `ℹ️ ${triggerResult.message || 'Training job executed (need more approved images before updating).'}`}
          </div>
        )}

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            marginBottom: '1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '0.5rem',
            overflowX: 'auto',
          }}
        >
          {[
            { id: 'telemetry', label: '📊 Telemetry & Metrics', icon: '📊' },
            { id: 'sandbox', label: '🔬 AI Testing Sandbox', icon: '🔬' },
            { id: 'gallery', label: '📁 Dataset Gallery', icon: '📁' },
            { id: 'models', label: '🧠 ResNet50 Models', icon: '🧠' },
            { id: 'training', label: '📜 Execution Logs', icon: '📜' },
            { id: 'guards', label: '👥 User & Access Control', icon: '👥' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0.6rem 1.2rem',
                background:
                  activeTab === tab.id
                    ? 'rgba(99, 102, 241, 0.2)'
                    : 'transparent',
                border:
                  activeTab === tab.id
                    ? '1px solid rgba(99, 102, 241, 0.4)'
                    : '1px solid transparent',
                borderRadius: 10,
                color:
                  activeTab === tab.id ? '#818cf8' : 'var(--text-secondary)',
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: '0.9rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* TAB 1: TELEMETRY & METRICS */}
        {activeTab === 'telemetry' && stats && (
          <div className="animate-fade-in" style={{ display: 'grid', gap: '1.5rem' }}>
            {/* Top Key Metrics */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '1.25rem',
              }}
            >
              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  TOTAL INSPECTIONS
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>
                  {stats.inspections.total}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Approved: {stats.inspections.approved} | Rejected: {stats.inspections.rejected}
                </div>
              </div>

              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  ACTIVE AI MODEL
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#818cf8', marginTop: 4 }}>
                  {stats.ai_model.active_version ? `v${stats.ai_model.active_version}` : 'Baseline'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Architecture: {stats.ai_model.architecture}
                </div>
              </div>

              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  ACCUMULATED DATASET
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#34d399', marginTop: 4 }}>
                  {stats.inspections.approved} <span style={{ fontSize: '1rem' }}>images</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Storage: {stats.system.storage_size_mb} MB
                </div>
              </div>

              <div className="glass-card" style={{ padding: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  GUARD STATIONS
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24', marginTop: 4 }}>
                  {stats.system.connected_guard_clients} <span style={{ fontSize: '1rem' }}>connected</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Total accounts: {stats.users.total_accounts}
                </div>
              </div>
            </div>

            {/* System Breakdown Card */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>
                ⚙️ System & Server Telemetry
              </h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '1rem',
                  fontSize: '0.85rem',
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Environment:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{stats.system.environment}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Inference Hardware:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{stats.system.device.toUpperCase()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Storage Provider:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{stats.system.storage_provider.toUpperCase()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Model Status:</span>{' '}
                  <strong style={{ color: stats.ai_model.is_loaded ? '#34d399' : '#f87171' }}>
                    {stats.ai_model.is_loaded ? 'LOADED & ACTIVE' : 'UNLOADED'}
                  </strong>
                </div>
              </div>
            </div>

            {/* Currently Logged-In Guards Table */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>
                  🟢 Currently Logged-In Guards & Active WebSocket Sessions ({stats.system.active_guards?.length || 0})
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
                  LIVE TELEMETRY
                </span>
              </div>

              {(!stats.system.active_guards || stats.system.active_guards.length === 0) ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  No active guard WebSocket sessions connected right now.
                </div>
              ) : (
                <table className="inspection-table">
                  <thead>
                    <tr>
                      <th>Guard ID</th>
                      <th>Full Name</th>
                      <th>Username</th>
                      <th>Role</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.system.active_guards.map((g) => (
                      <tr key={g.id}>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#818cf8' }}>
                          {g.id}
                        </td>
                        <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{g.full_name}</td>
                        <td style={{ color: 'var(--text-secondary)' }}>@{g.username}</td>
                        <td>
                          <span className="badge badge-approved">
                            {g.role.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: '#34d399', fontWeight: 600, fontSize: '0.8rem' }}>
                            🟢 ACTIVE LIVE SESSION
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* TAB: AI TESTING SANDBOX */}
        {activeTab === 'sandbox' && (
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            {/* Image Selection / Upload Card */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '1.2rem' }}>🔬</span>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Creator AI Testing Sandbox
                </h3>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
                Upload or select any image file from your computer to run immediate live inference through the active ResNet50 model.
              </p>

              {/* File Input */}
              <div
                style={{
                  border: '2px dashed var(--border-accent)',
                  borderRadius: 14,
                  padding: '2rem 1rem',
                  textAlign: 'center',
                  background: 'rgba(99, 102, 241, 0.04)',
                  cursor: 'pointer',
                  marginBottom: '1.25rem',
                }}
                onClick={() => document.getElementById('sandbox-file-input').click()}
              >
                <input
                  id="sandbox-file-input"
                  type="file"
                  accept="image/*"
                  onChange={handleSelectTestImage}
                  style={{ display: 'none' }}
                />
                <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📁</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                  {testImageFile ? testImageFile.name : 'Click to select or drop an image file'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  Supports JPEG, PNG, WEBP, etc.
                </div>
              </div>

              {/* Image Preview */}
              {testImagePreview && (
                <div style={{ marginBottom: '1.25rem', textAlign: 'center' }}>
                  <img
                    src={testImagePreview}
                    alt="Test Preview"
                    style={{
                      maxHeight: 220,
                      maxWidth: '100%',
                      borderRadius: 12,
                      border: '1px solid var(--border-subtle)',
                      objectFit: 'contain',
                    }}
                  />
                </div>
              )}

              {/* Run Inference Button */}
              <button
                onClick={handleRunSandboxInference}
                disabled={!testImageFile || testingModel}
                style={{
                  width: '100%',
                  padding: '0.85rem',
                  background: !testImageFile || testingModel
                    ? 'rgba(99, 102, 241, 0.3)'
                    : 'linear-gradient(135deg, #6366f1, #818cf8)',
                  border: 'none',
                  borderRadius: 12,
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  cursor: !testImageFile || testingModel ? 'not-allowed' : 'pointer',
                  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.3)',
                }}
              >
                {testingModel ? '⚙️ Running ResNet50 Inference...' : '⚡ Run Live Model Inference'}
              </button>
            </div>

            {/* Inference Results Card */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>
                📊 Model Output & Confidence Analysis
              </h3>

              {!testResult ? (
                <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '3rem', opacity: 0.3, marginBottom: '1rem' }}>🤖</div>
                  Select an image on the left and click "Run Live Model Inference" to view predictions.
                </div>
              ) : (
                <div className="animate-fade-in">
                  {/* Top Prediction Badge */}
                  <div
                    style={{
                      padding: '1.25rem',
                      borderRadius: 14,
                      marginBottom: '1.5rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      background: testResult.prediction === 'ok'
                        ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(52, 211, 153, 0.1))'
                        : 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(248, 113, 113, 0.1))',
                      border: testResult.prediction === 'ok'
                        ? '1px solid rgba(16, 185, 129, 0.4)'
                        : '1px solid rgba(239, 68, 68, 0.4)',
                    }}
                  >
                    <div style={{ fontSize: '2.5rem' }}>
                      {testResult.prediction === 'ok' ? '✅' : '⚠️'}
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: '1.3rem',
                          fontWeight: 800,
                          color: testResult.prediction === 'ok' ? '#34d399' : '#f87171',
                        }}
                      >
                        {testResult.prediction === 'ok' ? 'NORMAL / OK' : 'SUSPICIOUS / ANOMALY'}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Confidence: <strong>{testResult.confidence_percentage}%</strong>
                      </div>
                    </div>
                  </div>

                  {/* Confidence Bar */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.8rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Model Confidence</span>
                      <strong style={{ color: testResult.prediction === 'ok' ? '#34d399' : '#f87171' }}>
                        {testResult.confidence_percentage}%
                      </strong>
                    </div>
                    <div className="confidence-bar-track" style={{ height: 10 }}>
                      <div
                        className={`confidence-bar-fill ${testResult.confidence_percentage >= 80 ? 'high' : testResult.confidence_percentage >= 50 ? 'medium' : 'low'}`}
                        style={{ width: `${testResult.confidence_percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Class Probabilities Table */}
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                    Class Probabilities Breakdown
                  </h4>
                  <table className="inspection-table" style={{ marginBottom: '1.5rem' }}>
                    <thead>
                      <tr>
                        <th>Class Label</th>
                        <th>Probability Score</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ fontWeight: 700, color: '#34d399' }}>OK (Normal)</td>
                        <td>{(testResult.probabilities.ok * 100).toFixed(1)}%</td>
                        <td>
                          {testResult.prediction === 'ok' && (
                            <span className="badge badge-approved">WINNER</span>
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 700, color: '#f87171' }}>Suspicious (Anomaly)</td>
                        <td>{(testResult.probabilities.suspicious * 100).toFixed(1)}%</td>
                        <td>
                          {testResult.prediction === 'suspicious' && (
                            <span className="badge badge-rejected">WINNER</span>
                          )}
                        </td>
                      </tr>
                    </tbody>
                  </table>

                  {/* Model Metadata */}
                  <div
                    style={{
                      padding: '1rem',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: 10,
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      lineHeight: 1.6,
                      marginBottom: '1.25rem',
                    }}
                  >
                    <div>Architecture: <strong style={{ color: 'var(--text-primary)' }}>{testResult.architecture}</strong></div>
                    <div>Active Version: <strong style={{ color: '#818cf8' }}>v{testResult.model_version}</strong></div>
                    <div>Input Resolution: <strong style={{ color: 'var(--text-primary)' }}>256x256 RGB</strong></div>
                    <div>Payload Size: <strong style={{ color: 'var(--text-primary)' }}>{Math.round(testResult.image_size_bytes / 1024)} KB</strong></div>
                  </div>

                  {/* Creator Manual Save to Dataset Action Buttons */}
                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                      💾 Creator Dataset Controls — Add Image to Fine-Tuning Dataset:
                    </div>

                    {saveFeedback && (
                      <div
                        className="animate-fade-in"
                        style={{
                          padding: '0.75rem 1rem',
                          borderRadius: 10,
                          marginBottom: '1rem',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          background: saveFeedback.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          border: saveFeedback.type === 'success' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                          color: saveFeedback.type === 'success' ? '#34d399' : '#f87171',
                        }}
                      >
                        {saveFeedback.text}
                      </div>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                      <button
                        onClick={() => handleSaveToDataset('approved')}
                        disabled={savingDataset}
                        style={{
                          padding: '0.75rem',
                          background: 'linear-gradient(135deg, #059669, #10b981)',
                          border: 'none',
                          borderRadius: 10,
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          cursor: savingDataset ? 'wait' : 'pointer',
                        }}
                      >
                        {savingDataset ? 'Saving...' : '✓ Save as NORMAL (OK)'}
                      </button>

                      <button
                        onClick={() => handleSaveToDataset('rejected')}
                        disabled={savingDataset}
                        style={{
                          padding: '0.75rem',
                          background: 'linear-gradient(135deg, #dc2626, #ef4444)',
                          border: 'none',
                          borderRadius: 10,
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          cursor: savingDataset ? 'wait' : 'pointer',
                        }}
                      >
                        {savingDataset ? 'Saving...' : '✗ Save as SUSPICIOUS'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB: DATASET GALLERY */}
        {activeTab === 'gallery' && (
          <div className="animate-fade-in">
            <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    📁 Fine-Tuning Dataset Gallery ({galleryTotal} images)
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Browse and inspect every image stored in the dataset (Guard Approvals, Rejections, and Creator Sandbox uploads).
                  </p>
                </div>

                {/* Filter Controls */}
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <select
                    className="input-field"
                    value={galleryDecisionFilter}
                    onChange={(e) => setGalleryDecisionFilter(e.target.value)}
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                  >
                    <option value="all">All Decisions (Approved & Rejected)</option>
                    <option value="approved">Approved / Normal (✓)</option>
                    <option value="rejected">Rejected / Suspicious (✗)</option>
                  </select>

                  <select
                    className="input-field"
                    value={gallerySourceFilter}
                    onChange={(e) => setGallerySourceFilter(e.target.value)}
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                  >
                    <option value="all">All Sources</option>
                    <option value="sandbox">⚡ Creator Sandbox Uploads</option>
                    <option value="bot">🤖 Edge Bot Camera Streams</option>
                  </select>

                  <a
                    href="/api/admin/export-dataset-zip"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button-primary"
                    style={{
                      fontSize: '0.8rem',
                      padding: '0.4rem 0.9rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      textDecoration: 'none',
                      background: 'linear-gradient(135deg, #059669, #10b981)',
                    }}
                  >
                    📦 Download Dataset ZIP
                  </a>
                </div>
              </div>

              {/* Gallery Grid */}
              {galleryLoading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  Loading dataset images...
                </div>
              ) : galleryItems.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  No dataset images found matching the current filters.
                </div>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                    gap: '1.25rem',
                  }}
                >
                  {galleryItems.map((item) => (
                    <div
                      key={item.id}
                      className="glass-card"
                      style={{
                        padding: '0.75rem',
                        borderRadius: 12,
                        cursor: 'pointer',
                        transition: 'transform 0.2s ease, border-color 0.2s ease',
                        border: '1px solid var(--border-subtle)',
                      }}
                      onClick={() => setSelectedGalleryImage(item)}
                    >
                      {/* Image Thumbnail */}
                      <div
                        style={{
                          height: 160,
                          borderRadius: 8,
                          overflow: 'hidden',
                          background: '#111827',
                          position: 'relative',
                          marginBottom: '0.75rem',
                        }}
                      >
                        <img
                          src={item.image_url}
                          alt={`Inspection ${item.id}`}
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                          }}
                          loading="lazy"
                        />
                        <div
                          style={{
                            position: 'absolute',
                            top: 6,
                            right: 6,
                          }}
                        >
                          <span className={`badge ${item.decision === 'approved' ? 'badge-approved' : 'badge-rejected'}`}>
                            {item.decision === 'approved' ? 'APPROVED' : 'REJECTED'}
                          </span>
                        </div>
                      </div>

                      {/* Info Footer */}
                      <div style={{ fontSize: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontWeight: 700, color: item.is_sandbox ? '#c084fc' : '#818cf8' }}>
                            {item.is_sandbox ? '⚡ Creator Sandbox' : `🤖 ${item.bot_id}`}
                          </span>
                          <span style={{ color: 'var(--text-muted)' }}>
                            {item.model_confidence ? `${(item.model_confidence * 100).toFixed(0)}%` : ''}
                          </span>
                        </div>

                        <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                          {item.captured_at ? new Date(item.captured_at).toLocaleString() : '—'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* High-Resolution Image Modal */}
        {selectedGalleryImage && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.85)',
              backdropFilter: 'blur(10px)',
              zIndex: 9999,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2rem',
            }}
            onClick={() => setSelectedGalleryImage(null)}
          >
            <div
              className="glass-card animate-fade-in"
              style={{
                maxWidth: 900,
                width: '100%',
                maxHeight: '90vh',
                overflowY: 'auto',
                padding: '1.5rem',
                borderRadius: 16,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  🖼️ Dataset Image Details
                </h3>
                <button
                  onClick={() => setSelectedGalleryImage(null)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: 'white',
                    padding: '0.4rem 0.8rem',
                    borderRadius: 8,
                    cursor: 'pointer',
                    fontWeight: 700,
                  }}
                >
                  ✕ Close
                </button>
              </div>

              <div style={{ textAlign: 'center', marginBottom: '1.25rem', background: '#000', borderRadius: 12, overflow: 'hidden' }}>
                <img
                  src={selectedGalleryImage.image_url}
                  alt="Full Dataset Image"
                  style={{
                    maxHeight: '60vh',
                    maxWidth: '100%',
                    objectFit: 'contain',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.85rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Inspection ID:</span>{' '}
                  <strong style={{ fontFamily: 'monospace', color: '#818cf8' }}>{selectedGalleryImage.id}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Decision Label:</span>{' '}
                  <span className={`badge ${selectedGalleryImage.decision === 'approved' ? 'badge-approved' : 'badge-rejected'}`}>
                    {selectedGalleryImage.decision.toUpperCase()}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Source:</span>{' '}
                  <strong style={{ color: selectedGalleryImage.is_sandbox ? '#c084fc' : 'var(--text-primary)' }}>
                    {selectedGalleryImage.is_sandbox ? '⚡ Creator Sandbox Upload' : `🤖 ${selectedGalleryImage.bot_id}`}
                  </strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>AI Prediction:</span>{' '}
                  <strong style={{ color: selectedGalleryImage.model_prediction === 'ok' ? '#34d399' : '#f87171' }}>
                    {selectedGalleryImage.model_prediction?.toUpperCase() || 'N/A'} ({(selectedGalleryImage.model_confidence * 100).toFixed(1)}%)
                  </strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Model Version:</span>{' '}
                  <strong style={{ color: '#818cf8' }}>v{selectedGalleryImage.model_version}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Captured Timestamp:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>
                    {selectedGalleryImage.captured_at ? new Date(selectedGalleryImage.captured_at).toLocaleString() : '—'}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: RESNET50 MODELS */}
        {activeTab === 'models' && (
          <div className="animate-fade-in">
            <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    🤖 Trained Model Checkpoints (ResNet50)
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Hot-swap any historical model version directly into the live inspection server.
                  </p>
                </div>
              </div>

              <table className="inspection-table" style={{ marginTop: '1.5rem' }}>
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Training Images</th>
                    <th>Val Accuracy</th>
                    <th>Trained At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {models.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        No fine-tuned model versions saved yet. The baseline ResNet50 model is active.
                      </td>
                    </tr>
                  ) : (
                    models.map((m) => (
                      <tr key={m.version}>
                        <td style={{ fontWeight: 700, color: '#818cf8' }}>v{m.version}</td>
                        <td>
                          <span
                            className={`badge ${
                              m.status === 'active' ? 'badge-approved' : 'badge-pending'
                            }`}
                          >
                            {m.status.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <div><strong>{m.training_image_count} images</strong></div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Kaggle Base (3,000+) + Live Approved ({stats?.inspections?.approved || 0})
                          </div>
                        </td>
                        <td style={{ fontWeight: 700, color: '#34d399' }}>
                          {m.validation_accuracy ? `${(m.validation_accuracy * 100).toFixed(1)}%` : 'N/A'}
                        </td>
                        <td>{m.trained_at ? new Date(m.trained_at).toLocaleString() : 'Baseline'}</td>
                        <td>
                          {m.status !== 'active' && (
                            <button
                              onClick={() => handleActivateModel(m.version)}
                              style={{
                                padding: '0.3rem 0.75rem',
                                background: 'rgba(99, 102, 241, 0.2)',
                                border: '1px solid rgba(99, 102, 241, 0.4)',
                                borderRadius: 6,
                                color: '#818cf8',
                                fontWeight: 600,
                                fontSize: '0.75rem',
                                cursor: 'pointer',
                              }}
                            >
                              Activate Live
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: TRAINING LOGS */}
        {activeTab === 'training' && (
          <div className="animate-fade-in">
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>
                📜 AI Training Execution History
              </h3>

              <table className="inspection-table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>New / Total Images</th>
                    <th>Validation Accuracy</th>
                    <th>Final Loss</th>
                    <th>Execution Time</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingLogs.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        No training runs recorded yet. Click "Trigger AI Training" above to execute a run.
                      </td>
                    </tr>
                  ) : (
                    trainingLogs.map((log) => (
                      <tr key={log.id}>
                        <td style={{ fontWeight: 700, color: '#818cf8' }}>v{log.model_version}</td>
                        <td>
                          <span
                            className={`badge ${
                              log.status === 'success' ? 'badge-approved' : 'badge-rejected'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td>+{log.new_images_count} (Total: {log.total_images_count})</td>
                        <td style={{ fontWeight: 700, color: '#34d399' }}>
                          {log.accuracy ? `${(log.accuracy * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td>{log.loss ? log.loss.toFixed(4) : '—'}</td>
                        <td>{new Date(log.started_at).toLocaleString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: USER & ACCESS CONTROL */}
        {activeTab === 'guards' && (
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            {/* Create Account Form */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                ➕ Create Guard or Creator Account
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
                Provision login credentials for security personnel or lead creators.
              </p>

              {userCreateMsg && (
                <div
                  style={{
                    padding: '0.75rem',
                    borderRadius: 8,
                    marginBottom: '1rem',
                    fontSize: '0.85rem',
                    background: userCreateMsg.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                    color: userCreateMsg.type === 'success' ? '#34d399' : '#f87171',
                  }}
                >
                  {userCreateMsg.text}
                </div>
              )}

              <form onSubmit={handleCreateGuard}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Guard John Doe"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    required
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Username
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. guard_john"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    required
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Password
                  </label>
                  <input
                    type="password"
                    className="input-field"
                    placeholder="Enter secure password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                  />
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Role / Permissions
                  </label>
                  <select
                    className="input-field"
                    value={guardRole}
                    onChange={(e) => setGuardRole(e.target.value)}
                  >
                    <option value="guard">Guard (Inspection UI Only)</option>
                    <option value="admin">Creator / Admin (Full Command Center Access)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  style={{
                    width: '100%',
                    padding: '0.8rem',
                    background: 'linear-gradient(135deg, #6366f1, #818cf8)',
                    border: 'none',
                    borderRadius: 10,
                    color: 'white',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Create Account
                </button>
              </form>
            </div>

            {/* Existing Accounts List */}
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  👥 Registered Accounts List
                </h3>
                <span
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    background: 'rgba(99, 102, 241, 0.15)',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    color: '#818cf8',
                    padding: '0.25rem 0.75rem',
                    borderRadius: 8,
                  }}
                >
                  TOTAL REGISTERED: {users.length}
                </span>
              </div>

              <table className="inspection-table">
                <thead>
                  <tr>
                    <th>Guard ID</th>
                    <th>User</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u, idx) => (
                    <tr key={`${u.id}-${idx}`}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#818cf8' }}>
                        {u.id}
                      </td>
                      <td>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{u.full_name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>@{u.username}</div>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            u.role === 'admin' ? 'badge-approved' : 'badge-pending'
                          }`}
                        >
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.75rem' }}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td>
                        {u.id !== user?.id && (
                          <button
                            onClick={() => handleDeleteGuard(u.id, u.username)}
                            style={{
                              padding: '0.25rem 0.6rem',
                              background: 'rgba(239, 68, 68, 0.15)',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              borderRadius: 6,
                              color: '#f87171',
                              fontSize: '0.75rem',
                              cursor: 'pointer',
                              fontWeight: 600,
                            }}
                          >
                            🗑️ Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
