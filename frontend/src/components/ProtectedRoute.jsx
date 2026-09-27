import { Navigate } from 'react-router-dom'
import { authStorage } from '../services/api.js'

function ProtectedRoute({ children }) {
  if (!authStorage.getToken()) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default ProtectedRoute
