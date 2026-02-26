import type { FormEvent } from 'react';
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { KeyRound, Loader2, User, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../api/users';
import logo from '../../assets/logo.png';
import './Header.css';

const Header = () => {
  const [menuAberto, setMenuAberto] = useState<string | null>(null);
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
    setMenuAberto((prev) => (prev === menu ? null : menu));
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

  const displayName = user?.nome || user?.username || '';

  return (
    <header className="header">
      <div className="header__inner">
        <div className="header__branding">
          <img src={logo} alt="Painel Fiscal" className="branding__logo" />
          <div className="branding__text">
            <span className="branding__main">PLANNUS</span>
            <span className="branding__sub">FISCAL</span>
          </div>
        </div>

        <nav className="header__nav">
          <ul className="menu__top">
            <li onMouseEnter={() => toggleMenu('ferramentas')} onMouseLeave={() => toggleMenu(null)}>
              <span className="menu__title">Ferramentas</span>
              {menuAberto === 'ferramentas' && (
                <ul className="submenu">
                  <li>
                    <NavLink to="/ferramentas/importacao-nfs">Importação de NFs</NavLink>
                  </li>
                </ul>
              )}
            </li>
            <li onMouseEnter={() => toggleMenu('auditores')} onMouseLeave={() => toggleMenu(null)}>
              <span className="menu__title">Auditores</span>
              {menuAberto === 'auditores' && (
                <ul className="submenu">
                  <li>
                    <NavLink to="/auditores/entrega-2099-4099">Entrega 2099 e 4099</NavLink>
                  </li>
                  <li>
                    <NavLink to="/auditores/diferencas-2099-4099">Diferenças 2099 e 4099</NavLink>
                  </li>
                </ul>
              )}
            </li>
            <li onMouseEnter={() => toggleMenu('cadastros')} onMouseLeave={() => toggleMenu(null)}>
              <span className="menu__title">Cadastros</span>
              {menuAberto === 'cadastros' && (
                <ul className="submenu">
                  <li>
                    <NavLink to="/usuarios">Usuários</NavLink>
                  </li>
                  <li>
                    <NavLink to="/grupos">Grupos</NavLink>
                  </li>
                </ul>
              )}
            </li>
            <li onMouseEnter={() => toggleMenu('usuario')} onMouseLeave={() => toggleMenu(null)}>
              <span className="menu__title">
                <User size={20} />
              </span>
              {menuAberto === 'usuario' && (
                <ul className="submenu usuario">
                  <li className="info">{displayName}</li>
                  <li
                    onClick={() => {
                      setPasswordError('');
                      setPasswordMessage('');
                      setShowPasswordModal(true);
                    }}
                  >
                    Alterar Senha
                  </li>
                  <li onClick={logout}>Sair</li>
                </ul>
              )}
            </li>
          </ul>
        </nav>
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
                  Informe a senha atual e escolha uma nova.
                </p>
              </div>
              <button
                type="button"
                className="icon-button"
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
