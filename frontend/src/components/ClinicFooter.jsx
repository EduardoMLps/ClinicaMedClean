import React from "react";
import { IconMapPin, IconMail, IconWhatsapp } from "../assets/icons";
import { CLINICA, linkMapa, linkEmail, linkWhatsApp } from "../config/clinica";

/**
 * Rodapé institucional com CNPJ, endereço (clicável → abre o Google Maps
 * com a localização da clínica), WhatsApp e e-mail (clicável → abre o
 * app de e-mail padrão). Usado no Layout (todas as telas autenticadas)
 * e na tela de Login.
 */
export default function ClinicFooter({ variant = "light" }) {
  const claro = variant === "light";

  return (
    <footer
      className={`flex flex-wrap items-center justify-center gap-x-6 gap-y-2 px-4 py-4 text-xs ${
        claro ? "text-ink-300" : "text-brand-200/70"
      }`}
    >
      <span className="font-medium">
        {CLINICA.nome} • CNPJ {CLINICA.cnpj}
      </span>

      <a
        href={linkMapa()}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center gap-1.5 transition hover:underline ${
          claro ? "hover:text-ink-700" : "hover:text-white"
        }`}
        title="Ver no mapa"
      >
        <IconMapPin className="h-3.5 w-3.5" />
        {CLINICA.endereco}
      </a>

      <a
        href={linkWhatsApp()}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center gap-1.5 transition hover:underline ${
          claro ? "hover:text-ink-700" : "hover:text-white"
        }`}
        title="Falar no WhatsApp"
      >
        <IconWhatsapp className="h-3.5 w-3.5" />
        {CLINICA.whatsapp.numeroExibicao}
      </a>

      <a
        href={linkEmail()}
        className={`inline-flex items-center gap-1.5 transition hover:underline ${
          claro ? "hover:text-ink-700" : "hover:text-white"
        }`}
        title="Enviar e-mail"
      >
        <IconMail className="h-3.5 w-3.5" />
        {CLINICA.email}
      </a>
    </footer>
  );
}
