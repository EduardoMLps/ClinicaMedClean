/**
 * Prontuário / Odontograma.
 *
 * Fluxo da tela:
 *   1) Busca de paciente (nome ou CPF) -> GET /pacientes?busca=...
 *   2) Ao selecionar um paciente, carrega em paralelo:
 *      - a linha do tempo de evoluções clínicas -> GET /pacientes/:id/evolucoes
 *      - o odontograma -> GET /pacientes/:id/odontograma
 *   3) Formulário para registrar nova evolução -> POST /pacientes/:id/evolucoes
 *   4) Odontograma visual (32 dentes, notação FDI, 4 quadrantes). Clicar num
 *      dente abre um seletor de situação por face (vestibular, mesial,
 *      oclusal/incisal, distal, lingual/palatina). Alterações são otimistas
 *      e persistidas em PUT /pacientes/:id/odontograma/:dente.
 *
 * Nenhuma chamada à API deve derrubar a tela: todo erro vira uma mensagem
 * discreta, nunca uma tela quebrada.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import {
  IconSearch,
  IconUsers,
  IconStethoscope,
  IconClipboard,
  IconPlus,
  IconSmile,
  IconTooth,
} from "../assets/icons";

/* ------------------------------------------------------------------ */
/* Constantes do odontograma                                          */
/* ------------------------------------------------------------------ */

// Notação FDI, organizada como um dentista vê o paciente à sua frente.
const QUADRANTE_SUP_DIREITO = [18, 17, 16, 15, 14, 13, 12, 11];
const QUADRANTE_SUP_ESQUERDO = [21, 22, 23, 24, 25, 26, 27, 28];
const QUADRANTE_INF_DIREITO = [48, 47, 46, 45, 44, 43, 42, 41];
const QUADRANTE_INF_ESQUERDO = [31, 32, 33, 34, 35, 36, 37, 38];

const TODOS_OS_DENTES = [
  ...QUADRANTE_SUP_DIREITO,
  ...QUADRANTE_SUP_ESQUERDO,
  ...QUADRANTE_INF_DIREITO,
  ...QUADRANTE_INF_ESQUERDO,
];

const FACES = [
  { chave: "vestibular", label: "Vestibular", area: "col-start-2 row-start-1" },
  { chave: "mesial", label: "Mesial", area: "col-start-1 row-start-2" },
  { chave: "oclusal", label: "Oclusal / Incisal", area: "col-start-2 row-start-2" },
  { chave: "distal", label: "Distal", area: "col-start-3 row-start-2" },
  { chave: "lingual", label: "Lingual / Palatina", area: "col-start-2 row-start-3" },
];

const SITUACOES = {
  saudavel: {
    label: "Saudável",
    swatch: "bg-brand-500",
    swatchSuave: "bg-brand-100 text-brand-800",
    anel: "ring-brand-500",
  },
  a_tratar: {
    label: "A tratar",
    swatch: "bg-amber-500",
    swatchSuave: "bg-amber-100 text-amber-800",
    anel: "ring-amber-500",
  },
  tratado: {
    label: "Tratado",
    swatch: "bg-ink-700",
    swatchSuave: "bg-ink-100 text-ink-700",
    anel: "ring-ink-700",
  },
};

// Prioridade visual quando as faces de um dente estão em situações diferentes:
// um alerta pendente sempre "vence" no resumo do dente.
const PRIORIDADE_SITUACAO = ["a_tratar", "tratado", "saudavel"];

function facesIniciais() {
  return FACES.reduce((acc, face) => {
    acc[face.chave] = "saudavel";
    return acc;
  }, {});
}

function odontogramaInicial() {
  return TODOS_OS_DENTES.reduce((acc, dente) => {
    acc[dente] = { situacao: "saudavel", faces: facesIniciais() };
    return acc;
  }, {});
}

function calcularSituacaoGeral(faces) {
  if (!faces) return "saudavel";
  const valores = Object.values(faces);
  for (const situacao of PRIORIDADE_SITUACAO) {
    if (valores.includes(situacao)) return situacao;
  }
  return "saudavel";
}

// Normaliza a resposta real da API: GET /odontograma/:paciente_id devolve
// { paciente_id, dentes: [{ dente_fdi, faces: { distal: {situacao,...}, ... } }] }
// — cada face vem como objeto (com situacao/profissional_id/registrado_em),
// não como string solta.
function normalizarOdontograma(data) {
  const base = odontogramaInicial();
  const registros = Array.isArray(data?.dentes) ? data.dentes : [];

  registros.forEach((registro) => {
    const numero = Number(registro?.dente_fdi);
    if (!numero || !base[numero]) return;
    const facesBrutas = registro.faces || {};
    const faces = FACES.reduce((acc, face) => {
      acc[face.chave] = facesBrutas[face.chave]?.situacao || "saudavel";
      return acc;
    }, {});
    base[numero] = {
      situacao: calcularSituacaoGeral(faces),
      faces,
    };
  });

  return base;
}

function formatarData(valor) {
  if (!valor) return "Data não informada";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return String(valor);
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function calcularIdade(dataNascimento) {
  if (!dataNascimento) return null;
  const nascimento = new Date(dataNascimento);
  if (Number.isNaN(nascimento.getTime())) return null;
  const hoje = new Date();
  let idade = hoje.getFullYear() - nascimento.getFullYear();
  const aindaNaoFezAniversario =
    hoje.getMonth() < nascimento.getMonth() ||
    (hoje.getMonth() === nascimento.getMonth() && hoje.getDate() < nascimento.getDate());
  if (aindaNaoFezAniversario) idade -= 1;
  return idade;
}

/* ------------------------------------------------------------------ */
/* Subcomponentes                                                      */
/* ------------------------------------------------------------------ */

function Dente({ numero, situacao, selecionado, onClick }) {
  const meta = SITUACOES[situacao] || SITUACOES.saudavel;
  return (
    <button
      type="button"
      onClick={() => onClick(numero)}
      title={`Dente ${numero} · ${meta.label}`}
      className={`group relative grid h-10 w-10 shrink-0 place-items-center rounded-xl text-xs font-semibold
        text-white shadow-sm transition sm:h-11 sm:w-11
        ${meta.swatch}
        ${selecionado ? `ring-4 ring-offset-2 ring-offset-brand-50 ${meta.anel} scale-105` : "hover:scale-105 hover:shadow-card"}`}
    >
      {numero}
    </button>
  );
}

function FaceBotao({ face, situacao, ativa, onSelecionar }) {
  const meta = SITUACOES[situacao] || SITUACOES.saudavel;
  return (
    <button
      type="button"
      onClick={() => onSelecionar(face.chave)}
      title={face.label}
      className={`${face.area} grid place-items-center rounded-lg text-[10px] font-medium text-white transition
        ${meta.swatch}
        ${ativa ? "ring-2 ring-ink-900 ring-offset-1" : "opacity-80 hover:opacity-100"}
        ${face.chave === "oclusal" ? "h-10 w-10" : "h-8 w-8"}`}
    >
      {face.chave === "oclusal" ? "◎" : ""}
    </button>
  );
}

function Quadrante({ dentes, situacaoPorDente, denteSelecionado, onClickDente, inverter }) {
  const lista = inverter ? [...dentes] : dentes;
  return (
    <div className="flex gap-1.5">
      {lista.map((numero) => (
        <Dente
          key={numero}
          numero={numero}
          situacao={situacaoPorDente[numero]?.situacao || "saudavel"}
          selecionado={denteSelecionado === numero}
          onClick={onClickDente}
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Página                                                              */
/* ------------------------------------------------------------------ */

export default function Prontuario() {
  // Busca de pacientes
  const [termoBusca, setTermoBusca] = useState("");
  const [resultadosBusca, setResultadosBusca] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [erroBusca, setErroBusca] = useState(false);
  const [jaBuscou, setJaBuscou] = useState(false);

  // Profissional responsável pelo registro. Desde a versão 4.0.1 (B9), o
  // usuário vinculado a um profissional registra sempre em seu próprio nome
  // (o backend recusa outro). Só o administrador sem vínculo escolhe aqui.
  const { user } = useAuth();
  const profissionalVinculado = user?.profissional_id ?? null;
  const [profissionais, setProfissionais] = useState([]);
  const [profissionalId, setProfissionalId] = useState(
    profissionalVinculado ? String(profissionalVinculado) : ""
  );

  // Prontuário do paciente ativo (criado sob demanda, se ainda não existir).
  const [prontuarioAtualId, setProntuarioAtualId] = useState(null);

  useEffect(() => {
    let ativo = true;
    api
      .get("/profissionais")
      .then(({ data }) => {
        if (!ativo) return;
        const lista = Array.isArray(data) ? data : [];
        setProfissionais(lista);
        if (profissionalVinculado) setProfissionalId(String(profissionalVinculado));
        else if (lista.length > 0) setProfissionalId(String(lista[0].id));
      })
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, [profissionalVinculado]);

  // Paciente ativo
  const [paciente, setPaciente] = useState(null);

  // Linha do tempo de evoluções
  const [evolucoes, setEvolucoes] = useState([]);
  const [carregandoEvolucoes, setCarregandoEvolucoes] = useState(false);
  const [erroEvolucoes, setErroEvolucoes] = useState(false);

  // Formulário de nova evolução
  const [formEvolucao, setFormEvolucao] = useState({ descricao: "", procedimento: "", dente: "" });
  const [salvandoEvolucao, setSalvandoEvolucao] = useState(false);
  const [erroSalvarEvolucao, setErroSalvarEvolucao] = useState(false);

  // Odontograma
  const [odontograma, setOdontograma] = useState(odontogramaInicial);
  const [carregandoOdontograma, setCarregandoOdontograma] = useState(false);
  const [erroOdontograma, setErroOdontograma] = useState(false);
  const [erroSalvarDente, setErroSalvarDente] = useState(false);
  const [denteSelecionado, setDenteSelecionado] = useState(null);
  const [faceSelecionada, setFaceSelecionada] = useState("oclusal");

  const buscarPacientes = useCallback(async (evento) => {
    evento?.preventDefault?.();
    if (!termoBusca.trim()) return;

    setBuscando(true);
    setErroBusca(false);
    setJaBuscou(true);
    try {
      const { data } = await api.get("/pacientes", { params: { q: termoBusca.trim() } });
      const lista = Array.isArray(data) ? data : data?.dados || [];
      setResultadosBusca(lista);
    } catch (err) {
      setErroBusca(true);
      setResultadosBusca([]);
    } finally {
      setBuscando(false);
    }
  }, [termoBusca]);

  const carregarEvolucoes = useCallback(async (pacienteId) => {
    setCarregandoEvolucoes(true);
    setErroEvolucoes(false);
    try {
      // GET /prontuarios/:paciente_id devolve todos os prontuários do
      // paciente (normalmente um só), cada um já com suas evoluções
      // aninhadas (incluir_evolucoes=True no backend).
      const { data } = await api.get(`/prontuarios/${pacienteId}`);
      const prontuarios = Array.isArray(data?.prontuarios) ? data.prontuarios : [];
      setProntuarioAtualId(prontuarios[0]?.id ?? null);
      const todasEvolucoes = prontuarios
        .flatMap((p) => (Array.isArray(p.evolucoes) ? p.evolucoes : []))
        .sort((a, b) => new Date(b.criado_em || 0) - new Date(a.criado_em || 0));
      setEvolucoes(todasEvolucoes);
    } catch (err) {
      setErroEvolucoes(true);
      setEvolucoes([]);
      setProntuarioAtualId(null);
    } finally {
      setCarregandoEvolucoes(false);
    }
  }, []);

  const carregarOdontograma = useCallback(async (pacienteId) => {
    setCarregandoOdontograma(true);
    setErroOdontograma(false);
    try {
      const { data } = await api.get(`/odontograma/${pacienteId}`);
      setOdontograma(normalizarOdontograma(data));
    } catch (err) {
      setErroOdontograma(true);
      setOdontograma(odontogramaInicial());
    } finally {
      setCarregandoOdontograma(false);
    }
  }, []);

  const selecionarPaciente = useCallback(
    (pacienteEscolhido) => {
      setPaciente(pacienteEscolhido);
      setDenteSelecionado(null);
      setFormEvolucao({ descricao: "", procedimento: "", dente: "" });
      setErroSalvarEvolucao(false);
      setErroSalvarDente(false);
      carregarEvolucoes(pacienteEscolhido.id);
      carregarOdontograma(pacienteEscolhido.id);
    },
    [carregarEvolucoes, carregarOdontograma]
  );

  const trocarPaciente = useCallback(() => {
    setPaciente(null);
    setEvolucoes([]);
    setOdontograma(odontogramaInicial());
    setDenteSelecionado(null);
  }, []);

  const handleSubmitEvolucao = useCallback(
    async (evento) => {
      evento.preventDefault();
      if (!paciente || !formEvolucao.descricao.trim() || !profissionalId) return;

      setSalvandoEvolucao(true);
      setErroSalvarEvolucao(false);
      try {
        // O backend guarda a evolução como texto único (não há colunas
        // separadas para procedimento/dente) — juntamos aqui para manter
        // o registro legível, sem perder o que foi digitado em cada campo.
        const partes = [formEvolucao.descricao.trim()];
        if (formEvolucao.procedimento.trim()) partes.push(`Procedimento: ${formEvolucao.procedimento.trim()}`);
        if (formEvolucao.dente) partes.push(`Dente: ${formEvolucao.dente}`);
        const texto = partes.join(" — ");

        let prontuarioId = prontuarioAtualId;
        if (!prontuarioId) {
          const { data: novoProntuario } = await api.post(`/prontuarios/${paciente.id}`, {
            profissional_id: Number(profissionalId),
          });
          prontuarioId = novoProntuario.id;
          setProntuarioAtualId(prontuarioId);
        }

        const { data } = await api.post(`/prontuarios/${prontuarioId}/evolucoes`, {
          texto,
          profissional_id: Number(profissionalId),
        });
        setEvolucoes((atual) => [data, ...atual]);
        setFormEvolucao({ descricao: "", procedimento: "", dente: "" });
      } catch (err) {
        setErroSalvarEvolucao(true);
      } finally {
        setSalvandoEvolucao(false);
      }
    },
    [paciente, formEvolucao, profissionalId, prontuarioAtualId]
  );

  const handleClickDente = useCallback((numero) => {
    setErroSalvarDente(false);
    setFaceSelecionada("oclusal");
    setDenteSelecionado((atual) => (atual === numero ? null : numero));
  }, []);

  const persistirDente = useCallback(
    async (numero, proximoRegistro, registroAnterior) => {
      setOdontograma((atual) => ({ ...atual, [numero]: proximoRegistro }));
      if (!paciente || !profissionalId) return;
      setErroSalvarDente(false);
      try {
        // O backend recebe uma lista de alterações por face (não um
        // "registro" completo do dente), cada uma com o profissional
        // responsável.
        const alteracoes = Object.entries(proximoRegistro.faces || {}).map(([face, situacao]) => ({
          dente_fdi: numero,
          face,
          situacao,
          profissional_id: Number(profissionalId),
        }));
        await api.put(`/odontograma/${paciente.id}`, { alteracoes });
      } catch (err) {
        // Reverte a alteração otimista e avisa discretamente.
        setOdontograma((atual) => ({ ...atual, [numero]: registroAnterior }));
        setErroSalvarDente(true);
      }
    },
    [paciente, profissionalId]
  );

  const definirSituacaoDaFace = useCallback(
    (situacao) => {
      if (!denteSelecionado) return;
      const registroAnterior = odontograma[denteSelecionado];
      const novasFaces = { ...registroAnterior.faces, [faceSelecionada]: situacao };
      const proximoRegistro = { situacao: calcularSituacaoGeral(novasFaces), faces: novasFaces };
      persistirDente(denteSelecionado, proximoRegistro, registroAnterior);
    },
    [denteSelecionado, faceSelecionada, odontograma, persistirDente]
  );

  const definirSituacaoGeralDoDente = useCallback(
    (situacao) => {
      if (!denteSelecionado) return;
      const registroAnterior = odontograma[denteSelecionado];
      const novasFaces = FACES.reduce((acc, face) => {
        acc[face.chave] = situacao;
        return acc;
      }, {});
      const proximoRegistro = { situacao, faces: novasFaces };
      persistirDente(denteSelecionado, proximoRegistro, registroAnterior);
    },
    [denteSelecionado, odontograma, persistirDente]
  );

  const registroDenteSelecionado = denteSelecionado ? odontograma[denteSelecionado] : null;

  const resumoOdontograma = useMemo(() => {
    const contagem = { saudavel: 0, a_tratar: 0, tratado: 0 };
    TODOS_OS_DENTES.forEach((numero) => {
      const situacao = odontograma[numero]?.situacao || "saudavel";
      contagem[situacao] = (contagem[situacao] || 0) + 1;
    });
    return contagem;
  }, [odontograma]);

  const idadePaciente = paciente ? calcularIdade(paciente.data_nascimento || paciente.dataNascimento) : null;

  /* ------------------------------ Render ------------------------------ */

  if (!paciente) {
    return (
      <Layout title="Prontuário">
        <div className="mx-auto max-w-2xl">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand-100">
                <IconUsers className="h-6 w-6 text-brand-600" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-ink-900">Buscar paciente</h2>
                <p className="text-sm text-ink-500">
                  Encontre o paciente pelo nome ou CPF para abrir o prontuário.
                </p>
              </div>
            </div>

            <form onSubmit={buscarPacientes} className="mt-5 flex gap-3">
              <input
                type="text"
                className="input"
                placeholder="Nome ou CPF do paciente"
                value={termoBusca}
                onChange={(e) => setTermoBusca(e.target.value)}
              />
              <button type="submit" className="btn-primary shrink-0" disabled={buscando}>
                <IconSearch className="h-4 w-4" />
                {buscando ? "Buscando..." : "Buscar"}
              </button>
            </form>

            {erroBusca && (
              <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                Não foi possível buscar pacientes agora. Tente novamente em instantes.
              </p>
            )}

            {!erroBusca && jaBuscou && !buscando && resultadosBusca.length === 0 && (
              <p className="mt-4 text-sm text-ink-300">Nenhum paciente encontrado para essa busca.</p>
            )}

            {resultadosBusca.length > 0 && (
              <ul className="mt-5 divide-y divide-brand-100 overflow-hidden rounded-xl border border-brand-100">
                {resultadosBusca.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => selecionarPaciente(item)}
                      className="flex w-full items-center justify-between gap-3 bg-white px-4 py-3.5 text-left transition hover:bg-brand-50"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink-900">{item.nome}</p>
                        <p className="text-xs text-ink-300">
                          {item.cpf || "CPF não informado"}
                          {item.telefone ? ` · ${item.telefone}` : ""}
                        </p>
                      </div>
                      <span className="badge shrink-0">Abrir prontuário</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Prontuário">
      {/* Cabeçalho do paciente */}
      <div className="card mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand-100">
            <IconSmile className="h-7 w-7 text-brand-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink-900">{paciente.nome}</h2>
            <p className="text-sm text-ink-500">
              {paciente.cpf || "CPF não informado"}
              {idadePaciente != null ? ` · ${idadePaciente} anos` : ""}
              {paciente.telefone ? ` · ${paciente.telefone}` : ""}
            </p>
          </div>
        </div>
        <button type="button" onClick={trocarPaciente} className="btn-secondary">
          <IconSearch className="h-4 w-4" />
          Trocar paciente
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        {/* ---------------------------- Odontograma --------------------------- */}
        <div className="xl:col-span-3">
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-100">
                  <IconTooth className="h-5 w-5 text-brand-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-ink-900">Odontograma</h2>
                  <p className="text-xs text-ink-300">Notação FDI · clique em um dente para editar</p>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs text-ink-500">
                {Object.entries(SITUACOES).map(([chave, meta]) => (
                  <span key={chave} className="flex items-center gap-1.5">
                    <span className={`h-2.5 w-2.5 rounded-full ${meta.swatch}`} />
                    {meta.label}
                  </span>
                ))}
              </div>
            </div>

            {erroOdontograma && (
              <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                Não foi possível sincronizar o odontograma agora. As alterações podem não ser salvas.
              </p>
            )}
            {erroSalvarDente && (
              <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                Não foi possível salvar a alteração deste dente. Tente novamente.
              </p>
            )}

            {carregandoOdontograma ? (
              <p className="mt-6 text-sm text-ink-300">Carregando odontograma...</p>
            ) : (
              <div className="mt-6 overflow-x-auto">
                <div className="mx-auto w-fit space-y-3 rounded-2xl bg-brand-50/60 p-5">
                  <p className="text-center text-[11px] font-medium uppercase tracking-wide text-ink-300">
                    Arco superior
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    <Quadrante
                      dentes={QUADRANTE_SUP_DIREITO}
                      situacaoPorDente={odontograma}
                      denteSelecionado={denteSelecionado}
                      onClickDente={handleClickDente}
                    />
                    <div className="h-9 w-px bg-ink-100 sm:h-10" />
                    <Quadrante
                      dentes={QUADRANTE_SUP_ESQUERDO}
                      situacaoPorDente={odontograma}
                      denteSelecionado={denteSelecionado}
                      onClickDente={handleClickDente}
                    />
                  </div>

                  <div className="h-px w-full bg-ink-100" />

                  <div className="flex items-center justify-center gap-3">
                    <Quadrante
                      dentes={QUADRANTE_INF_DIREITO}
                      situacaoPorDente={odontograma}
                      denteSelecionado={denteSelecionado}
                      onClickDente={handleClickDente}
                    />
                    <div className="h-9 w-px bg-ink-100 sm:h-10" />
                    <Quadrante
                      dentes={QUADRANTE_INF_ESQUERDO}
                      situacaoPorDente={odontograma}
                      denteSelecionado={denteSelecionado}
                      onClickDente={handleClickDente}
                    />
                  </div>
                  <p className="text-center text-[11px] font-medium uppercase tracking-wide text-ink-300">
                    Arco inferior
                  </p>
                </div>
              </div>
            )}

            {/* Resumo rápido */}
            <div className="mt-5 flex flex-wrap gap-2">
              <span className={`rounded-full px-3 py-1 text-xs font-medium ${SITUACOES.saudavel.swatchSuave}`}>
                {resumoOdontograma.saudavel} saudáveis
              </span>
              <span className={`rounded-full px-3 py-1 text-xs font-medium ${SITUACOES.a_tratar.swatchSuave}`}>
                {resumoOdontograma.a_tratar} a tratar
              </span>
              <span className={`rounded-full px-3 py-1 text-xs font-medium ${SITUACOES.tratado.swatchSuave}`}>
                {resumoOdontograma.tratado} tratados
              </span>
            </div>

            {/* Seletor de situação por face */}
            {denteSelecionado && registroDenteSelecionado && (
              <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-ink-900">
                    Dente {denteSelecionado}
                  </h3>
                  <button
                    type="button"
                    onClick={() => setDenteSelecionado(null)}
                    className="text-xs font-medium text-ink-300 hover:text-ink-700"
                  >
                    Fechar
                  </button>
                </div>

                <div className="mt-4 flex flex-col gap-6 sm:flex-row sm:items-center">
                  {/* Mapa das faces */}
                  <div className="grid w-fit grid-cols-3 grid-rows-3 gap-1.5">
                    {FACES.map((face) => (
                      <FaceBotao
                        key={face.chave}
                        face={face}
                        situacao={registroDenteSelecionado.faces[face.chave]}
                        ativa={faceSelecionada === face.chave}
                        onSelecionar={setFaceSelecionada}
                      />
                    ))}
                  </div>

                  {/* Controles */}
                  <div className="flex-1 space-y-4">
                    <div>
                      <p className="label mb-2">
                        Face selecionada: {FACES.find((f) => f.chave === faceSelecionada)?.label}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(SITUACOES).map(([chave, meta]) => (
                          <button
                            key={chave}
                            type="button"
                            onClick={() => definirSituacaoDaFace(chave)}
                            className={`rounded-lg px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 ${meta.swatch}`}
                          >
                            {meta.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="label mb-2">Aplicar a todas as faces do dente</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(SITUACOES).map(([chave, meta]) => (
                          <button
                            key={chave}
                            type="button"
                            onClick={() => definirSituacaoGeralDoDente(chave)}
                            className="btn-secondary !px-3 !py-1.5 text-xs"
                          >
                            <span className={`h-2 w-2 rounded-full ${meta.swatch}`} />
                            {meta.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ---------------------------- Evoluções ------------------------------ */}
        <div className="xl:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-100">
                <IconPlus className="h-5 w-5 text-brand-600" />
              </div>
              <h2 className="text-base font-semibold text-ink-900">Nova evolução clínica</h2>
            </div>

            <form onSubmit={handleSubmitEvolucao} className="mt-4 space-y-4">
              <div>
                <label className="label" htmlFor="descricao-evolucao">
                  Descrição
                </label>
                <textarea
                  id="descricao-evolucao"
                  className="input min-h-[90px] resize-none"
                  placeholder="Descreva o atendimento, achados clínicos e conduta..."
                  value={formEvolucao.descricao}
                  onChange={(e) => setFormEvolucao((f) => ({ ...f, descricao: e.target.value }))}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label" htmlFor="procedimento-evolucao">
                    Procedimento
                  </label>
                  <input
                    id="procedimento-evolucao"
                    type="text"
                    className="input"
                    placeholder="Ex: Restauração"
                    value={formEvolucao.procedimento}
                    onChange={(e) => setFormEvolucao((f) => ({ ...f, procedimento: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="dente-evolucao">
                    Dente (opcional)
                  </label>
                  <select
                    id="dente-evolucao"
                    className="input"
                    value={formEvolucao.dente}
                    onChange={(e) => setFormEvolucao((f) => ({ ...f, dente: e.target.value }))}
                  >
                    <option value="">—</option>
                    {TODOS_OS_DENTES.map((numero) => (
                      <option key={numero} value={numero}>
                        {numero}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="label" htmlFor="profissional-evolucao">
                  Profissional responsável
                </label>
                <select
                  id="profissional-evolucao"
                  className="input"
                  value={profissionalId}
                  onChange={(e) => setProfissionalId(e.target.value)}
                  disabled={Boolean(profissionalVinculado)}
                  title={profissionalVinculado ? "Registro feito em seu nome (usuário vinculado a este profissional)" : undefined}
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

              {erroSalvarEvolucao && (
                <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  Não foi possível salvar a evolução agora. Tente novamente.
                </p>
              )}

              <button
                type="submit"
                className="btn-primary w-full"
                disabled={salvandoEvolucao || !profissionalId}
              >
                <IconClipboard className="h-4 w-4" />
                {salvandoEvolucao ? "Salvando..." : "Registrar evolução"}
              </button>
            </form>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-100">
                <IconStethoscope className="h-5 w-5 text-brand-600" />
              </div>
              <h2 className="text-base font-semibold text-ink-900">Linha do tempo</h2>
            </div>

            <div className="mt-4 space-y-3">
              {carregandoEvolucoes ? (
                <p className="text-sm text-ink-300">Carregando evoluções...</p>
              ) : erroEvolucoes ? (
                <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  Não foi possível carregar as evoluções agora.
                </p>
              ) : evolucoes.length === 0 ? (
                <p className="text-sm text-ink-300">Nenhuma evolução registrada ainda.</p>
              ) : (
                evolucoes.map((item, index) => (
                  <div
                    key={item.id ?? index}
                    className="rounded-xl border border-brand-100 bg-brand-50/50 p-4"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-ink-300">
                        {formatarData(item.criado_em)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-ink-700">{item.texto}</p>
                    {(() => {
                      const prof = profissionais.find((p) => p.id === item.profissional_id);
                      return prof ? (
                        <p className="mt-1 text-xs text-ink-300">Por {prof.nome}</p>
                      ) : null;
                    })()}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
