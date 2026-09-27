function FileExplorer({ files, selectedPath, isDirty, onSelect, onNewFile, onRename, onDelete }) {
  return <aside className="file-explorer">
    <div className="panel-heading"><strong>FILES</strong><button type="button" onClick={onNewFile}>+ New File</button></div>
    <div className="file-list">{files.map((file) => <div className={`file-row ${file.path === selectedPath ? 'selected' : ''}`} key={file.path}>
      <button type="button" className="file-select" onClick={() => onSelect(file)} title={file.path}>📄 {file.path}{file.path === selectedPath && isDirty ? ' *' : ''}</button>
      <button type="button" className="icon-button" onClick={() => onRename(file)} aria-label={`Rename ${file.path}`}>✎</button>
      <button type="button" className="icon-button" onClick={() => onDelete(file)} aria-label={`Delete ${file.path}`}>×</button>
    </div>)}</div>
  </aside>
}
export default FileExplorer
