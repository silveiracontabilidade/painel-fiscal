import './WelcomePage.css';

const WelcomePage = () => (
  <div className="welcome-page">
    <section className="welcome-hero">
      <h1>Bem-vindo ao Painel Fiscal</h1>
      <p>Escolha uma ferramenta no menu para iniciar os trabalhos.</p>
    </section>

    <section className="welcome-card">
      <h2>Primeiros passos</h2>
      <ul>
        <li>Use o menu Ferramentas para importar NFSe.</li>
        <li>Em Cadastros, gerencie usuários e auditores.</li>
      </ul>
    </section>
  </div>
);

export default WelcomePage;
