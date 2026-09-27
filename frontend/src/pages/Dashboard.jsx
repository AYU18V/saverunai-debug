import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CreateProjectModal from '../components/CreateProjectModal.jsx'
import { authStorage, createProject, deleteProject, getCurrentUser, getProjects } from '../services/api.js'

function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState(authStorage.getUser())
  const [projects, setProjects] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  function handleUnauthorized(requestError) {
    if (requestError.status === 401) {
      authStorage.clear()
      navigate('/login', { replace: true })
      return true
    }
    return false
  }

  async function loadProjects() {
    setIsLoading(true)
    setError('')
    try {
      setProjects(await getProjects(authStorage.getToken()))
    } catch (requestError) {
      if (!handleUnauthorized(requestError)) {
        setError('Unable to load projects. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        const currentUser = await getCurrentUser(authStorage.getToken())
        authStorage.setUser(currentUser)
        setUser(currentUser)
      } catch (requestError) {
        authStorage.clear()
        navigate('/login', { replace: true })
      }
    }

    loadCurrentUser()
    loadProjects()
  }, [navigate])

  async function handleCreateProject(form) {
    setCreateError('')
    setIsCreating(true)
    try {
      await createProject(form, authStorage.getToken())
      setIsCreateOpen(false)
      setFeedback('Project created successfully.')
      await loadProjects()
    } catch (requestError) {
      if (!handleUnauthorized(requestError)) {
        setCreateError(requestError.status === 422 ? 'Enter a valid project name and description.' : 'Unable to create project.')
      }
    } finally {
      setIsCreating(false)
    }
  }

  async function handleDeleteProject(project) {
    if (!window.confirm('Are you sure you want to delete this project?')) return

    setError('')
    setFeedback('')
    try {
      await deleteProject(project.id, authStorage.getToken())
      setProjects((current) => current.filter((item) => item.id !== project.id))
      setFeedback('Project deleted successfully.')
    } catch (requestError) {
      if (!handleUnauthorized(requestError)) {
        setError('Unable to delete project. Please try again.')
      }
    }
  }

  function logout() {
    authStorage.clear()
    navigate('/login')
  }

  if (!user) {
    return <main className="dashboard-page">Loading dashboard…</main>
  }

  return (
    <main className="dashboard-page">
      <section className="dashboard-shell">
        <header className="dashboard-header">
          <span className="app-title">Web IDE AI Debugger</span>
          <button type="button" className="secondary-button" onClick={logout}>Logout</button>
        </header>
        <div className="dashboard-content">
          <h1>Welcome, {user.name}</h1>
          <div className="projects-heading">
            <h2>My Projects</h2>
            <button type="button" onClick={() => { setCreateError(''); setIsCreateOpen(true) }}>+ New Project</button>
          </div>
          {feedback && <p className="success-message" role="status">{feedback}</p>}
          {error && <p className="error-message" role="alert">{error}</p>}
          {isLoading ? (
            <p className="dashboard-copy">Loading projects...</p>
          ) : projects.length === 0 ? (
            <p className="dashboard-copy">You don&apos;t have any projects yet.</p>
          ) : (
            <div className="project-grid">
              {projects.map((project) => (
                <article className="project-card" key={project.id}>
                  <h3>{project.name}</h3>
                  <p>{project.description || 'No description provided.'}</p>
                  <small>Last updated {new Date(project.updated_at).toLocaleString()}</small>
                  <div className="project-actions">
                    <button type="button" onClick={() => navigate(`/projects/${project.id}`)}>Open</button>
                    <button type="button" className="danger-button" onClick={() => handleDeleteProject(project)}>Delete</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
      {isCreateOpen && (
        <CreateProjectModal
          error={createError}
          isSubmitting={isCreating}
          onClose={() => setIsCreateOpen(false)}
          onCreate={handleCreateProject}
        />
      )}
    </main>
  )
}

export default Dashboard
