import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Edit2,
  KeyRound,
  PlusCircle,
  RefreshCcw,
  ShieldCheck,
  Trash,
} from 'lucide-react';
import './UsuariosPage.css';
import { usersApi, type UserPayload } from '../../api/users';
import type { UserAccount } from '../../types/user';

const emptyForm: UserPayload = {
  username: '',
  email: '',
  profile: 'analista',
};

const UsuariosPage = () => {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [form, setForm] = useState<UserPayload>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingUser, setEditingUser] = useState<UserAccount | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const pageTitle = useMemo(
    () => (editingUser ? 'Editar usuário' : 'Cadastrar novo usuário'),
    [editingUser],
  );

  const loadUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível carregar os usuários.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingUser(null);
  };

  const handleSubmit = async (evt: FormEvent) => {
    evt.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      if (editingUser) {
        const updated = await usersApi.update(editingUser.id, form);
        setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
        setMessage('Usuário atualizado com sucesso.');
      } else {
        const created = await usersApi.create(form);
        setUsers((prev) => [...prev, created]);
        setMessage('Usuário criado. Senha inicial: Mudar123');
      }
      resetForm();
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.username ||
        err?.message ||
        'Não foi possível salvar o usuário.';
      setError(Array.isArray(detail) ? detail.join(' ') : detail);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (user: UserAccount) => {
    setEditingUser(user);
    setForm({
      username: user.username,
      email: user.email || '',
      profile: user.profile,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (user: UserAccount) => {
    if (!window.confirm(`Remover o usuário ${user.username}?`)) return;
    setError('');
    try {
      await usersApi.delete(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
      setMessage('Usuário removido.');
      if (editingUser?.id === user.id) {
        resetForm();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível remover o usuário.');
    }
  };

  const handleResetPassword = async (user: UserAccount) => {
    if (!window.confirm(`Resetar a senha de ${user.username} para "Mudar123"?`)) return;
    setError('');
    try {
      await usersApi.resetPassword(user.id);
      setMessage(`Senha de ${user.username} redefinida para Mudar123.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível redefinir a senha.');
    }
  };

  return (
    <div className="users-page">
      <section className="page-hero users-hero">
        <div>
          <p className="page-hero__eyebrow">Equipe</p>
          <h1>Usuários e Perfis</h1>
        </div>
        <div className="page-hero__actions">
          <button type="button" className="btn btn--ghost" onClick={loadUsers} disabled={loading}>
            <RefreshCcw size={16} />
            Atualizar lista
          </button>
        </div>
      </section>

      <div className="grid-two-columns">
        <section className="card">
          <header className="card__header">
            <div>
              <h3>{pageTitle}</h3>
              <p className="text-muted">
                Informe username, e-mail e escolha o perfil. A senha padrão é definida
                automaticamente.
              </p>
            </div>
          </header>

          {message && <div className="alert alert--success">{message}</div>}
          {error && <div className="alert alert--error">{error}</div>}

          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Username
              <input
                type="text"
                value={form.username}
                required
                onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
                placeholder="ex.: joao.silva"
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder="ex.: joao@empresa.com"
              />
            </label>
            <label>
              Perfil
              <select
                value={form.profile}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    profile: e.target.value as UserPayload['profile'],
                  }))
                }
              >
                <option value="administrador">Administrador</option>
                <option value="analista">Analista</option>
              </select>
            </label>

            <div className="form-actions">
              {editingUser && (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={resetForm}
                  disabled={saving}
                >
                  Cancelar edição
                </button>
              )}
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? (
                  <>
                    <RefreshCcw className="spin" size={16} /> Salvando...
                  </>
                ) : editingUser ? (
                  <>
                    <Check size={16} /> Atualizar usuário
                  </>
                ) : (
                  <>
                    <PlusCircle size={16} /> Criar usuário
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        <section className="card">
          <header className="card__header">
            <div>
              <h3>Usuários cadastrados</h3>
              <p className="text-muted">Gerencie perfis, redefina senhas e remova acessos.</p>
            </div>
          </header>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Email</th>
                  <th>Perfil</th>
                  <th align="right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="user-cell">
                        <ShieldCheck size={16} />
                        <div>
                          <strong>{user.username}</strong>
                          <small>ID {user.id}</small>
                        </div>
                      </div>
                    </td>
                    <td>{user.email || '—'}</td>
                    <td className="user-profile">
                      {user.profile === 'administrador' ? 'Administrador' : 'Analista'}
                    </td>
                    <td align="right">
                      <div className="actions">
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => handleEdit(user)}
                          title="Editar"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => handleResetPassword(user)}
                          title="Resetar senha"
                        >
                          <KeyRound size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-button text-button--danger"
                          onClick={() => handleDelete(user)}
                          title="Excluir"
                        >
                          <Trash size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!users.length && (
                  <tr>
                    <td colSpan={4}>
                      <div className="empty-state">
                        {loading ? 'Carregando usuários...' : 'Nenhum usuário cadastrado ainda.'}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

export default UsuariosPage;
