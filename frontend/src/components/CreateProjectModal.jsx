import { useState } from 'react'

function CreateProjectModal({ isSubmitting, onClose, onCreate, error }) {
  const [form, setForm] = useState({ name: '', description: '' })

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    onCreate(form)
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="create-project-title">
        <h2 id="create-project-title">Create New Project</h2>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Project Name
            <input name="name" value={form.name} onChange={updateField} maxLength="100" autoFocus required />
          </label>
          <label>
            Description <span className="optional-label">(optional)</span>
            <textarea name="description" value={form.description} onChange={updateField} maxLength="1000" rows="4" />
          </label>
          {error && <p className="error-message" role="alert">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={isSubmitting}>Cancel</button>
            <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Creating…' : 'Create Project'}</button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default CreateProjectModal
