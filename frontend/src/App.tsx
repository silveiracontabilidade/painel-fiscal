import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import RequireAuth from './components/RequireAuth/RequireAuth';
import ImportacaoNfsPage from './pages/ImportacaoNfs/ImportacaoNfsPage';
import UsuariosPage from './pages/Usuarios/UsuariosPage';
import LoginPage from './pages/Login/LoginPage';

const App = () => (
  <Routes>
    <Route element={<RequireAuth />}>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/ferramentas/importacao-nfs" replace />} />
          <Route path="ferramentas">
            <Route index element={<Navigate to="importacao-nfs" replace />} />
            <Route path="importacao-nfs" element={<ImportacaoNfsPage />} />
          </Route>
          <Route path="usuarios" element={<UsuariosPage />} />
        </Route>
      </Route>
    <Route path="/login" element={<LoginPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default App;
