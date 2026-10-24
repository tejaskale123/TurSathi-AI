import { Navigate, useLocation } from 'react-router-dom';
import { tokenService } from '../../services/tokenService.js';

export function ProtectedRoute({ children }) {
  const location = useLocation();
  const authenticated = tokenService.isAuthenticated();

  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export default ProtectedRoute;
