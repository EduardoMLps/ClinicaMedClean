/**
 * Biblioteca de ícones do sistema — linha fina, cor herdada via `currentColor`.
 * Uso: <IconTooth className="w-6 h-6 text-brand-600" />
 * Mantém o sistema visual 100% consistente entre as telas sem depender de
 * bibliotecas externas (nenhum pacote de ícones precisa ser instalado).
 */
import React from "react";

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  viewBox: "0 0 24 24",
};

export function IconTooth(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3c-2.2 0-3.2 1.1-4.2 1.1C6.4 4.1 5 3.4 3.9 4.4 2.6 5.6 2.7 8 3.3 10.4c.6 2.4 1.6 5.6 2.5 7.7.5 1.2 1 2 1.9 2 1.4 0 1.3-2.8 2.1-4.9.3-.9.7-1.4 1.2-1.4.5 0 .9.5 1.2 1.4.8 2.1.7 4.9 2.1 4.9.9 0 1.4-.8 1.9-2 .9-2.1 1.9-5.3 2.5-7.7.6-2.4.7-4.8-.6-6-1.1-1-2.5-.3-3.9-.3-1-.1-2-1.1-4.2-1.1Z" />
    </svg>
  );
}

export function IconCalendar(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M3.5 9.5h17M8 3v3.2M16 3v3.2" />
      <path d="M8.2 14l2 2 4-4.2" />
    </svg>
  );
}

export function IconChart(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </svg>
  );
}

export function IconWallet(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3.5 7.5A2.5 2.5 0 0 1 6 5h11a1.5 1.5 0 0 1 1.5 1.5V8" />
      <rect x="3.5" y="7.5" width="17" height="12" rx="2.5" />
      <circle cx="16" cy="13.5" r="1.4" />
    </svg>
  );
}

export function IconBox(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3.5 8.2 12 4l8.5 4.2v7.6L12 20l-8.5-4.2Z" />
      <path d="M3.5 8.2 12 12l8.5-4.2M12 12v8" />
    </svg>
  );
}

export function IconStethoscope(props) {
  return (
    <svg {...base} {...props}>
      <path d="M6 3v5.5a4.5 4.5 0 0 0 9 0V3" />
      <path d="M6 3H4.3M15 3h1.7" />
      <path d="M15 8.5V12a6 6 0 0 1-12 0V8.5" />
      <circle cx="19" cy="12.5" r="2.3" />
      <path d="M19 10.2V9" />
    </svg>
  );
}

export function IconSmile(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 13.5c1 1.7 2.3 2.5 4 2.5s3-.8 4-2.5" />
      <path d="M8.5 9.5h.01M15.5 9.5h.01" strokeWidth="2.6" />
    </svg>
  );
}

export function IconUsers(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.8 20c.6-3.4 3-5.4 6.2-5.4s5.6 2 6.2 5.4" />
      <path d="M16 4.6c1.6.4 2.7 1.8 2.7 3.4 0 1.6-1.1 3-2.7 3.4M19 14.9c2 .5 3.4 2.1 3.8 5.1" />
    </svg>
  );
}

export function IconLogout(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 4.5H6A2.5 2.5 0 0 0 3.5 7v10A2.5 2.5 0 0 0 6 19.5h3" />
      <path d="M14.5 16 19 12l-4.5-4M19 12H9" />
    </svg>
  );
}

export function IconBell(props) {
  return (
    <svg {...base} {...props}>
      <path d="M6 10a6 6 0 1 1 12 0c0 4.2 1.2 5.7 1.9 6.5H4.1C4.8 15.7 6 14.2 6 10Z" />
      <path d="M9.7 19.5a2.3 2.3 0 0 0 4.6 0" />
    </svg>
  );
}

export function IconSearch(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M20 20l-4.5-4.5" />
    </svg>
  );
}

export function IconPlus(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconClipboard(props) {
  return (
    <svg {...base} {...props}>
      <rect x="5" y="4.5" width="14" height="16" rx="2" />
      <rect x="8.5" y="3" width="7" height="3" rx="1.2" />
      <path d="M8.5 11h7M8.5 14.5h7M8.5 18h4" />
    </svg>
  );
}

export function IconFile(props) {
  return (
    <svg {...base} {...props}>
      <path d="M7 3.5h7.5L18.5 8V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h4.5" />
      <path d="M9 13h6M9 16.3h6" />
    </svg>
  );
}

export function IconLock(props) {
  return (
    <svg {...base} {...props}>
      <rect x="5" y="10.5" width="14" height="9.5" rx="2" />
      <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
      <circle cx="12" cy="15" r="1.4" />
    </svg>
  );
}

export function IconMapPin(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 21s-7-6.3-7-11.5a7 7 0 0 1 14 0C19 14.7 12 21 12 21Z" />
      <circle cx="12" cy="9.5" r="2.4" />
    </svg>
  );
}

export function IconMail(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2.2" />
      <path d="m3.5 6 8.5 7 8.5-7" />
    </svg>
  );
}

export function IconPrinter(props) {
  return (
    <svg {...base} {...props}>
      <path d="M7 8.5V4h10v4.5" />
      <rect x="4" y="8.5" width="16" height="8" rx="1.8" />
      <path d="M7 15h10v5H7z" />
    </svg>
  );
}

/** Ícone do WhatsApp em cor sólida (não segue currentColor no glifo interno). */
export function IconWhatsapp(props) {
  return (
    <svg viewBox="0 0 32 32" {...props}>
      <path
        fill="currentColor"
        d="M16 3.5C9.1 3.5 3.5 9.1 3.5 16c0 2.4.68 4.66 1.86 6.58L3.5 28.5l6.1-1.83A12.44 12.44 0 0 0 16 28.5c6.9 0 12.5-5.6 12.5-12.5S22.9 3.5 16 3.5Zm0 22.7c-2.1 0-4.06-.6-5.72-1.63l-.41-.24-4.05 1.22 1.25-3.94-.27-.42A10.18 10.18 0 0 1 5.8 16c0-5.63 4.58-10.2 10.2-10.2S26.2 10.38 26.2 16 21.63 26.2 16 26.2Z"
      />
      <path
        fill="currentColor"
        d="M21.6 18.3c-.3-.15-1.77-.87-2.05-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.16-.17.2-.35.22-.65.07-.3-.15-1.24-.46-2.37-1.46-.88-.78-1.47-1.75-1.64-2.05-.17-.3-.02-.46.13-.6.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.6-.92-2.2-.24-.58-.49-.5-.67-.5-.17 0-.37-.02-.57-.02s-.52.07-.8.37c-.27.3-1.05 1.03-1.05 2.5s1.08 2.9 1.23 3.1c.15.2 2.13 3.25 5.16 4.56.72.31 1.28.5 1.72.64.72.23 1.38.2 1.9.12.58-.09 1.77-.72 2.02-1.42.25-.7.25-1.3.17-1.42-.07-.13-.27-.2-.57-.35Z"
      />
    </svg>
  );
}
