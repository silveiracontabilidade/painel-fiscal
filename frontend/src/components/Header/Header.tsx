import type { FormEvent } from 'react';
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  ChevronDown,
  FolderCog,
  KeyRound,
  Loader2,
  LogOut,
  User,
  X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../api/users';
import logo from '../../assets/logo.png';
import './Header.css';

const Header = () => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const { user, logout } = useAuth();

  const toggleMenu = (menu: string | null) => {
    setActiveMenu((prev) => (prev === menu ? null : menu));
  };

  const handlePasswordSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setChangingPassword(true);
    setPasswordError('');
    setPasswordMessage('');
    try {
      await usersApi.changeOwnPassword(passwordForm);
      setPasswordMessage('Senha atualizada com sucesso.');
      setPasswordForm({ currentPassword: '', newPassword: '' });
    } catch (err: any) {
      const detail = err?.response?.data;
      const message =
        detail?.currentPassword?.[0] ||
        detail?.newPassword?.[0] ||
        detail?.detail ||
        'Não foi possível atualizar a senha.';
      setPasswordError(message);
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="app-header__branding">
          <img src={logo} alt="Painel Fiscal" className="app-header__logo" />
          <div className="app-header__titles">
            <span className="app-header__title">Painel Fiscal</span>
            <span className="app-header__subtitle">Backoffice</span>
          </div>
        </div>

        <nav className="app-header__nav">
          <ul>
            <li
              onMouseEnter={() => toggleMenu('ferramentas')}
              onMouseLeave={() => toggleMenu(null)}
            >
              <button type="button" className="menu-trigger">
                <FolderCog size={16} />
                Ferramentas
                <ChevronDown size={14} />
              </button>
              {activeMenu === 'ferramentas' && (
                <div className="submenu">
                  <NavLink
                    to="/ferramentas/importacao-nfs"
                    className={({ isActive }) =>
                      `submenu__item${isActive ? ' submenu__item--active' : ''}`
                    }
                  >
                    Importação de NFs
                  </NavLink>
                </div>
              )}
            </li>
            <li>
              <NavLink
                to="/usuarios"
                className={({ isActive }) =>
                  `nav-link${isActive ? ' nav-link--active' : ''}`
                }
              >
                Usuários
              </NavLink>
            </li>
          </ul>
        </nav>

        <div className="app-header__user">
          <button
            type="button"
            className="app-header__user-info"
            onClick={() => {
              setPasswordError('');
              setPasswordMessage('');
              setShowPasswordModal(true);
            }}
          >
            <span>{user?.nome || user?.username}</span>
            <small>online</small>
          </button>
          <div className="app-header__user-avatar">
            <User size={16} />
          </div>
          <button
            className="app-header__icon-btn"
            type="button"
            aria-label="Sair"
            onClick={logout}
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
      {showPasswordModal && (
        <div className="header-modal">
          <div className="header-modal__backdrop" onClick={() => setShowPasswordModal(false)} />
          <div className="header-modal__content">
            <div className="header-modal__header">
              <div>
                <p className="header-modal__eyebrow">Segurança</p>
                <h3>Alterar senha</h3>
                <p className="header-modal__subtitle">
                  Informe a senha atual e escolha uma nova. Evite reutilizar Mudar123.
                </p>
              </div>
              <button
                type="button"
                className="app-header__icon-btn"
                onClick={() => setShowPasswordModal(false)}
                aria-label="Fechar"
              >
                <X size={16} />
              </button>
            </div>

            {passwordMessage && <div className="alert alert--success">{passwordMessage}</div>}
            {passwordError && <div className="alert alert--error">{passwordError}</div>}

            <form className="header-modal__form" onSubmit={handlePasswordSubmit}>
              <label>
                Senha atual
                <input
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(e) =>
                    setPasswordForm((prev) => ({ ...prev, currentPassword: e.target.value }))
                  }
                  required
                />
              </label>
              <label>
                Nova senha
                <input
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(e) =>
                    setPasswordForm((prev) => ({ ...prev, newPassword: e.target.value }))
                  }
                  required
                />
              </label>
              <div className="header-modal__actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={changingPassword}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn--primary" disabled={changingPassword}>
                  {changingPassword ? (
                    <>
                      <Loader2 className="spin" size={16} /> Salvando...
                    </>
                  ) : (
                    <>
                      <KeyRound size={16} /> Atualizar senha
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
