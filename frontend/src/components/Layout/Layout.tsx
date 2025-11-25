import { Outlet } from 'react-router-dom';
import Header from '../Header/Header';
import './Layout.css';

const Layout = () => (
  <div className="app-shell">
    <Header />
    <main className="app-shell__main">
      <div className="app-shell__container">
        <Outlet />
      </div>
    </main>
  </div>
);

export default Layout;
