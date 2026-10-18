import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Logo } from "../assets/Logo";
import { HeroIllustration } from "../assets/HeroIllustration";
import { IconLock } from "../assets/icons";
import { useAuth } from "../context/AuthContext";
import { CLINICA } from "../config/clinica";
import ClinicFooter from "../components/ClinicFooter";
import WhatsAppButton from "../components/WhatsAppButton";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  const redirectTo = location.state?.from?.pathname || "/";

  async function handleSubmit(event) {
    event.preventDefault();
    setErro("");

    if (!email || !senha) {
      setErro("Preencha e-mail e senha para continuar.");
      return;
    }

    setLoading(true);
    try {
      await login(email, senha);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      // O backend devolve erros no formato { erro: "..." } (nunca "mensagem").
      // Exceção: respostas 429 do Flask-Limiter vêm como HTML puro (não JSON),
      // então tratamos esse status à parte com uma mensagem amigável.
      const status = err?.response?.status;
      const mensagem =
        status === 429
          ? "Muitas tentativas de login. Aguarde um minuto e tente novamente."
          : err?.response?.data?.erro ||
            (status === 401
              ? "E-mail ou senha incorretos."
              : "Não foi possível entrar. Tente novamente em instantes.");
      setErro(mensagem);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Coluna esquerda: formulário */}
      <div className="relative flex items-center justify-center bg-white px-6 py-12 sm:px-12">
        <div className="w-full max-w-sm">
          <div className="mb-10">
            <Logo size={44} />
          </div>

          <h2 className="text-2xl font-semibold text-ink-900">
            Bem-vindo de volta
          </h2>
          <p className="mt-1.5 text-sm text-ink-500">
            Entre com suas credenciais para acessar o sistema da clínica.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit} noValidate>
            <div>
              <label htmlFor="email" className="label">
                E-mail
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className="input"
                placeholder="voce@clinica.com.br"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="senha" className="label">
                Senha
              </label>
              <div className="relative">
                <IconLock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
                <input
                  id="senha"
                  type="password"
                  autoComplete="current-password"
                  className="input pl-10"
                  placeholder="••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {erro && (
              <p className="rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
                {erro}
              </p>
            )}

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          <p className="mt-8 text-center text-xs text-ink-300">
            {CLINICA.nomeCompleto}
          </p>
        </div>

        <div className="absolute inset-x-0 bottom-0">
          <ClinicFooter variant="light" />
        </div>
      </div>

      {/* Coluna direita: ilustração */}
      <div className="relative hidden items-center justify-center overflow-hidden bg-brand-50 lg:flex">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand-200/40 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-brand-300/30 blur-3xl" />

        <div className="relative z-10 flex flex-col items-center px-10 text-center">
          <HeroIllustration className="w-full max-w-md" />
          <h3 className="mt-6 text-2xl font-semibold text-ink-900">
            Cuidar de sorrisos começa por uma boa gestão
          </h3>
          <p className="mt-3 max-w-sm text-sm text-ink-500">
            Agenda, prontuários, financeiro e estoque da sua clínica em um só
            lugar, com a simplicidade que o seu dia a dia precisa.
          </p>
        </div>
      </div>

      <WhatsAppButton />
    </div>
  );
}
