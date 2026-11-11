import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Crucial for HTTP-only cookie session authentication
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Response interceptor for consistent error extraction
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An unexpected error occurred. Please try again.';

    if (error.response) {
      // Backend FastAPI HTTPException returns { "detail": ... }
      const data = error.response.data;
      if (typeof data?.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data?.detail)) {
        // Pydantic validation errors format: [{ loc, msg, type }]
        message = data.detail.map((err) => err.msg || `${err.loc?.join('.')} is invalid`).join(', ');
      } else if (data?.message) {
        message = data.message;
      }
    } else if (error.request) {
      message = 'Unable to connect to FinAdvisor server. Please ensure the backend is running.';
    }

    const customError = new Error(message);
    customError.status = error.response?.status;
    customError.response = error.response;
    return Promise.reject(customError);
  }
);

export default api;
