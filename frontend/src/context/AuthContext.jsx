/**
 * Contexto de autenticação do sistema.
 *
 * Uso nas páginas/componentes:
 *   import { useAuth } from '../context/AuthContext';
 *   const { user, token, login, logout } = useAuth();
 *   await login(email, senha);
 *
 * O JWT é mantido em memória (nunca em localStorage/sessionStorage) para
 * reduzir superfície de ataque a XSS. Isso significa que o usuário perde a
 * sessão ao recarregar a página — comportamento aceito neste estágio do
 * projeto, já que a prioridade é robustez e segurança do token.
 *
 * Login: POST /api/v1/auth/login  ->  { access_token, refresh_token, usuario }
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import api, { AUTH_LOGOUT_EVENT, setAuthToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  // Enquanto a app ainda não tentou restaurar/validar a sessão inicial.
  const [initializing, setInitializing] = useState(false);

  const login = useCallback(async (email, senha) => {
    const response = await api.post("/auth/login", { email, senha });
    const { access_token, refresh_token, usuario } = response.data || {};

    if (!access_token) {
      throw new Error("Resposta de login inválida: token de acesso ausente.");
    }

    setAuthToken(access_token);
    setToken(access_token);
    setRefreshToken(refresh_token || null);
    setUser(usuario || null);

    return usuario;
  }, []);

  // Limpa a sessão só no navegador (usado quando o servidor já recusou o token).
  const limparSessaoLocal = useCallback(() => {
    setAuthToken(null);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  // Botão "Sair": avisa o servidor para revogar o token e o refresh token
  // (correção B3) e depois limpa a sessão local, mesmo se a chamada falhar.
  const logout = useCallback(async () => {
    try {
      if (token) {
        await api.post("/auth/logout", refreshToken ? { refresh_token: refreshToken } : {});
      }
    } catch (err) {
      // Sem rede ou token já inválido: a limpeza local abaixo basta.
    } finally {
      limparSessaoLocal();
    }
  }, [token, refreshToken, limparSessaoLocal]);

  // Logout automático quando o client.js detecta um 401 em qualquer chamada.
  useEffect(() => {
    function handleForcedLogout() {
      limparSessaoLocal();
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
  }, [limparSessaoLocal]);

  const value = useMemo(
    () => ({
      user,
      token,
      refreshToken,
      isAuthenticated: Boolean(token),
      initializing,
      login,
      logout,
    }),
    [user, token, refreshToken, initializing, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de um <AuthProvider>.");
  }
  return ctx;
}

export default AuthContext;
