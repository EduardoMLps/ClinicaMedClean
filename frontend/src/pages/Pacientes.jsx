/**
 * Tela de Pacientes.
 *
 * Lista os pacientes cadastrados em cards/tabela, permite buscar por nome e
 * cadastrar um novo paciente através de um formulário modal simples que
 * envia POST /pacientes. Segue o design system do projeto (brand/ink,
 * classes utilitárias .card/.btn-primary/.input/.label/.badge).
 */
import React, { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import { IconSearch, IconPlus, IconUsers } from "../assets/icons";

function calcularIdade(dataNascimento) {
  if (!dataNascimento) return null;
  const nascimento = new Date(dataNascimento);
  if (Number.isNaN(nascimento.getTime())) return null;

  const hoje = new Date();
  let idade = hoje.getFullYear() - nascimento.getFullYear();
  const aindaNaoFezAniversario =
    hoje.getMonth() < nascimento.getMonth() ||
    (hoje.getMonth() === nascimento.getMonth() &&
      hoje.getDate() < nascimento.getDate());
  if (aindaNaoFezAniversario) idade -= 1;
  return idade;
}

function ehMenorDeIdade(dataNascimento) {
  const idade = calcularIdade(dataNascimento);
  return idade !== null && idade < 18;
}

function formatarTelefone(telefone) {
  return telefone || "—";
}

function iniciaisDoNome(nome) {
  if (!nome) return "?";
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0]?.[0] || "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

const FORM_INICIAL = {
  nome: "",
  cpf: "",
  data_nascimento: "",
  telefone: "",
  email: "",
  responsavel_nome: "",
  responsavel_cpf: "",
  responsavel_telefone: "",
};

function NovoPacienteModal({ aberto, onFechar, onCriado }) {
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

  const menorDeIdade = ehMenorDeIdade(form.data_nascimento);

  function atualizarCampo(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }));
  }

  async function handleSubmit(evento) {
    evento.preventDefault();
    setErro("");

    if (!form.nome.trim()) {
      setErro("Informe o nome do paciente.");
      return;
    }
    if (!form.data_nascimento) {
      // A API exige data_nascimento (usada, entre outras coisas, para
      // detectar pacientes menores de idade e exigir dados do responsável).
      setErro("Informe a data de nascimento do paciente.");
      return;
    }
    if (menorDeIdade && !form.responsavel_nome.trim()) {
      setErro("Paciente menor de idade: informe o nome do responsável.");
      return;
    }

    const payload = {
      nome: form.nome.trim(),
      cpf: form.cpf.trim() || null,
      data_nascimento: form.data_nascimento || null,
      telefone: form.telefone.trim() || null,
      email: form.email.trim() || null,
    };

    if (menorDeIdade) {
      payload.responsavel = {
        nome: form.responsavel_nome.trim(),
        cpf: form.responsavel_cpf.trim() || null,
        telefone: form.responsavel_telefone.trim() || null,
      };
    }

    setSalvando(true);
    try {
      const { data } = await api.post("/pacientes", payload);
      onCriado(data);
      onFechar();
    } catch (err) {
      // O backend devolve erros como { erro: "..." }, não { mensagem: "..." }.
      setErro(
        err?.response?.data?.erro ||
          "Não foi possível salvar o paciente. Tente novamente."
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 px-4 py-8">
      <div className="max-h-full w-full max-w-lg overflow-y-auto rounded-xl2 bg-white p-6 shadow-card">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink-900">
            Novo paciente
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
            <label className="label" htmlFor="nome">
              Nome completo
            </label>
            <input
              id="nome"
              className="input"
              type="text"
              value={form.nome}
              onChange={(e) => atualizarCampo("nome", e.target.value)}
              placeholder="Ex: Maria da Silva"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="cpf">
                CPF
              </label>
              <input
                id="cpf"
                className="input"
                type="text"
                value={form.cpf}
                onChange={(e) => atualizarCampo("cpf", e.target.value)}
                placeholder="000.000.000-00"
              />
            </div>
            <div>
              <label className="label" htmlFor="data_nascimento">
                Data de nascimento *
              </label>
              <input
                id="data_nascimento"
                className="input"
                type="date"
                value={form.data_nascimento}
                onChange={(e) =>
                  atualizarCampo("data_nascimento", e.target.value)
                }
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="telefone">
                Telefone
              </label>
              <input
                id="telefone"
                className="input"
                type="text"
                value={form.telefone}
                onChange={(e) => atualizarCampo("telefone", e.target.value)}
                placeholder="(00) 00000-0000"
              />
            </div>
            <div>
              <label className="label" htmlFor="email">
                E-mail
              </label>
              <input
                id="email"
                className="input"
                type="email"
                value={form.email}
                onChange={(e) => atualizarCampo("email", e.target.value)}
                placeholder="paciente@email.com"
              />
            </div>
          </div>

          {menorDeIdade && (
            <div className="rounded-xl bg-brand-50 p-4">
              <p className="mb-3 text-sm font-medium text-ink-700">
                Paciente menor de idade — dados do responsável
              </p>
              <div className="space-y-3">
                <div>
                  <label className="label" htmlFor="responsavel_nome">
                    Nome do responsável
                  </label>
                  <input
                    id="responsavel_nome"
                    className="input"
                    type="text"
                    value={form.responsavel_nome}
                    onChange={(e) =>
                      atualizarCampo("responsavel_nome", e.target.value)
                    }
                    placeholder="Nome completo do responsável"
                    required={menorDeIdade}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label" htmlFor="responsavel_cpf">
                      CPF do responsável
                    </label>
                    <input
                      id="responsavel_cpf"
                      className="input"
                      type="text"
                      value={form.responsavel_cpf}
                      onChange={(e) =>
                        atualizarCampo("responsavel_cpf", e.target.value)
                      }
                      placeholder="000.000.000-00"
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="responsavel_telefone">
                      Telefone do responsável
                    </label>
                    <input
                      id="responsavel_telefone"
                      className="input"
                      type="text"
                      value={form.responsavel_telefone}
                      onChange={(e) =>
                        atualizarCampo("responsavel_telefone", e.target.value)
                      }
                      placeholder="(00) 00000-0000"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

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
              {salvando ? "Salvando..." : "Salvar paciente"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Pacientes() {
  const [pacientes, setPacientes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);
  const [busca, setBusca] = useState("");
  const [modalAberto, setModalAberto] = useState(false);

  useEffect(() => {
    let ativo = true;

    async function carregarPacientes() {
      setCarregando(true);
      setErro(false);
      try {
        const { data } = await api.get("/pacientes", { params: { por_pagina: 200 } });
        if (ativo) {
          setPacientes(Array.isArray(data) ? data : data?.dados || []);
        }
      } catch (err) {
        if (ativo) setErro(true);
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    carregarPacientes();
    return () => {
      ativo = false;
    };
  }, []);

  const pacientesFiltrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return pacientes;
    return pacientes.filter((paciente) =>
      (paciente.nome || "").toLowerCase().includes(termo)
    );
  }, [busca, pacientes]);

  function handlePacienteCriado(novoPaciente) {
    setPacientes((atual) => [novoPaciente, ...atual]);
  }

  return (
    <Layout title="Pacientes">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <IconSearch className="pointer-events-none absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-ink-300" />
          <input
            type="text"
            className="input pl-10"
            placeholder="Buscar paciente por nome..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="btn-primary shrink-0"
          onClick={() => setModalAberto(true)}
        >
          <IconPlus className="h-4.5 w-4.5" />
          Novo Paciente
        </button>
      </div>

      {erro && (
        <p className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Não foi possível carregar a lista de pacientes agora. Tente
          novamente em instantes.
        </p>
      )}

      {carregando ? (
        <div className="card text-sm text-ink-300">Carregando pacientes...</div>
      ) : pacientesFiltrados.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 py-12 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-100">
            <IconUsers className="h-7 w-7 text-brand-600" />
          </div>
          <p className="text-sm text-ink-500">
            {busca
              ? "Nenhum paciente encontrado para essa busca."
              : "Nenhum paciente cadastrado ainda."}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-brand-100 bg-brand-50/60 text-ink-500">
                <th className="px-5 py-3 font-medium">Paciente</th>
                <th className="px-5 py-3 font-medium">Telefone</th>
                <th className="px-5 py-3 font-medium">Idade</th>
                <th className="px-5 py-3 font-medium">Cadastro</th>
              </tr>
            </thead>
            <tbody>
              {pacientesFiltrados.map((paciente, index) => {
                const idade = calcularIdade(paciente.data_nascimento);
                return (
                  <tr
                    key={paciente.id ?? index}
                    className="border-b border-brand-50 last:border-0 hover:bg-brand-50/40"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                          {iniciaisDoNome(paciente.nome)}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-ink-900">
                            {paciente.nome || "Sem nome"}
                          </p>
                          {paciente.email && (
                            <p className="truncate text-xs text-ink-300">
                              {paciente.email}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-ink-700">
                      {formatarTelefone(paciente.telefone)}
                    </td>
                    <td className="px-5 py-3.5 text-ink-700">
                      {idade !== null ? `${idade} anos` : "—"}
                      {idade !== null && idade < 18 && (
                        <span className="badge ml-2">menor</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-ink-500">
                      {paciente.criado_em
                        ? new Date(paciente.criado_em).toLocaleDateString(
                            "pt-BR"
                          )
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <NovoPacienteModal
        aberto={modalAberto}
        onFechar={() => setModalAberto(false)}
        onCriado={handlePacienteCriado}
      />
    </Layout>
  );
}
