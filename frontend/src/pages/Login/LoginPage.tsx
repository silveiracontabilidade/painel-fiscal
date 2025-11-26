import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../../context/AuthContext';
import logo from '../../assets/logo.png';
import './LoginPage.css';

const LoginPage = () => {
  const { login } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(form.username, form.password);
    } catch (err) {
      console.error(err);
      setError('Credenciais inválidas ou servidor indisponível.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <header>
          <img src={logo} alt="Painel Fiscal" className="login-logo" />
          <h1>Painel Fiscal</h1>
          <p>Sem acesso ? Entre em contato com seu coordenador.</p>
        </header>
        <form onSubmit={handleSubmit}>
          <label htmlFor="username">
            Usuário
            <input
              id="username"
              type="text"
              value={form.username}
              onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
              placeholder="usuario@empresa.com"
              required
            />
          </label>
          <label htmlFor="password">
            Senha
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="••••••••"
              required
            />
          </label>
          {error && <p className="login-error">{error}</p>}
          {/* {location.state?.from && (
            // <p className="login-info">Faça login para continuar até {location.state.from.pathname}</p>
          )} */}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
