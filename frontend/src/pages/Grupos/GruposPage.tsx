import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Check, Edit2, PlusCircle, RefreshCcw, Trash } from 'lucide-react';
import './GruposPage.css';
import { groupsApi, type GroupPayload } from '../../api/groups';
import { usersApi } from '../../api/users';
import type { Group } from '../../types/group';
import type { UserAccount } from '../../types/user';

const emptyForm: GroupPayload = {
  nome: '',
  coordenador_id: null,
};

const GruposPage = () => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [form, setForm] = useState<GroupPayload>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const pageTitle = useMemo(
    () => (editingGroup ? 'Editar grupo' : 'Cadastrar novo grupo'),
    [editingGroup],
  );

  const loadGroups = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await groupsApi.list();
      setGroups(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível carregar os grupos.');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível carregar os usuários.');
    }
  };

  useEffect(() => {
    loadGroups();
    loadUsers();
  }, []);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingGroup(null);
  };

  const handleSubmit = async (evt: FormEvent) => {
    evt.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      if (editingGroup) {
        const updated = await groupsApi.update(editingGroup.id, form);
        setGroups((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
        setMessage('Grupo atualizado com sucesso.');
      } else {
        const created = await groupsApi.create(form);
        setGroups((prev) => [...prev, created]);
        setMessage('Grupo criado com sucesso.');
      }
      resetForm();
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.nome ||
        err?.message ||
        'Não foi possível salvar o grupo.';
      setError(Array.isArray(detail) ? detail.join(' ') : detail);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (group: Group) => {
    setEditingGroup(group);
    setForm({
      nome: group.nome,
      coordenador_id: group.coordenador?.id ?? null,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (group: Group) => {
    if (!window.confirm(`Remover o grupo ${group.nome}?`)) return;
    setError('');
    try {
      await groupsApi.delete(group.id);
      setGroups((prev) => prev.filter((g) => g.id !== group.id));
      setMessage('Grupo removido.');
      if (editingGroup?.id === group.id) {
        resetForm();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível remover o grupo.');
    }
  };

  return (
    <div className="grupos-page">
      <section className="page-hero users-hero">
        <div>
          <p className="page-hero__eyebrow">Cadastros</p>
          <h1>Grupos</h1>
        </div>
        <div className="page-hero__actions">
          <button type="button" className="btn btn--ghost" onClick={loadGroups} disabled={loading}>
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
              <p className="text-muted">Defina o nome do grupo e o coordenador responsável.</p>
            </div>
          </header>

          {message && <div className="alert alert--success">{message}</div>}
          {error && <div className="alert alert--error">{error}</div>}

          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Nome do grupo
              <input
                type="text"
                value={form.nome}
                required
                onChange={(e) => setForm((prev) => ({ ...prev, nome: e.target.value }))}
                placeholder="ex.: Fiscal SP"
              />
            </label>
            <label>
              Coordenador
              <select
                value={form.coordenador_id ? String(form.coordenador_id) : ''}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    coordenador_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">Sem coordenador</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.username}
                  </option>
                ))}
              </select>
            </label>

            <div className="form-actions">
              {editingGroup && (
                <button type="button" className="btn btn--ghost" onClick={resetForm} disabled={saving}>
                  Cancelar edição
                </button>
              )}
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? (
                  <>
                    <RefreshCcw className="spin" size={16} /> Salvando...
                  </>
                ) : editingGroup ? (
                  <>
                    <Check size={16} /> Atualizar grupo
                  </>
                ) : (
                  <>
                    <PlusCircle size={16} /> Criar grupo
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        <section className="card">
          <header className="card__header">
            <div>
              <h3>Grupos cadastrados</h3>
              <p className="text-muted">Atualize responsáveis e organize a equipe.</p>
            </div>
          </header>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Grupo</th>
                  <th>Coordenador</th>
                  <th align="right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <tr key={group.id}>
                    <td>
                      <strong>{group.nome}</strong>
                    </td>
                    <td>{group.coordenador?.username || '—'}</td>
                    <td align="right">
                      <div className="actions">
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => handleEdit(group)}
                          title="Editar"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-button text-button--danger"
                          onClick={() => handleDelete(group)}
                          title="Excluir"
                        >
                          <Trash size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!groups.length && (
                  <tr>
                    <td colSpan={3}>
                      <div className="empty-state">
                        {loading ? 'Carregando grupos...' : 'Nenhum grupo cadastrado ainda.'}
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

export default GruposPage;
