/**
 * Tela de Agenda.
 *
 * Mostra os agendamentos do dia organizados em colunas por profissional,
 * com badges de status coloridos e um formulário rápido para criar um novo
 * agendamento (POST /agenda, com "inicio"/"fim" em ISO 8601). Segue o
 * design system do projeto.
 */
import React, { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import { IconCalendar, IconPlus } from "../assets/icons";

function hojeISO() {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = String(hoje.getMonth() + 1).padStart(2, "0");
  const dia = String(hoje.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function formatarDataExibicao(dataISO) {
  if (!dataISO) return "";
  const [ano, mes, dia] = dataISO.split("-");
  if (!ano || !mes || !dia) return dataISO;
  return `${dia}/${mes}/${ano}`;
}

function formatarHora(valor) {
  if (!valor) return "—";
  // Aceita tanto "HH:MM" / "HH:MM:SS" quanto um ISO datetime completo.
  if (/^\d{2}:\d{2}/.test(valor)) return valor.slice(0, 5);
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STATUS_CONFIG = {
  agendado: { label: "Agendado", className: "bg-ink-50 text-ink-700" },
  confirmado: { label: "Confirmado", className: "bg-brand-100 text-brand-800" },
  concluido: { label: "Concluído", className: "bg-brand-600 text-white" },
  faltou: { label: "Faltou", className: "bg-ink-100 text-ink-500" },
  cancelado: { label: "Cancelado", className: "bg-ink-100 text-ink-300 line-through" },
};

function StatusBadge({ status }) {
  const chave = (status || "agendado").toLowerCase();
  const config = STATUS_CONFIG[chave] || {
    label: status || "Agendado",
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

function nomeDoProfissional(agendamento) {
  return (
    agendamento.profissional_nome ||
    agendamento.profissional?.nome ||
    "Profissional não informado"
  );
}

function nomeDoPaciente(agendamento) {
  return (
    agendamento.paciente_nome || agendamento.paciente?.nome || "Sem paciente"
  );
}

function agruparPorProfissional(agendamentos) {
  const grupos = new Map();
  agendamentos.forEach((agendamento) => {
    const chave = agendamento.profissional_id ?? nomeDoProfissional(agendamento);
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        profissional: nomeDoProfissional(agendamento),
        itens: [],
      });
    }
    grupos.get(chave).itens.push(agendamento);
  });

  return Array.from(grupos.values()).map((grupo) => ({
    ...grupo,
    itens: [...grupo.itens].sort((a, b) =>
      formatarHora(a.hora || a.data_hora).localeCompare(
        formatarHora(b.hora || b.data_hora)
      )
    ),
  }));
}

const FORM_INICIAL = {
  paciente_id: "",
  profissional_id: "",
  data: hojeISO(),
  hora: "",
  duracao_min: "30",
};

// A API espera os campos "inicio"/"fim" como datetime ISO 8601
// (ex.: "2026-08-20T14:30:00"), não "data"/"hora" separados — monta o
// ISO local a partir do formulário e soma a duração escolhida para obter
// o horário de término.
function montarIsoLocal(dataISO, horaHHMM) {
  const [ano, mes, dia] = dataISO.split("-").map(Number);
  const [h, m] = horaHHMM.split(":").map(Number);
  const data = new Date(ano, (mes || 1) - 1, dia, h, m, 0);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}` +
    `T${pad(data.getHours())}:${pad(data.getMinutes())}:${pad(data.getSeconds())}`
  );
}

function somarMinutosIsoLocal(dataISO, horaHHMM, minutos) {
  const [ano, mes, dia] = dataISO.split("-").map(Number);
  const [h, m] = horaHHMM.split(":").map(Number);
  const data = new Date(ano, (mes || 1) - 1, dia, h, m, 0);
  data.setMinutes(data.getMinutes() + Number(minutos || 30));
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}` +
    `T${pad(data.getHours())}:${pad(data.getMinutes())}:${pad(data.getSeconds())}`
  );
}

function NovoAgendamentoModal({
  aberto,
  onFechar,
  onCriado,
  pacientes,
  profissionais,
}) {
  const [form, setForm] = useState(FORM_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (aberto) {
      setForm(FORM_INICIAL);
      setErro("");
    }
  }, [aberto]);

  if (!aberto) return null;

  function atualizarCampo(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }));
  }

  async function handleSubmit(evento) {
    evento.preventDefault();
    setErro("");

    if (!form.paciente_id || !form.profissional_id || !form.data || !form.hora) {
      setErro("Preencha paciente, profissional, data e horário.");
      return;
    }

    const payload = {
      paciente_id: Number(form.paciente_id),
      profissional_id: Number(form.profissional_id),
      inicio: montarIsoLocal(form.data, form.hora),
      fim: somarMinutosIsoLocal(form.data, form.hora, form.duracao_min),
      status: "agendado",
    };

    setSalvando(true);
    try {
      const { data } = await api.post("/agenda", payload);
      onCriado(data);
      onFechar();
    } catch (err) {
      // O backend devolve erros como { erro: "..." }, não { mensagem: "..." }.
      setErro(
        err?.response?.data?.erro ||
          "Não foi possível criar o agendamento. Tente novamente."
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 px-4 py-8">
      <div className="max-h-full w-full max-w-md overflow-y-auto rounded-xl2 bg-white p-6 shadow-card">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink-900">
            Novo agendamento
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="paciente_id">
              Paciente
            </label>
            <select
              id="paciente_id"
              className="input"
              value={form.paciente_id}
              onChange={(e) => atualizarCampo("paciente_id", e.target.value)}
              required
            >
              <option value="">Selecione o paciente</option>
              {pacientes.map((paciente) => (
                <option key={paciente.id} value={paciente.id}>
                  {paciente.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="profissional_id">
              Profissional
            </label>
            <select
              id="profissional_id"
              className="input"
              value={form.profissional_id}
              onChange={(e) =>
                atualizarCampo("profissional_id", e.target.value)
              }
              required
            >
              <option value="">Selecione o profissional</option>
              {profissionais.map((profissional) => (
                <option key={profissional.id} value={profissional.id}>
                  {profissional.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="data">
                Data
              </label>
              <input
                id="data"
                className="input"
                type="date"
                value={form.data}
                onChange={(e) => atualizarCampo("data", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="hora">
                Horário
              </label>
              <input
                id="hora"
                className="input"
                type="time"
                value={form.hora}
                onChange={(e) => atualizarCampo("hora", e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="label" htmlFor="duracao_min">
              Duração
            </label>
            <select
              id="duracao_min"
              className="input"
              value={form.duracao_min}
              onChange={(e) => atualizarCampo("duracao_min", e.target.value)}
            >
              <option value="30">30 minutos</option>
              <option value="45">45 minutos</option>
              <option value="60">1 hora</option>
              <option value="90">1h30</option>
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
              {salvando ? "Salvando..." : "Criar agendamento"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Agenda() {
  const [data, setData] = useState(hojeISO());
  const [agendamentos, setAgendamentos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);

  const [pacientes, setPacientes] = useState([]);
  const [profissionais, setProfissionais] = useState([]);

  const [modalAberto, setModalAberto] = useState(false);

  useEffect(() => {
    let ativo = true;

    async function carregarAgendamentos() {
      setCarregando(true);
      setErro(false);
      try {
        const { data: resposta } = await api.get("/agenda", {
          params: { data },
        });
        if (ativo) {
          setAgendamentos(
            Array.isArray(resposta) ? resposta : resposta?.agendamentos || []
          );
        }
      } catch (err) {
        if (ativo) setErro(true);
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    carregarAgendamentos();
    return () => {
      ativo = false;
    };
  }, [data]);

  useEffect(() => {
    let ativo = true;

    async function carregarDadosAuxiliares() {
      try {
        const { data: respostaPacientes } = await api.get("/pacientes", {
          params: { por_pagina: 200 },
        });
        if (ativo) {
          setPacientes(
            Array.isArray(respostaPacientes)
              ? respostaPacientes
              : respostaPacientes?.dados || []
          );
        }
      } catch (err) {
        // Falha silenciosa: o select de pacientes fica vazio, mas a tela
        // continua funcional.
      }

      try {
        const { data: respostaProfissionais } = await api.get(
          "/profissionais"
        );
        if (ativo) {
          setProfissionais(
            Array.isArray(respostaProfissionais)
              ? respostaProfissionais
              : respostaProfissionais?.profissionais || []
          );
        }
      } catch (err) {
        // Idem: select de profissionais fica vazio se a rota falhar.
      }
    }

    carregarDadosAuxiliares();
    return () => {
      ativo = false;
    };
  }, []);

  const grupos = useMemo(
    () => agruparPorProfissional(agendamentos),
    [agendamentos]
  );

  function handleAgendamentoCriado(novoAgendamento) {
    setAgendamentos((atual) => [...atual, novoAgendamento]);
  }

  return (
    <Layout title="Agenda">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-100">
            <IconCalendar className="h-5.5 w-5.5 text-brand-600" />
          </div>
          <div>
            <p className="text-sm text-ink-500">Agenda do dia</p>
            <p className="text-base font-semibold text-ink-900">
              {formatarDataExibicao(data)}
            </p>
          </div>
          <input
            type="date"
            className="input ml-2 w-auto"
            value={data}
            onChange={(e) => setData(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="btn-primary shrink-0"
          onClick={() => setModalAberto(true)}
        >
          <IconPlus className="h-4.5 w-4.5" />
          Novo Agendamento
        </button>
      </div>

      {erro && (
        <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Não foi possível carregar a agenda agora. Tente novamente em
          instantes.
        </p>
      )}

      {carregando ? (
        <div className="card text-sm text-ink-300">Carregando agenda...</div>
      ) : grupos.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 py-12 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-100">
            <IconCalendar className="h-7 w-7 text-brand-600" />
          </div>
          <p className="text-sm text-ink-500">
            Nenhum agendamento para o dia {formatarDataExibicao(data)}.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {grupos.map((grupo) => (
            <div key={grupo.profissional} className="card !p-0 overflow-hidden">
              <div className="border-b border-brand-100 bg-brand-50/60 px-5 py-3.5">
                <p className="font-semibold text-ink-900">
                  {grupo.profissional}
                </p>
                <p className="text-xs text-ink-500">
                  {grupo.itens.length}{" "}
                  {grupo.itens.length === 1 ? "atendimento" : "atendimentos"}
                </p>
              </div>
              <ul className="divide-y divide-brand-50">
                {grupo.itens.map((agendamento, index) => (
                  <li
                    key={agendamento.id ?? index}
                    className="flex items-center justify-between gap-3 px-5 py-3.5"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink-900">
                        {formatarHora(agendamento.hora || agendamento.data_hora)}
                      </p>
                      <p className="truncate text-sm text-ink-700">
                        {nomeDoPaciente(agendamento)}
                      </p>
                    </div>
                    <StatusBadge status={agendamento.status} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <NovoAgendamentoModal
        aberto={modalAberto}
        onFechar={() => setModalAberto(false)}
        onCriado={handleAgendamentoCriado}
        pacientes={pacientes}
        profissionais={profissionais}
      />
    </Layout>
  );
}
