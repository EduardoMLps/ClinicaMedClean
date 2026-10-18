/**
 * Tela de Estoque.
 *
 * Lista os produtos cadastrados (GET /estoque, com busca opcional via ?q=),
 * destaca os que estão no ou abaixo da quantidade mínima (GET /estoque/alertas),
 * permite cadastrar novo produto (POST /estoque) e registrar entrada/saída
 * (POST /estoque/:id/movimentacao). Segue o mesmo design system das demais
 * telas (brand/ink, classes utilitárias .card/.btn-primary/.input/.badge).
 */
import React, { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/client";
import { IconBox, IconPlus, IconSearch, IconBell } from "../assets/icons";

function NovoProdutoModal({ aberto, onFechar, onCriado }) {
  const [form, setForm] = useState({ nome: "", unidade: "unidade", quantidade_minima: 5 });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  if (!aberto) return null;

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    if (!form.nome.trim()) {
      setErro("Informe o nome do produto.");
      return;
    }
    setSalvando(true);
    try {
      await api.post("/estoque", {
        nome: form.nome.trim(),
        unidade: form.unidade,
        quantidade_minima: Number(form.quantidade_minima) || 0,
      });
      setForm({ nome: "", unidade: "unidade", quantidade_minima: 5 });
      onCriado();
      onFechar();
    } catch (err) {
      setErro(err?.response?.data?.erro || "Não foi possível cadastrar o produto.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 grid place-items-center bg-ink-900/40 p-4">
      <div className="card w-full max-w-md">
        <h2 className="mb-4 text-lg font-semibold text-ink-900">Novo produto de estoque</h2>
        <form onSubmit={salvar} className="space-y-3">
          <div>
            <label className="label">Nome do produto</label>
            <input
              className="input"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Ex.: Luva de procedimento (caixa)"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Unidade</label>
              <input
                className="input"
                value={form.unidade}
                onChange={(e) => setForm({ ...form, unidade: e.target.value })}
                placeholder="unidade, caixa, ml..."
              />
            </div>
            <div>
              <label className="label">Quantidade mínima</label>
              <input
                type="number"
                min="0"
                className="input"
                value={form.quantidade_minima}
                onChange={(e) => setForm({ ...form, quantidade_minima: e.target.value })}
              />
            </div>
          </div>
          {erro && <p className="text-sm text-rose-600">{erro}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onFechar}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={salvando}>
              {salvando ? "Salvando..." : "Cadastrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MovimentacaoModal({ produto, onFechar, onRegistrada }) {
  const [tipo, setTipo] = useState("entrada");
  const [quantidade, setQuantidade] = useState(1);
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  if (!produto) return null;

  async function salvar(e) {
    e.preventDefault();
    setErro("");
    setSalvando(true);
    try {
      await api.post(`/estoque/${produto.id}/movimentacao`, {
        tipo,
        quantidade: Number(quantidade) || 0,
        motivo: motivo.trim() || undefined,
      });
      onRegistrada();
      onFechar();
    } catch (err) {
      setErro(err?.response?.data?.erro || "Não foi possível registrar a movimentação.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 grid place-items-center bg-ink-900/40 p-4">
      <div className="card w-full max-w-md">
        <h2 className="mb-1 text-lg font-semibold text-ink-900">Movimentar estoque</h2>
        <p className="mb-4 text-sm text-ink-300">{produto.nome}</p>
        <form onSubmit={salvar} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTipo("entrada")}
              className={`rounded-xl border px-3 py-2 text-sm font-medium ${
                tipo === "entrada"
                  ? "border-brand-500 bg-brand-50 text-brand-800"
                  : "border-ink-100 text-ink-500"
              }`}
            >
              Entrada
            </button>
            <button
              type="button"
              onClick={() => setTipo("saida")}
              className={`rounded-xl border px-3 py-2 text-sm font-medium ${
                tipo === "saida"
                  ? "border-brand-500 bg-brand-50 text-brand-800"
                  : "border-ink-100 text-ink-500"
              }`}
            >
              Saída
            </button>
          </div>
          <div>
            <label className="label">Quantidade</label>
            <input
              type="number"
              min="1"
              className="input"
              value={quantidade}
              onChange={(e) => setQuantidade(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Motivo (opcional)</label>
            <input
              className="input"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Ex.: uso em atendimento, compra, perda..."
            />
          </div>
          {erro && <p className="text-sm text-rose-600">{erro}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onFechar}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={salvando}>
              {salvando ? "Salvando..." : "Confirmar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Estoque() {
  const [produtos, setProdutos] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalNovo, setModalNovo] = useState(false);
  const [produtoMovimentando, setProdutoMovimentando] = useState(null);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [respProdutos, respAlertas] = await Promise.all([
        api.get("/estoque", { params: busca ? { q: busca } : {} }),
        api.get("/estoque/alertas"),
      ]);
      setProdutos(respProdutos.data?.dados || []);
      setAlertas(respAlertas.data?.dados || []);
    } catch (err) {
      setErro("Não foi possível carregar o estoque agora.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timeout = setTimeout(carregar, 300);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busca]);

  const idsEmAlerta = new Set(alertas.map((a) => a.id));

  return (
    <Layout title="Estoque">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-full bg-brand-100 text-brand-700">
            <IconBox className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-ink-900">Estoque de materiais</h1>
            <p className="text-sm text-ink-300">
              {alertas.length > 0
                ? `${alertas.length} produto(s) no ponto de reposição`
                : "Nenhum produto abaixo do mínimo"}
            </p>
          </div>
        </div>
        <button className="btn-primary" onClick={() => setModalNovo(true)}>
          <IconPlus className="h-4 w-4" /> Novo produto
        </button>
      </div>

      {alertas.length > 0 && (
        <div className="card mb-6 border-amber-200 bg-amber-50">
          <div className="mb-2 flex items-center gap-2 text-amber-800">
            <IconBell className="h-5 w-5" />
            <span className="font-medium">Reposição recomendada</span>
          </div>
          <ul className="space-y-1 text-sm text-amber-800">
            {alertas.map((a) => (
              <li key={a.id}>
                {a.nome} — restam {a.quantidade} {a.unidade} (mínimo: {a.quantidade_minima})
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-ink-100 bg-white px-3 py-2">
          <IconSearch className="h-4 w-4 text-ink-300" />
          <input
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink-300"
            placeholder="Buscar produto por nome..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>

        {erro && <p className="mb-3 text-sm text-rose-600">{erro}</p>}

        {carregando ? (
          <p className="py-8 text-center text-sm text-ink-300">Carregando estoque...</p>
        ) : produtos.length === 0 ? (
          <p className="py-8 text-center text-sm text-ink-300">Nenhum produto cadastrado ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-ink-300">
                  <th className="pb-2">Produto</th>
                  <th className="pb-2">Quantidade</th>
                  <th className="pb-2">Mínimo</th>
                  <th className="pb-2">Unidade</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody>
                {produtos.map((p) => (
                  <tr key={p.id} className="border-t border-brand-50">
                    <td className="py-3 font-medium text-ink-900">{p.nome}</td>
                    <td className="py-3">
                      <span
                        className={
                          idsEmAlerta.has(p.id)
                            ? "badge bg-amber-100 text-amber-800"
                            : "badge"
                        }
                      >
                        {p.quantidade}
                      </span>
                    </td>
                    <td className="py-3 text-ink-500">{p.quantidade_minima}</td>
                    <td className="py-3 text-ink-500">{p.unidade}</td>
                    <td className="py-3 text-right">
                      <button
                        className="btn-secondary py-1.5 text-xs"
                        onClick={() => setProdutoMovimentando(p)}
                      >
                        Movimentar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <NovoProdutoModal aberto={modalNovo} onFechar={() => setModalNovo(false)} onCriado={carregar} />
      <MovimentacaoModal
        produto={produtoMovimentando}
        onFechar={() => setProdutoMovimentando(null)}
        onRegistrada={carregar}
      />
    </Layout>
  );
}
