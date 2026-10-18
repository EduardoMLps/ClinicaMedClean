import React from "react";

/**
 * Ilustração decorativa para a tela de login / estados vazios.
 * Composição própria (sem imagens externas): dente sorridente sobre blob
 * verde, com um "cartão de agenda" flutuante — reforça a identidade visual
 * verde + azul-marinho do sistema em qualquer resolução (é um SVG puro).
 */
export function HeroIllustration({ className = "" }) {
  return (
    <svg viewBox="0 0 420 420" className={className} role="img" aria-label="Ilustração da clínica odontológica">
      <defs>
        <linearGradient id="blobGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4CD388" />
          <stop offset="100%" stopColor="#0F7347" />
        </linearGradient>
        <linearGradient id="cardGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#F0FDF6" />
        </linearGradient>
      </defs>

      {/* Blob de fundo */}
      <path
        fill="url(#blobGrad)"
        opacity="0.16"
        d="M210 40c58 0 118 26 148 78 28 49 18 116-24 156-45 43-116 55-176 37-56-17-101-63-112-121-11-59 16-123 68-150 30-16 62-0 96 0Z"
      />
      <circle cx="335" cy="90" r="14" fill="#22B36B" opacity="0.35" />
      <circle cx="55" cy="330" r="20" fill="#0B1730" opacity="0.08" />
      <circle cx="70" cy="70" r="9" fill="#22B36B" opacity="0.5" />

      {/* Cadeira/base circular central */}
      <ellipse cx="210" cy="330" rx="120" ry="18" fill="#0B1730" opacity="0.06" />

      {/* Personagem: dente sorridente */}
      <g transform="translate(120,110)">
        <path
          d="M90 0C55 0 40 18 22 18 10 18-8 8-24 26c-20 23-18 62-6 100 12 39 30 84 46 112 8 14 18 24 32 24 22 0 20-38 32-66 5-11 11-17 20-17s15 6 20 17c12 28 10 66 32 66 14 0 24-10 32-24 16-28 34-73 46-112 12-38 14-77-6-100-16-18-34-8-46-8C140 18 125 0 90 0Z"
          fill="#FFFFFF"
          stroke="#0F7347"
          strokeWidth="4"
        />
        {/* rosto */}
        <circle cx="62" cy="95" r="7" fill="#0B1730" />
        <circle cx="118" cy="95" r="7" fill="#0B1730" />
        <path d="M58 128c10 16 22 24 34 24s24-8 34-24" stroke="#22B36B" strokeWidth="6" fill="none" strokeLinecap="round" />
        {/* bochechas */}
        <circle cx="40" cy="112" r="10" fill="#4CD388" opacity="0.35" />
        <circle cx="140" cy="112" r="10" fill="#4CD388" opacity="0.35" />
      </g>

      {/* Cartão flutuante: agenda confirmada */}
      <g transform="translate(255,235)">
        <rect x="0" y="0" width="130" height="70" rx="16" fill="url(#cardGrad)" stroke="#DCFCE9" strokeWidth="2" />
        <circle cx="24" cy="24" r="12" fill="#22B36B" />
        <path d="M18 24l4 4 8-8" stroke="#FFFFFF" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="44" y="16" width="70" height="8" rx="4" fill="#0B1730" opacity="0.75" />
        <rect x="44" y="32" width="52" height="6" rx="3" fill="#7C8CA8" />
        <rect x="14" y="48" width="102" height="8" rx="4" fill="#DCFCE9" />
      </g>

      {/* Estrela/brilho decorativo */}
      <path d="M330 200l4 10 10 4-10 4-4 10-4-10-10-4 10-4 4-10Z" fill="#22B36B" opacity="0.6" />
      <path d="M60 210l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z" fill="#0F7347" opacity="0.4" />
    </svg>
  );
}
