export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const TOKEN_KEY = 'web-ide-auth-token'
const USER_KEY = 'web-ide-auth-user'

export class ApiRequestError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    const user = localStorage.getItem(USER_KEY)
    return user ? JSON.parse(user) : null
  },
  setSession: ({ token, user }) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  setUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}

export const registerUser = (user) => apiRequest('/api/auth/register', { method: 'POST', body: user })

export const loginUser = (credentials) => apiRequest('/api/auth/login', { method: 'POST', body: credentials })

export const getCurrentUser = (token) => apiRequest('/api/auth/me', { token })

export const createProject = (project, token) => apiRequest('/api/projects', { method: 'POST', body: project, token })

export const getProjects = (token) => apiRequest('/api/projects', { token })

export const getProject = (projectId, token) => apiRequest(`/api/projects/${projectId}`, { token })

export const updateProject = (projectId, project, token) => apiRequest(`/api/projects/${projectId}`, {
  method: 'PUT',
  body: project,
  token,
})

export const deleteProject = (projectId, token) => apiRequest(`/api/projects/${projectId}`, {
  method: 'DELETE',
  token,
})

const encodedFilePath = (path) => path.split('/').map(encodeURIComponent).join('/')

export const getProjectFiles = (projectId, token) => apiRequest(`/api/projects/${projectId}/files`, { token })
export const createProjectFile = (projectId, file, token) => apiRequest(`/api/projects/${projectId}/files`, { method: 'POST', body: file, token })
export const updateProjectFile = (projectId, path, file, token) => apiRequest(`/api/projects/${projectId}/files/${encodedFilePath(path)}`, { method: 'PUT', body: file, token })
export const deleteProjectFile = (projectId, path, token) => apiRequest(`/api/projects/${projectId}/files/${encodedFilePath(path)}`, { method: 'DELETE', token })
export const renameProjectFile = (projectId, path, newPath, token) => apiRequest(`/api/projects/${projectId}/files/${encodedFilePath(path)}`, { method: 'PATCH', body: { new_path: newPath }, token })
export const runCode = (payload, token) => apiRequest('/api/execution/run', { method: 'POST', body: payload, token })
export const startWorkspace = (projectId, token) => apiRequest(`/api/workspaces/${projectId}/start`, { method: 'POST', token })
export const getWorkspaceStatus = (projectId, token) => apiRequest(`/api/workspaces/${projectId}/status`, { token })

export function terminalUrl(projectId, token) {
  const url = new URL(`/api/terminal/${projectId}`, API_BASE_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  return url.toString()
}

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' }
  if (body) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await response.json().catch(() => ({}))

  if (import.meta.env.DEV && path === '/api/execution/run') {
    console.log('Execution request status:', response.status)
  }

  if (!response.ok) {
    if (response.status === 401) {
      authStorage.clear()
    }
    throw new ApiRequestError(data.detail || 'Something went wrong. Please try again.', response.status)
  }

  return data
}
