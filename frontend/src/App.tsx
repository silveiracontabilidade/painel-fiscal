import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import RequireAuth from './components/RequireAuth/RequireAuth';
import ImportacaoNfsPage from './pages/ImportacaoNfs/ImportacaoNfsPage';
import UsuariosPage from './pages/Usuarios/UsuariosPage';
import GruposPage from './pages/Grupos/GruposPage';
import LoginPage from './pages/Login/LoginPage';
import WelcomePage from './pages/Welcome/WelcomePage';
import AuditoresPage from './pages/Auditores/AuditoresPage';
import Entrega2099Page from './pages/Auditores/Entrega2099Page';
import Diferencas2099Page from './pages/Auditores/Diferencas2099Page';

const App = () => (
  <Routes>
    <Route element={<RequireAuth />}>
      <Route path="/" element={<Layout />}>
        <Route index element={<WelcomePage />} />
          <Route path="ferramentas">
            <Route index element={<Navigate to="importacao-nfs" replace />} />
            <Route path="importacao-nfs" element={<ImportacaoNfsPage />} />
          </Route>
          <Route path="usuarios" element={<UsuariosPage />} />
          <Route path="grupos" element={<GruposPage />} />
          <Route path="auditores" element={<AuditoresPage />} />
          <Route path="auditores/entrega-2099-4099" element={<Entrega2099Page />} />
          <Route path="auditores/diferencas-2099-4099" element={<Diferencas2099Page />} />
        </Route>
      </Route>
    <Route path="/login" element={<LoginPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default App;
