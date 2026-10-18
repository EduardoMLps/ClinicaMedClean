/**
 * Dados institucionais da clínica, usados em vários pontos do sistema
 * (rodapé, botão do WhatsApp, recibo/nota fiscal, tela de login).
 *
 * Centralizado aqui para não haver risco de divergência entre as telas
 * caso algum dado mude no futuro (telefone, endereço, etc.).
 */

export const CLINICA = {
  nome: "Med Flow",
  nomeCompleto: "Med Flow — Clínica Odontológica",
  cnpj: "30.888.223/0001-99",
  endereco: "Rua Dom Pedro I, 80, Curitiba - PR",
  email: "pedro.augusto@medflow.com.br",
  whatsapp: {
    numeroExibicao: "(41) 99740-2973",
    // Formato internacional exigido pelo wa.me (55 = Brasil, sem 0/9 extra).
    numeroInternacional: "5541997402973",
  },
};

// Link do WhatsApp já com uma mensagem inicial pronta.
export const linkWhatsApp = (mensagem = "Olá! Vim pelo sistema da Med Flow e gostaria de falar com a clínica.") =>
  `https://wa.me/${CLINICA.whatsapp.numeroInternacional}?text=${encodeURIComponent(mensagem)}`;

// Link do Google Maps a partir do endereço (abre o app de mapas no celular
// ou o Google Maps no navegador, sem precisar de API key).
export const linkMapa = () =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(CLINICA.endereco)}`;

export const linkEmail = () => `mailto:${CLINICA.email}`;
