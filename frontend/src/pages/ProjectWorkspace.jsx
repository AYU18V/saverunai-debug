import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import CodeEditor from '../components/ide/CodeEditor.jsx'
import EditorToolbar from '../components/ide/EditorToolbar.jsx'
import FileExplorer from '../components/ide/FileExplorer.jsx'
import TerminalPanel from '../components/ide/TerminalPanel.jsx'
import { authStorage, createProjectFile, deleteProjectFile, getProject, getProjectFiles, renameProjectFile, runCode, startWorkspace, updateProjectFile } from '../services/api.js'

function ProjectWorkspace() {
  const { projectId } = useParams(); const navigate = useNavigate(); const editorRef = useRef(null); const [project, setProject] = useState(null); const [files, setFiles] = useState([]); const [selected, setSelected] = useState(null); const [content, setContent] = useState(''); const [dirty, setDirty] = useState(false); const [saving, setSaving] = useState(false); const [running, setRunning] = useState(false); const [result, setResult] = useState(null); const [workspaceStatus, setWorkspaceStatus] = useState('starting'); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [dialog, setDialog] = useState(null); const [pathInput, setPathInput] = useState('')
  const token = () => authStorage.getToken()
  function failed(e) { if (e.status === 401) { authStorage.clear(); navigate('/login', { replace: true }); return true } return false }
  useEffect(() => { async function load() { try { const [p, f] = await Promise.all([getProject(projectId, token()), getProjectFiles(projectId, token())]); setProject(p); setFiles(f); if (f[0]) { setSelected(f[0]); setContent(f[0].content) }; const workspace = await startWorkspace(projectId, token()); setWorkspaceStatus(workspace.status) } catch (e) { if (!failed(e)) { setWorkspaceStatus('unavailable'); setError(e.status === 404 ? 'Project not found.' : 'Unable to load project.') } } } load() }, [projectId])
  async function save() { if (!selected) return; setSaving(true); try { const file = await updateProjectFile(projectId, selected.path, { content, language: selected.language }, token()); setFiles(x => x.map(i => i.path === file.path ? file : i)); setSelected(file); setDirty(false); setNotice('Saved') } catch (e) { if (!failed(e)) setError('Unable to save file. Please try again.') } finally { setSaving(false) } }
  async function run() {
    if (!selected || !['python', 'javascript', 'java', 'cpp'].includes(selected.language)) return
    // Monaco is the source of truth here: do not run an older MongoDB version of the file.
    const currentCode = editorRef.current?.getValue() ?? content
    const payload = { project_id: projectId, file_path: selected.path, language: selected.language, code: currentCode }
    setRunning(true); setResult(null); setError(''); setNotice('')
    console.log('Running:', { ...payload, code: `${currentCode.length} characters` })
    try {
      const executionResult = await runCode(payload, token())
      console.log('Execution response:', executionResult)
      setResult(executionResult)
    } catch (e) {
      // Keep an execution-authentication error visible in the terminal instead
      // of navigating away before the user can see the failed Run result.
      if (e.status !== 401 && !failed(e)) {
        const messages = { 401: 'Authentication required.', 403: 'You do not have access to this project.', 404: 'Project or file not found.', 408: 'Execution timed out.', 500: 'Execution service failed safely.' }
        setResult({ status: 'error', stdout: '', stderr: messages[e.status] || e.message || 'Unable to run code.', exit_code: null, execution_time_ms: 0 })
      } else {
        setResult({ status: 'error', stdout: '', stderr: 'Authentication required.', exit_code: null, execution_time_ms: 0 })
      }
    } finally { setRunning(false) }
  }
  useEffect(() => { const shortcut = e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save() } }; window.addEventListener('keydown', shortcut); return () => window.removeEventListener('keydown', shortcut) })
  function select(file) { if (dirty && !window.confirm(`Discard unsaved changes to ${selected.path}?`)) return; setSelected(file); setContent(file.content); setDirty(false); setResult(null) }
  async function submit(e) { e.preventDefault(); try { let file; if (dialog.type === 'new') { file = await createProjectFile(projectId, { path: pathInput, content: '' }, token()); setFiles(x => [...x, file]) } else { file = await renameProjectFile(projectId, dialog.file.path, pathInput, token()); setFiles(x => x.map(i => i.path === dialog.file.path ? file : i)) } setSelected(file); setContent(file.content); setDirty(false); setDialog(null) } catch (e) { if (!failed(e)) setError(e.status === 409 ? 'A file with this path already exists.' : 'Unable to update file name.') } }
  async function remove(file) { if (!window.confirm(`Delete ${file.path}?`)) return; try { await deleteProjectFile(projectId, file.path, token()); const next = files.filter(i => i.path !== file.path); setFiles(next); if (selected?.path === file.path) { setSelected(next[0] || null); setContent(next[0]?.content || ''); setDirty(false) } } catch (e) { if (!failed(e)) setError('Unable to delete file. Please try again.') } }
  if (!project) return <main className="dashboard-page">{error || 'Loading project...'}</main>
  return <main className="ide-page"><EditorToolbar projectName={project.name} isDirty={dirty} isSaving={saving} isRunning={running} onSave={save} onRun={run} onAiDebug={() => setNotice('AI debugging will be implemented in the Ollama phase.')} />{notice && <p className="ide-notice">{notice}</p>}{error && <p className="error-message">{error}</p>}<section className="ide-main"><FileExplorer files={files} selectedPath={selected?.path} isDirty={dirty} onSelect={select} onNewFile={() => { setPathInput(''); setDialog({ type: 'new' }) }} onRename={file => { setPathInput(file.path); setDialog({ type: 'rename', file }) }} onDelete={remove} /><div className="editor-area"><CodeEditor file={selected} content={content} onEditorMount={editor => { editorRef.current = editor }} onChange={v => { setContent(v); setDirty(v !== selected.content) }} /></div></section><TerminalPanel projectId={projectId} token={token()} workspaceStatus={workspaceStatus} result={result} isRunning={running} />{dialog && <div className="modal-backdrop"><form className="modal-card auth-form" onSubmit={submit}><h2>{dialog.type === 'new' ? 'New File' : 'Rename File'}</h2><label>File Name<input value={pathInput} onChange={e => setPathInput(e.target.value)} placeholder="src/main.py" autoFocus /></label><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setDialog(null)}>Cancel</button><button type="submit">{dialog.type === 'new' ? 'Create' : 'Rename'}</button></div></form></div>}</main>
}
export default ProjectWorkspace
