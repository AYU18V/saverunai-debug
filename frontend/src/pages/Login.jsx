import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authStorage, loginUser } from '../services/api.js'

function loginErrorMessage(requestError) {
  if (requestError.status === 401) return 'Invalid email or password.'
  if (requestError.status === 422) return 'Enter a valid email and password.'
  if (requestError.status === 503) return 'The database is temporarily unavailable. Please try again shortly.'
  if (requestError.status === 500) return 'The authentication service is unavailable. Please try again later.'
  return requestError.message
}

function Login() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!form.email || !form.password) {
      setError('Email and password are required.')
      return
    }

    setIsSubmitting(true)
    try {
      const response = await loginUser(form)
      authStorage.setSession({ token: response.access_token, user: response.user })
      navigate('/dashboard')
    } catch (requestError) {
      setError(loginErrorMessage(requestError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <h1 id="login-title">Login</h1>
        <p className="subtitle">Continue to Web IDE AI Debugger.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input name="email" type="email" value={form.email} onChange={updateField} autoComplete="email" />
          </label>
          <label>
            Password
            <input name="password" type="password" value={form.password} onChange={updateField} autoComplete="current-password" />
          </label>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Logging in…' : 'Login'}
          </button>
        </form>
        <p className="form-link">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </section>
    </main>
  )
}

export default Login
