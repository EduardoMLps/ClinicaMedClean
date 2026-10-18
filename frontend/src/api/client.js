/**
 * Cliente HTTP central do sistema.
 *
 * Todas as páginas devem importar este módulo e usá-lo assim:
 *   import api from '../api/client';
 *   api.get('/pacientes');
 *   api.post('/pacientes', body);
 *   api.put('/pacientes/:id', body);
 *   api.delete('/pacientes/:id');
 *
 * O header Authorization: Bearer <token> é injetado automaticamente a partir
 * do token guardado em memória (ver src/context/AuthContext.jsx). Em caso de
 * resposta 401 (token inválido/expirado), o client dispara um evento global
 * que o AuthProvider escuta para fazer logout automático — sem precisar de
 * import circular entre client.js e AuthContext.jsx.
 */
import axios from "axios";

export const AUTH_LOGOUT_EVENT = "auth:logout";

// Guarda o token em memória (fora do React), para o interceptor conseguir
// acessá-lo de forma síncrona sem depender de contexto/hooks.
let currentToken = null;

export function setAuthToken(token) {
  currentToken = token;
}

export function getAuthToken() {
  return currentToken;
}

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (currentToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${currentToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      // Token expirado/ inválido: limpa o token local e avisa o AuthProvider
      // para fazer logout e redirecionar para /login.
      currentToken = null;
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
      }
    }
    return Promise.reject(error);
  }
);

export default api;
