import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerUser } from '../services/api.js'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!form.name.trim() || !form.email || !form.password || !form.confirmPassword) {
      setError('Please complete every field.')
      return
    }
    if (!emailPattern.test(form.email)) {
      setError('Enter a valid email address.')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await registerUser({
        name: form.name,
        email: form.email,
        password: form.password,
      })
      navigate('/login')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <h1 id="register-title">Create Account</h1>
        <p className="subtitle">Start using Web IDE AI Debugger.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Name
            <input name="name" value={form.name} onChange={updateField} autoComplete="name" />
          </label>
          <label>
            Email
            <input name="email" type="email" value={form.email} onChange={updateField} autoComplete="email" />
          </label>
          <label>
            Password
            <input name="password" type="password" value={form.password} onChange={updateField} autoComplete="new-password" />
          </label>
          <label>
            Confirm Password
            <input name="confirmPassword" type="password" value={form.confirmPassword} onChange={updateField} autoComplete="new-password" />
          </label>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating Account…' : 'Create Account'}
          </button>
        </form>
        <p className="form-link">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </section>
    </main>
  )
}

export default Register
