import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Custom hook for WebSocket connection with auto-reconnect.
 * Connects to the guard WebSocket endpoint for real-time image pushes.
 */
export function useWebSocket(token) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const reconnectDelay = useRef(1000)

  const connect = useCallback(() => {
    if (!token) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/guard?token=${token}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        reconnectDelay.current = 1000
        console.log('[WS] Connected to guard channel')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch (e) {
          console.warn('[WS] Non-JSON message:', event.data)
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        console.log('[WS] Disconnected:', event.code, event.reason)

        // Auto-reconnect with exponential backoff
        if (token) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
            connect()
          }, reconnectDelay.current)
        }
      }

      ws.onerror = (error) => {
        console.error('[WS] Error:', error)
      }
    } catch (e) {
      console.error('[WS] Connection failed:', e)
    }
  }, [token])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { isConnected, lastMessage, sendMessage }
}
