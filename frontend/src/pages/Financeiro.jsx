/**
 * Tela de Financeiro.
 *
 * Reúne três blocos:
 *  - Resumo do mês (cards com total recebido, a receber e inadimplência),
 *    alimentado por GET /financeiro/resumo.
 *  - Orçamentos: lista com status colorido e botão para aprovar
 *    (POST /financeiro/orcamentos/:id/aprovar).
 *  - Contas a Receber: lista com vencimento/status e botão para registrar
 *    pagamento (POST /financeiro/contas-a-receber/:id/pagamento).
 *
 * Segue o design system do projeto (brand/ink, classes utilitárias
 * .card/.btn-primary/.btn-secondary/.input/.label/.badge).
 */
import React, { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import { IconWallet, IconChart, IconClipboard, IconFile } from "../assets/icons";
import ReciboModal from "../components/ReciboModal";

function formatarMoeda(valor) {
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "R$ 0,00";
  return numero.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatarData(valor) {
  if (!valor) return "—";
  // Aceita "YYYY-MM-DD" ou um ISO datetime completo.
  const dataISO = /^\d{4}-\d{2}-\d{2}/.test(valor) ? valor.slice(0, 10) : valor;
  const data = new Date(
    /^\d{4}-\d{2}-\d{2}$/.test(dataISO) ? `${dataISO}T00:00:00` : dataISO
  );
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

const STATUS_ORCAMENTO = {
  pendente: { label: "Pendente", className: "bg-amber-50 text-amber-700" },
  aprovado: { label: "Aprovado", className: "bg-brand-100 text-brand-800" },
  recusado: { label: "Recusado", className: "bg-rose-50 text-rose-700" },
  expirado: { label: "Expirado", className: "bg-ink-100 text-ink-500" },
};

const STATUS_CONTA = {
  pendente: { label: "Pendente", className: "bg-amber-50 text-amber-700" },
  pago: { label: "Pago", className: "bg-brand-100 text-brand-800" },
  atrasado: { label: "Atrasado", className: "bg-rose-50 text-rose-700" },
  cancelado: { label: "Cancelado", className: "bg-ink-100 text-ink-300 line-through" },
};

function StatusBadge({ status, mapa }) {
  const chave = (status || "pendente").toLowerCase();
  const config = mapa[chave] || {
    label: status || "Pendente",
    className: "bg-ink-50 text-ink-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}

// O backend não devolve o nome do paciente embutido em orçamentos/contas
// (só paciente_id) — resolvemos aqui a partir do mapa carregado à parte.
function nomeDoPaciente(item, pacientesPorId) {
  return (
    item.paciente_nome ||
    item.paciente?.nome ||
    pacientesPorId?.[item.paciente_id] ||
    "Paciente não informado"
  );
}

function ResumoCard({ icon: Icon, titulo, valor, destaque, carregando }) {
  return (
    <div className="card flex items-center gap-4">
      <div
        className={`grid h-12 w-12 shrink-0 place-items-center rounded-full ${
          destaque ? "bg-brand-600" : "bg-brand-100"
        }`}
      >
        <Icon className={`h-6 w-6 ${destaque ? "text-white" : "text-brand-600"}`} />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-ink-500">{titulo}</p>
        <p className="mt-0.5 truncate text-xl font-semibold text-ink-900">
          {carregando ? "—" : valor}
        </p>
      </div>
    </div>
  );
}

const FORMAS_PAGAMENTO = [
  { valor: "dinheiro", label: "Dinheiro" },
  { valor: "cartao", label: "Cartão" },
  { valor: "pix", label: "Pix" },
  { valor: "convenio", label: "Convênio" },
];

function RegistrarPagamentoModal({ conta, onFechar, onPago, pacientesPorId }) {
  const [forma, setForma] = useState("pix");
  const [profissionalId, setProfissionalId] = useState("");
  const [profissionais, setProfissionais] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!conta) return;
    api
      .get("/profissionais")
      .then(({ data }) => {
        const lista = Array.isArray(data) ? data : [];
        setProfissionais(lista);
        if (lista.length > 0) setProfissionalId(String(lista[0].id));
      })
      .catch(() => {});
  }, [conta]);

  useEffect(() => {
    if (conta) {
      setForma("pix");
      setErro("");
    }
  }, [conta]);

  if (!conta) return null;

  async function handleSubmit(evento) {
    evento.preventDefault();
    setErro("");

    if (!profissionalId) {
      setErro("Selecione o profissional responsável.");
      return;
    }

    setSalvando(true);
    try {
      // O backend baixa a conta pelo valor integral dela (não há
      // pagamento parcial) — por isso não enviamos "valor" aqui, só a
      // referência da conta, a forma e o profissional (para o cálculo
      // automático da comissão).
      const { data } = await api.post("/pagamentos", {
        conta_receber_id: conta.id,
        forma,
        profissional_id: Number(profissionalId),
      });
      onPago(conta.id, data);
      onFechar();
    } catch (err) {
      setErro(
        err?.response?.data?.erro ||
          "Não foi possível registrar o pagamento. Tente novamente."
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 px-4 py-8">
      <div className="w-full max-w-md rounded-xl2 bg-white p-6 shadow-card">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink-900">
            Registrar pagamento
          </h2>
          <button
            type="button"
            onClick={onFechar}
            className="grid h-8 w-8 place-items-center rounded-full text-ink-500 transition hover:bg-brand-50"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <p className="mb-4 text-sm text-ink-500">
          {nomeDoPaciente(conta, pacientesPorId)} • {formatarMoeda(conta.valor)}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="forma_pagamento">
              Forma de pagamento
            </label>
            <select
              id="forma_pagamento"
              className="input"
              value={forma}
              onChange={(e) => setForma(e.target.value)}
            >
              {FORMAS_PAGAMENTO.map((f) => (
                <option key={f.valor} value={f.valor}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="profissional_pagamento">
              Profissional responsável (para cálculo de comissão)
            </label>
            <select
              id="profissional_pagamento"
              className="input"
              value={profissionalId}
              onChange={(e) => setProfissionalId(e.target.value)}
              required
            >
              {profissionais.length === 0 && <option value="">Carregando...</option>}
              {profissionais.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}
                </option>
              ))}
            </select>
          </div>

          {erro && (
            <p className="rounded-xl bg-amber-50 px-3.5 py-2.5 text-sm text-amber-700">
              {erro}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onFechar}
              className="btn-secondary"
              disabled={salvando}
            >
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={salvando}>
              {salvando ? "Registrando..." : "Registrar pagamento"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const ABAS = [
  { chave: "orcamentos", label: "Orçamentos" },
  { chave: "contas", label: "Contas a Receber" },
];

export default function Financeiro() {
  const [abaAtiva, setAbaAtiva] = useState("orcamentos");

  // Resumo
  const [resumo, setResumo] = useState(null);
  const [carregandoResumo, setCarregandoResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState(false);

  // Orçamentos
  const [orcamentos, setOrcamentos] = useState([]);
  const [carregandoOrcamentos, setCarregandoOrcamentos] = useState(true);
  const [erroOrcamentos, setErroOrcamentos] = useState(false);
  const [aprovandoId, setAprovandoId] = useState(null);

  // Contas a receber
  const [contas, setContas] = useState([]);
  const [carregandoContas, setCarregandoContas] = useState(true);
  const [erroContas, setErroContas] = useState(false);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [contaParaRecibo, setContaParaRecibo] = useState(null);

  // Mapa paciente_id -> nome, para exibir nas listas de orçamentos/contas
  // (o backend só devolve o id nesses endpoints).
  const [pacientesPorId, setPacientesPorId] = useState({});

  useEffect(() => {
    let ativo = true;
    api
      .get("/pacientes", { params: { por_pagina: 200 } })
      .then(({ data }) => {
        if (!ativo) return;
        const lista = Array.isArray(data) ? data : data?.dados || [];
        setPacientesPorId(Object.fromEntries(lista.map((p) => [p.id, p.nome])));
      })
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, []);

  // Extraída do useEffect para poder ser chamada novamente após um
  // pagamento ser registrado (o card "Recebido no mês" precisa refletir
  // o novo pagamento sem exigir reload manual da página).
  const carregarResumo = useCallback(async () => {
    setCarregandoResumo(true);
    setErroResumo(false);
    try {
      const { data } = await api.get("/financeiro/resumo");
      setResumo(data || {});
    } catch (err) {
      setErroResumo(true);
    } finally {
      setCarregandoResumo(false);
    }
  }, []);

  useEffect(() => {
    carregarResumo();
  }, [carregarResumo]);

  useEffect(() => {
    let ativo = true;

    async function carregarOrcamentos() {
      setCarregandoOrcamentos(true);
      setErroOrcamentos(false);
      try {
        const { data } = await api.get("/orcamentos", { params: { por_pagina: 100 } });
        if (ativo) {
          setOrcamentos(Array.isArray(data) ? data : data?.dados || []);
        }
      } catch (err) {
        if (ativo) setErroOrcamentos(true);
      } finally {
        if (ativo) setCarregandoOrcamentos(false);
      }
    }

    carregarOrcamentos();
    return () => {
      ativo = false;
    };
  }, []);

  // Extraída para poder ser chamada novamente após aprovar um orçamento
  // (que cria novas contas a receber) ou registrar um pagamento.
  const carregarContas = useCallback(async () => {
    setCarregandoContas(true);
    setErroContas(false);
    try {
      const { data } = await api.get("/contas-receber", { params: { por_pagina: 100 } });
      setContas(Array.isArray(data) ? data : data?.dados || []);
    } catch (err) {
      setErroContas(true);
    } finally {
      setCarregandoContas(false);
    }
  }, []);

  useEffect(() => {
    carregarContas();
  }, [carregarContas]);

  async function handleAprovarOrcamento(orcamento) {
    setAprovandoId(orcamento.id);
    try {
      // A resposta tem o formato { orcamento, plano_tratamento, contas_receber },
      // não o orçamento "achatado" — usar data.orcamento (e não espalhar o
      // envelope inteiro, que traria chaves não relacionadas ao item da lista).
      const { data } = await api.post(`/orcamentos/${orcamento.id}/aprovar`);
      setOrcamentos((atual) =>
        atual.map((item) =>
          item.id === orcamento.id ? { ...item, ...(data?.orcamento || { status: "aprovado" }) } : item
        )
      );
      // Aprovar um orçamento cria novas contas a receber: recarrega a lista
      // e o resumo para refletir isso sem exigir reload manual da página.
      carregarContas();
      carregarResumo();
    } catch (err) {
      // Falha silenciosa e discreta: mantém o status anterior na lista.
      setOrcamentos((atual) => [...atual]);
    } finally {
      setAprovandoId(null);
    }
  }

  // Importante: NÃO espalhar `dataResposta` (o objeto Pagamento devolvido
  // por POST /pagamentos) sobre o item da conta — o Pagamento tem seu
  // próprio `id` (o id do registro de pagamento, não da conta a receber),
  // e espalhá-lo por cima de `item` corromperia silenciosamente o id da
  // linha na tabela. Atualizamos apenas o status localmente e recarregamos
  // o resumo financeiro para refletir o novo valor recebido no mês.
  function handlePagamentoRegistrado(contaId) {
    setContas((atual) =>
      atual.map((item) => (item.id === contaId ? { ...item, status: "pago" } : item))
    );
    carregarResumo();
  }

  const totalRecebidoMes = resumo?.recebido_no_mes;
  const totalAReceber = resumo?.total_a_receber;
  const inadimplencia = resumo?.inadimplencia?.valor_total;
  const inadimplenciaQtd = resumo?.inadimplencia?.quantidade_contas;

  return (
    <Layout title="Financeiro">
      {/* Resumo */}
      <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <ResumoCard
          icon={IconWallet}
          titulo="Recebido no mês"
          valor={formatarMoeda(totalRecebidoMes)}
          carregando={carregandoResumo}
          destaque
        />
        <ResumoCard
          icon={IconChart}
          titulo="A receber"
          valor={formatarMoeda(totalAReceber)}
          carregando={carregandoResumo}
        />
        <ResumoCard
          icon={IconWallet}
          titulo="Inadimplência"
          valor={formatarMoeda(inadimplencia)}
          carregando={carregandoResumo}
        />
      </div>

      {erroResumo && (
        <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Não foi possível carregar o resumo financeiro agora.
        </p>
      )}

      {/* Abas */}
      <div className="mb-6 flex gap-2 border-b border-brand-100">
        {ABAS.map((aba) => (
          <button
            key={aba.chave}
            type="button"
            onClick={() => setAbaAtiva(aba.chave)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition ${
              abaAtiva === aba.chave
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-ink-500 hover:text-ink-700"
            }`}
          >
            {aba.label}
          </button>
        ))}
      </div>

      {/* Orçamentos */}
      {abaAtiva === "orcamentos" && (
        <>
          {erroOrcamentos && (
            <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
              Não foi possível carregar os orçamentos agora. Tente novamente
              em instantes.
            </p>
          )}

          {carregandoOrcamentos ? (
            <div className="card text-sm text-ink-300">
              Carregando orçamentos...
            </div>
          ) : orcamentos.length === 0 ? (
            <div className="card flex flex-col items-center gap-3 py-12 text-center">
              <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-100">
                <IconClipboard className="h-7 w-7 text-brand-600" />
              </div>
              <p className="text-sm text-ink-500">
                Nenhum orçamento cadastrado ainda.
              </p>
            </div>
          ) : (
            <div className="card overflow-hidden !p-0">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/60 text-ink-500">
                    <th className="px-5 py-3 font-medium">Paciente</th>
                    <th className="px-5 py-3 font-medium">Total</th>
                    <th className="px-5 py-3 font-medium">Criado em</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium text-right">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {orcamentos.map((orcamento, index) => {
                    const chaveStatus = (orcamento.status || "pendente").toLowerCase();
                    const pendente = chaveStatus === "pendente";
                    return (
                      <tr
                        key={orcamento.id ?? index}
                        className="border-b border-brand-50 last:border-0 hover:bg-brand-50/40"
                      >
                        <td className="px-5 py-3.5 font-medium text-ink-900">
                          {nomeDoPaciente(orcamento, pacientesPorId)}
                        </td>
                        <td className="px-5 py-3.5 text-ink-700">
                          {formatarMoeda(orcamento.total)}
                        </td>
                        <td className="px-5 py-3.5 text-ink-500">
                          {formatarData(orcamento.criado_em)}
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusBadge
                            status={orcamento.status}
                            mapa={STATUS_ORCAMENTO}
                          />
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          {pendente ? (
                            <button
                              type="button"
                              className="btn-primary !px-3.5 !py-2 text-xs"
                              disabled={aprovandoId === orcamento.id}
                              onClick={() => handleAprovarOrcamento(orcamento)}
                            >
                              {aprovandoId === orcamento.id
                                ? "Aprovando..."
                                : "Aprovar"}
                            </button>
                          ) : (
                            <span className="text-xs text-ink-300">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Contas a Receber */}
      {abaAtiva === "contas" && (
        <>
          {erroContas && (
            <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
              Não foi possível carregar as contas a receber agora. Tente
              novamente em instantes.
            </p>
          )}

          {carregandoContas ? (
            <div className="card text-sm text-ink-300">
              Carregando contas a receber...
            </div>
          ) : contas.length === 0 ? (
            <div className="card flex flex-col items-center gap-3 py-12 text-center">
              <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-100">
                <IconFile className="h-7 w-7 text-brand-600" />
              </div>
              <p className="text-sm text-ink-500">
                Nenhuma conta a receber cadastrada ainda.
              </p>
            </div>
          ) : (
            <div className="card overflow-hidden !p-0">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/60 text-ink-500">
                    <th className="px-5 py-3 font-medium">Paciente</th>
                    <th className="px-5 py-3 font-medium">Valor</th>
                    <th className="px-5 py-3 font-medium">Vencimento</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium text-right">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {contas.map((conta, index) => {
                    const chaveStatus = (conta.status || "pendente").toLowerCase();
                    const podeRegistrarPagamento =
                      chaveStatus === "pendente" || chaveStatus === "atrasado";
                    return (
                      <tr
                        key={conta.id ?? index}
                        className="border-b border-brand-50 last:border-0 hover:bg-brand-50/40"
                      >
                        <td className="px-5 py-3.5 font-medium text-ink-900">
                          {nomeDoPaciente(conta, pacientesPorId)}
                        </td>
                        <td className="px-5 py-3.5 text-ink-700">
                          {formatarMoeda(conta.valor)}
                        </td>
                        <td className="px-5 py-3.5 text-ink-500">
                          {formatarData(conta.vencimento)}
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusBadge status={conta.status} mapa={STATUS_CONTA} />
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          {podeRegistrarPagamento ? (
                            <button
                              type="button"
                              className="btn-secondary !px-3.5 !py-2 text-xs"
                              onClick={() => setContaSelecionada(conta)}
                            >
                              Registrar pagamento
                            </button>
                          ) : chaveStatus === "pago" ? (
                            <button
                              type="button"
                              className="btn-secondary !px-3.5 !py-2 text-xs"
                              onClick={() => setContaParaRecibo(conta)}
                            >
                              Emitir recibo
                            </button>
                          ) : (
                            <span className="text-xs text-ink-300">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <RegistrarPagamentoModal
        conta={contaSelecionada}
        onFechar={() => setContaSelecionada(null)}
        onPago={handlePagamentoRegistrado}
        pacientesPorId={pacientesPorId}
      />

      <ReciboModal
        conta={contaParaRecibo}
        pacientesPorId={pacientesPorId}
        onFechar={() => setContaParaRecibo(null)}
      />
    </Layout>
  );
}
