import React from "react";
import { CLINICA } from "../config/clinica";

/**
 * Marca do sistema: logo oficial da Med Flow (imagem em
 * /branding/logo-medflow-icon.png) + nome da clínica.
 *
 * As imagens ficam em `public/branding/` para poderem ser referenciadas
 * por caminho absoluto (`/branding/...`) tanto aqui quanto no favicon
 * (index.html) e na nota fiscal/recibo (ReciboModal), sem duplicar o
 * arquivo em vários lugares.
 */
export function LogoMark({ size = 40 }) {
  return (
    <img
      src="/branding/logo-medflow-icon.png"
      alt={`Logo ${CLINICA.nome}`}
      className="shrink-0 rounded-2xl object-cover shadow-card"
      style={{ width: size, height: size }}
    />
  );
}

export function Logo({ size = 40, withText = true }) {
  return (
    <div className="flex items-center gap-3">
      <LogoMark size={size} />
      {withText && (
        <div className="leading-tight">
          <p className="font-semibold text-ink-900" style={{ fontSize: size * 0.42 }}>
            {CLINICA.nome}
          </p>
          <p className="text-ink-300 text-xs -mt-0.5">Clínica Odontológica</p>
        </div>
      )}
    </div>
  );
}
