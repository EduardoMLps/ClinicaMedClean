/**
 * Roteamento principal do sistema.
 *
 * Rotas públicas: /login
 * Rotas protegidas (exigem sessão autenticada): /, /pacientes, /agenda,
 * /prontuario, /financeiro, /estoque — qualquer usuário não autenticado é
 * redirecionado para /login, guardando a rota de origem para retomar depois
 * do login.
 *
 * As páginas ainda não implementadas por outros módulos são referenciadas
 * normalmente pelo import (mesmo caminho/nome de arquivo) — os demais
 * agentes do time vão criá-las em paralelo.
 */
import React from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Pacientes from "./pages/Pacientes";
import Agenda from "./pages/Agenda";
import Prontuario from "./pages/Prontuario";
import Financeiro from "./pages/Financeiro";
import Estoque from "./pages/Estoque";

function RotaProtegida({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <RotaProtegida>
            <Dashboard />
          </RotaProtegida>
        }
      />
      <Route
        path="/pacientes"
        element={
          <RotaProtegida>
            <Pacientes />
          </RotaProtegida>
        }
      />
      <Route
        path="/agenda"
        element={
          <RotaProtegida>
            <Agenda />
          </RotaProtegida>
        }
      />
      <Route
        path="/prontuario"
        element={
          <RotaProtegida>
            <Prontuario />
          </RotaProtegida>
        }
      />
      <Route
        path="/financeiro"
        element={
          <RotaProtegida>
            <Financeiro />
          </RotaProtegida>
        }
      />
      <Route
        path="/estoque"
        element={
          <RotaProtegida>
            <Estoque />
          </RotaProtegida>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
