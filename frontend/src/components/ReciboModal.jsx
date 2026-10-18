/**
 * Recibo / nota fiscal de pagamento, com a logo e os dados institucionais
 * da Med Flow. Abre como modal e pode ser impresso (ou salvo em PDF pelo
 * diálogo de impressão do navegador) através do botão "Imprimir".
 *
 * Observação técnica: este recibo NÃO é uma NF-e (nota fiscal eletrônica)
 * emitida junto à Receita/Sefaz — é um comprovante interno de pagamento.
 * Emissão de NF-e de verdade exige integração com um emissor fiscal
 * homologado (ex.: certificado digital + provedor de NF-e/NFS-e da
 * prefeitura), o que está fora do escopo deste protótipo.
 */
import React, { useEffect, useState } from "react";
import api from "../api/client";
import { CLINICA } from "../config/clinica";

function formatarMoeda(valor) {
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "R$ 0,00";
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarData(valor) {
  if (!valor) return "—";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleDateString("pt-BR");
}

const LABEL_FORMA = {
  dinheiro: "Dinheiro",
  cartao: "Cartão",
  pix: "Pix",
  convenio: "Convênio",
};

export default function ReciboModal({ conta, pacientesPorId, onFechar }) {
  const [pagamento, setPagamento] = useState(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (!conta) {
      setPagamento(null);
      return;
    }
    if (!conta.orcamento_id) return;

    let ativo = true;
    setCarregando(true);
    api
      .get("/pagamentos", { params: { orcamento_id: conta.orcamento_id } })
      .then(({ data }) => {
        if (!ativo) return;
        const lista = Array.isArray(data) ? data : data?.dados || [];
        // Um orçamento pode ter mais de uma conta/pagamento (parcelas);
        // tenta casar pelo valor exato e, na falta disso, usa o mais recente.
        const match =
          lista.find((p) => Number(p.valor) === Number(conta.valor)) ||
          lista.sort((a, b) => new Date(b.pago_em) - new Date(a.pago_em))[0] ||
          null;
        setPagamento(match);
      })
      .catch(() => setPagamento(null))
      .finally(() => ativo && setCarregando(false));

    return () => {
      ativo = false;
    };
  }, [conta]);

  if (!conta) return null;

  const nomePaciente =
    conta.paciente_nome || conta.paciente?.nome || pacientesPorId?.[conta.paciente_id] || "—";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 px-4 py-8 print:bg-white print:px-0 print:py-0">
      <div className="max-h-full w-full max-w-lg overflow-y-auto rounded-xl2 bg-white shadow-card print:max-w-none print:rounded-none print:shadow-none">
        {/* Barra de ações — some na impressão */}
        <div className="flex items-center justify-between border-b border-brand-100 px-6 py-4 print:hidden">
          <h2 className="text-lg font-semibold text-ink-900">Recibo de pagamento</h2>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => window.print()} className="btn-primary !px-3.5 !py-2 text-xs">
              Imprimir / salvar PDF
            </button>
            <button
              type="button"
              onClick={onFechar}
              className="grid h-8 w-8 place-items-center rounded-full text-ink-500 transition hover:bg-brand-50"
              aria-label="Fechar"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Conteúdo imprimível */}
        <div className="px-8 py-8">
          <div className="mb-6 flex items-center gap-3 border-b border-brand-100 pb-6">
            <img src="/branding/logo-medflow-icon.png" alt={`Logo ${CLINICA.nome}`} className="h-14 w-14 rounded-2xl object-cover" />
            <div>
              <p className="text-lg font-semibold text-ink-900">{CLINICA.nome}</p>
              <p className="text-xs text-ink-500">Clínica Odontológica</p>
              <p className="text-xs text-ink-500">CNPJ {CLINICA.cnpj}</p>
              <p className="text-xs text-ink-500">{CLINICA.endereco}</p>
            </div>
          </div>

          <p className="mb-1 text-xs uppercase tracking-wide text-ink-300">Recibo nº</p>
          <p className="mb-5 font-mono text-sm text-ink-700">
            {String(pagamento?.id || conta.id).padStart(6, "0")}
          </p>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-ink-300">Paciente</dt>
              <dd className="font-medium text-ink-900">{nomePaciente}</dd>
            </div>
            <div>
              <dt className="text-ink-300">Valor pago</dt>
              <dd className="font-medium text-ink-900">{formatarMoeda(pagamento?.valor ?? conta.valor)}</dd>
            </div>
            <div>
              <dt className="text-ink-300">Forma de pagamento</dt>
              <dd className="font-medium text-ink-900">
                {carregando ? "—" : LABEL_FORMA[pagamento?.forma] || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-ink-300">Data do pagamento</dt>
              <dd className="font-medium text-ink-900">
                {carregando ? "—" : formatarData(pagamento?.pago_em) || formatarData(conta.vencimento)}
              </dd>
            </div>
          </dl>

          <p className="mt-8 text-xs leading-relaxed text-ink-300">
            Este documento é um comprovante interno de pagamento emitido pela {CLINICA.nome}
            {" "}e não substitui nota fiscal eletrônica (NF-e/NFS-e).
          </p>

          <p className="mt-6 text-center text-xs text-ink-300">
            {CLINICA.nome} • {CLINICA.endereco} • {CLINICA.email}
          </p>
        </div>
      </div>
    </div>
  );
}
