function EditorToolbar({ projectName, isDirty, isSaving, isRunning, onSave, onRun, onAiDebug }) {
  return <header className="ide-toolbar"><strong>{projectName}</strong><div><button type="button" onClick={onSave} disabled={!isDirty || isSaving}>{isSaving ? 'Saving…' : 'Save'}</button><button type="button" className="secondary-button" onClick={onRun} disabled={isRunning}>{isRunning ? 'Running…' : 'Run'}</button><button type="button" className="secondary-button" onClick={onAiDebug}>AI Debug</button></div></header>
}
export default EditorToolbar
