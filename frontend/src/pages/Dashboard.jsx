import React, { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import {
  IconCalendar,
  IconWallet,
  IconUsers,
  IconBox,
} from "../assets/icons";

function formatarMoeda(valor) {
  if (typeof valor !== "number") return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function KpiCard({ icon: Icon, label, value, hint, loading, erro }) {
  return (
    <div className="card flex items-start gap-4">
      <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand-100">
        <Icon className="h-6 w-6 text-brand-600" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink-500">{label}</p>
        {loading ? (
          <p className="mt-1 text-sm text-ink-300">Carregando...</p>
        ) : erro ? (
          <p className="mt-1 text-sm text-ink-300">Indisponível no momento</p>
        ) : (
          <p className="mt-1 text-2xl font-semibold text-ink-900">{value}</p>
        )}
        {!loading && !erro && hint && (
          <p className="mt-0.5 text-xs text-ink-300">{hint}</p>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [carregandoResumo, setCarregandoResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState(false);

  const [alertasEstoque, setAlertasEstoque] = useState(null);
  const [carregandoEstoque, setCarregandoEstoque] = useState(true);
  const [erroEstoque, setErroEstoque] = useState(false);

  const [totalPacientes, setTotalPacientes] = useState(null);
  const [totalConsultasHoje, setTotalConsultasHoje] = useState(null);
  const [carregandoContagens, setCarregandoContagens] = useState(true);
  const [erroContagens, setErroContagens] = useState(false);

  useEffect(() => {
    let ativo = true;

    async function carregarResumoFinanceiro() {
      setCarregandoResumo(true);
      setErroResumo(false);
      try {
        const { data } = await api.get("/financeiro/resumo");
        if (ativo) setResumoFinanceiro(data);
      } catch (err) {
        if (ativo) setErroResumo(true);
      } finally {
        if (ativo) setCarregandoResumo(false);
      }
    }

    async function carregarAlertasEstoque() {
      setCarregandoEstoque(true);
      setErroEstoque(false);
      try {
        const { data } = await api.get("/estoque/alertas");
        if (ativo) setAlertasEstoque(data);
      } catch (err) {
        if (ativo) setErroEstoque(true);
      } finally {
        if (ativo) setCarregandoEstoque(false);
      }
    }

    // Pacientes ativos e consultas de hoje não vêm do /financeiro/resumo
    // (que só cobre indicadores financeiros) — são obtidos direto dos
    // módulos de pacientes e agenda.
    async function carregarContagens() {
      setCarregandoContagens(true);
      setErroContagens(false);
      try {
        const hoje = new Date().toISOString().slice(0, 10);
        const [respPacientes, respAgenda] = await Promise.all([
          api.get("/pacientes", { params: { por_pagina: 1 } }),
          api.get("/agenda", { params: { data: hoje } }),
        ]);
        if (ativo) {
          setTotalPacientes(
            respPacientes.data?.total ??
              (Array.isArray(respPacientes.data) ? respPacientes.data.length : null)
          );
          setTotalConsultasHoje(
            Array.isArray(respAgenda.data) ? respAgenda.data.length : null
          );
        }
      } catch (err) {
        if (ativo) setErroContagens(true);
      } finally {
        if (ativo) setCarregandoContagens(false);
      }
    }

    carregarResumoFinanceiro();
    carregarAlertasEstoque();
    carregarContagens();

    return () => {
      ativo = false;
    };
  }, []);

  const consultasHoje = totalConsultasHoje;
  const faturamentoMes = resumoFinanceiro?.recebido_no_mes;
  const pacientesAtivos = totalPacientes;

  const totalAlertasEstoque = Array.isArray(alertasEstoque)
    ? alertasEstoque.length
    : alertasEstoque?.total ?? alertasEstoque?.quantidade;

  const listaAlertasEstoque = Array.isArray(alertasEstoque)
    ? alertasEstoque
    : alertasEstoque?.dados ?? [];

  const houveFalhaGeral = erroResumo && erroEstoque;

  return (
    <Layout title="Dashboard">
      {houveFalhaGeral && (
        <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Não foi possível carregar os indicadores agora. O sistema segue
          disponível — tente novamente em instantes.
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          icon={IconCalendar}
          label="Consultas hoje"
          value={consultasHoje ?? "0"}
          hint="Agendadas para o dia"
          loading={carregandoContagens}
          erro={erroContagens}
        />
        <KpiCard
          icon={IconWallet}
          label="Faturamento do mês"
          value={formatarMoeda(faturamentoMes)}
          hint="Recebido no mês"
          loading={carregandoResumo}
          erro={erroResumo}
        />
        <KpiCard
          icon={IconUsers}
          label="Pacientes ativos"
          value={pacientesAtivos ?? "0"}
          hint="Com cadastro ativo"
          loading={carregandoContagens}
          erro={erroContagens}
        />
        <KpiCard
          icon={IconBox}
          label="Alertas de estoque"
          value={totalAlertasEstoque ?? "0"}
          hint="Itens com estoque baixo"
          loading={carregandoEstoque}
          erro={erroEstoque}
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="card">
          <h2 className="text-base font-semibold text-ink-900">
            Resumo financeiro
          </h2>
          {carregandoResumo ? (
            <p className="mt-3 text-sm text-ink-300">Carregando dados...</p>
          ) : erroResumo ? (
            <p className="mt-3 text-sm text-ink-300">
              O resumo financeiro ainda não está disponível.
            </p>
          ) : (
            <p className="mt-3 text-sm text-ink-500">
              Faturamento do mês: {formatarMoeda(faturamentoMes)} · Pacientes
              ativos: {pacientesAtivos ?? "—"}
            </p>
          )}
        </div>

        <div className="card">
          <h2 className="text-base font-semibold text-ink-900">
            Alertas de estoque
          </h2>
          {carregandoEstoque ? (
            <p className="mt-3 text-sm text-ink-300">Carregando dados...</p>
          ) : erroEstoque ? (
            <p className="mt-3 text-sm text-ink-300">
              Os alertas de estoque ainda não estão disponíveis.
            </p>
          ) : listaAlertasEstoque.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {listaAlertasEstoque.slice(0, 5).map((item, index) => (
                <li
                  key={item.id ?? index}
                  className="flex items-center justify-between rounded-xl bg-brand-50 px-3.5 py-2.5 text-sm text-ink-700"
                >
                  <span>{item.nome || item.produto || "Item de estoque"}</span>
                  <span className="badge">
                    {item.quantidade ?? item.quantidade_atual ?? "baixo"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ink-500">
              Nenhum alerta de estoque no momento.
            </p>
          )}
        </div>
      </div>
    </Layout>
  );
}
