import { useEffect, useRef, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { terminalUrl } from '../../services/api.js'

function TerminalPanel({ projectId, token, workspaceStatus, result, isRunning }) {
  const hostRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const [connection, setConnection] = useState('connecting')
  const [connectionVersion, setConnectionVersion] = useState(0)

  useEffect(() => {
    if (!projectId || !token || workspaceStatus !== 'running') return undefined
    let disposed = false
    let reconnectTimer
    const terminal = new Terminal({ cursorBlink: true, convertEol: true, fontFamily: 'Consolas, monospace', fontSize: 13, theme: { background: '#181818' } })
    const fit = new FitAddon()
    terminal.loadAddon(fit)
    terminal.open(hostRef.current)
    fit.fit()
    setConnection(reconnectAttempts.current ? 'reconnecting' : 'connecting')

    const socket = new WebSocket(terminalUrl(projectId, token))
    const heartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send('__webide_ping__')
    }, 25000)

    socket.onopen = () => {
      reconnectAttempts.current = 0
      setConnection('connected')
      terminal.writeln('\x1b[32mConnected to workspace terminal.\x1b[0m')
    }
    socket.onmessage = event => {
      if (event.data !== '__webide_pong__') terminal.write(event.data)
    }
    // Browsers always follow an error event with close.  Handle reconnection
    // in one place so a transient error cannot leave a stale terminal status.
    socket.onerror = () => undefined
    socket.onclose = () => {
      if (disposed) return
      if (reconnectAttempts.current >= 3) {
        setConnection('error')
        terminal.writeln('\x1b[31mTerminal connection closed.\x1b[0m')
        return
      }
      reconnectAttempts.current += 1
      setConnection('reconnecting')
      reconnectTimer = window.setTimeout(() => setConnectionVersion(version => version + 1), 500 * reconnectAttempts.current)
    }
    const disposable = terminal.onData(data => {
      if (socket.readyState === WebSocket.OPEN) socket.send(data)
    })
    const resize = () => fit.fit()
    window.addEventListener('resize', resize)

    return () => {
      disposed = true
      window.clearInterval(heartbeat)
      window.clearTimeout(reconnectTimer)
      disposable.dispose()
      window.removeEventListener('resize', resize)
      socket.close()
      terminal.dispose()
    }
  }, [projectId, token, workspaceStatus, connectionVersion])

  const status = workspaceStatus === 'unavailable' ? 'Workspace unavailable' : isRunning ? 'running' : connection
  const statusLabel = {
    connecting: 'Connecting',
    connected: 'Connected',
    reconnecting: 'Reconnecting',
    running: 'Running',
    error: 'Connection failed',
    'Workspace unavailable': 'Workspace unavailable',
  }[status] || status

  return <section className="terminal-panel"><div className="terminal-heading"><strong>TERMINAL</strong><span className={`terminal-status ${status}`}>● {statusLabel}</span></div>
    {workspaceStatus !== 'running' ? <p>{workspaceStatus === 'unavailable' ? 'Docker execution service is unavailable.' : 'Starting workspace...'}</p> : <div ref={hostRef} className="xterm-host" />}
    {isRunning && <p>$ Running current file...</p>}{result && <div className="run-result"><strong>Last Run: {result.status.toUpperCase()}</strong><pre>{result.stdout || result.stderr || `Process exited with code ${result.exit_code ?? 'unknown'}`}</pre><small>Exit Code: {result.exit_code ?? '—'} · Execution Time: {result.execution_time_ms ?? 0} ms</small></div>}
  </section>
}
export default TerminalPanel
