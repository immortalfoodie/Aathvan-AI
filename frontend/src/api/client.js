/**
 * Axios HTTP client with JWT interceptor.
 *
 * The token is stored in-memory via a module-level variable.
 * This is more secure than localStorage (immune to XSS reading the token),
 * but means the user will be logged out on page refresh.
 *
 * ⚠️ PLACEHOLDER: For production, replace with httpOnly cookie-based auth
 * and a token refresh flow.
 */
import axios from "axios";

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = null;
}

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT to every outgoing request
client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Handle 401 responses globally
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAccessToken();
      // Let the auth context handle redirect
    }
    return Promise.reject(error);
  }
);

export default client;
