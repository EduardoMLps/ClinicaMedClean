/**
 * Layout padrão das telas autenticadas.
 *
 * Contrato de props (não quebrar — outros módulos dependem disso):
 *   <Layout title="Nome da página">{children}</Layout>
 *
 * Sidebar fixa à esquerda (bg-ink-900) com a logo, navegação principal e
 * botão de sair. Área de conteúdo com fundo brand-50 e cabeçalho com o
 * título da página + sino de notificações.
 */
import React from "react";
import { NavLink } from "react-router-dom";
import { Logo, LogoMark } from "../assets/Logo";
import {
  IconCalendar,
  IconChart,
  IconWallet,
  IconBox,
  IconStethoscope,
  IconUsers,
  IconLogout,
  IconBell,
} from "../assets/icons";
import { useAuth } from "../context/AuthContext";
import { CLINICA } from "../config/clinica";
import ClinicFooter from "./ClinicFooter";
import WhatsAppButton from "./WhatsAppButton";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: IconChart, end: true },
  { to: "/pacientes", label: "Pacientes", icon: IconUsers },
  { to: "/agenda", label: "Agenda", icon: IconCalendar },
  { to: "/prontuario", label: "Prontuário", icon: IconStethoscope },
  { to: "/financeiro", label: "Financeiro", icon: IconWallet },
  { to: "/estoque", label: "Estoque", icon: IconBox },
];

export default function Layout({ children, title }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-brand-50">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col bg-ink-900 px-4 py-6">
        <div className="mb-8 px-2">
          <LogoMark size={40} />
          <p className="mt-3 text-lg font-semibold leading-tight text-white">
            {CLINICA.nome}
          </p>
          <p className="text-xs text-brand-200/70">Clínica Odontológica</p>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
            >
              <Icon className="h-5 w-5" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto border-t border-white/10 pt-4">
          {user?.nome && (
            <p className="mb-2 truncate px-3.5 text-xs text-brand-200/70">
              {user.nome}
            </p>
          )}
          <button
            type="button"
            onClick={logout}
            className="sidebar-link w-full text-left"
          >
            <IconLogout className="h-5 w-5" />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      {/* Conteúdo */}
      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-brand-100 bg-white px-8 py-5">
          <h1 className="text-xl font-semibold text-ink-900">{title}</h1>
          <button
            type="button"
            aria-label="Notificações"
            className="grid h-10 w-10 place-items-center rounded-full bg-brand-50 text-ink-700 transition hover:bg-brand-100"
          >
            <IconBell className="h-5 w-5" />
          </button>
        </header>

        <main className="flex-1 bg-brand-50 px-8 py-8">{children}</main>

        <div className="border-t border-brand-100 bg-white">
          <ClinicFooter variant="light" />
        </div>
      </div>

      <WhatsAppButton />
    </div>
  );
}

// Exporta a logo original também, caso alguma tela queira usá-la fora da sidebar.
export { Logo };
