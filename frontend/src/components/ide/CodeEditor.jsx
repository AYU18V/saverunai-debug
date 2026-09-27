import Editor from '@monaco-editor/react'

function CodeEditor({ file, content, onChange, onEditorMount }) {
  if (!file) return <div className="empty-editor">Create or select a file to start editing.</div>
  return <Editor height="100%" theme="vs-dark" language={file.language} value={content} onMount={onEditorMount} onChange={(value) => onChange(value ?? '')} options={{ automaticLayout: true, minimap: { enabled: true }, fontSize: 14, lineNumbers: 'on' }} />
}
export default CodeEditor
