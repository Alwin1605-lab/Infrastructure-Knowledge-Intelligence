import { useAuth } from '../context/AuthContext';

/**
 * Hook to check if the current user has specific roles/permissions
 * @returns {Object} { hasRole, isDeveloper, isAdmin }
 */
export const useRole = () => {
  const { user } = useAuth();
  
  const hasRole = (role) => {
    if (!user) return false;
    // Assuming backend returns an array of roles or a single role string
    if (Array.isArray(user.roles)) {
      return user.roles.includes(role) || user.roles.includes('admin'); // admin overrides
    }
    return user.role === role || user.role === 'admin';
  };

  return {
    hasRole,
    isDeveloper: hasRole('developer'),
    isAdmin: hasRole('admin'),
    isViewer: hasRole('viewer'),
    isEditor: hasRole('editor'),
  };
};
