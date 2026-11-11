import api from './api';

export const authService = {
  /**
   * Register a new user.
   * Backend sets the HTTP-only session cookie automatically on success.
   */
  async register(fullName, email, password) {
    const response = await api.post('/api/v1/auth/register', {
      full_name: fullName,
      email,
      password,
    });
    return response.data;
  },

  /**
   * Log in an existing user.
   * Backend sets the HTTP-only session cookie automatically on success.
   */
  async login(email, password) {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  /**
   * Invalidate the current session and clear the session cookie.
   */
  async logout() {
    const response = await api.post('/api/v1/auth/logout');
    return response.data;
  },

  /**
   * Retrieve the currently authenticated user from the backend session.
   * Throws 401 if unauthenticated or session expired.
   */
  async getCurrentUser() {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  /**
   * Health check utility to confirm backend availability.
   */
  async checkHealth() {
    const response = await api.get('/health');
    return response.data;
  },
};
