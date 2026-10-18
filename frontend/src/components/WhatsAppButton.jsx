import React from "react";
import { IconWhatsapp } from "../assets/icons";
import { linkWhatsApp } from "../config/clinica";

/**
 * Botão flutuante do WhatsApp, fixo no canto inferior direito da tela.
 * Abre uma nova aba em wa.me com o número da clínica já preenchido —
 * funciona tanto em desktop (abre o WhatsApp Web) quanto em celular
 * (abre o app do WhatsApp).
 */
export default function WhatsAppButton() {
  return (
    <a
      href={linkWhatsApp()}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Falar com a clínica pelo WhatsApp"
      title="Falar no WhatsApp"
      className="fixed bottom-6 right-6 z-40 grid h-14 w-14 place-items-center rounded-full bg-[#25D366] text-white shadow-lg transition hover:scale-105 hover:shadow-xl"
    >
      <IconWhatsapp className="h-7 w-7" />
    </a>
  );
}
