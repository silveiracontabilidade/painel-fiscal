import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import './Entrega2099Page.css';
import { auditoresApi } from '../../api/auditores';
import type {
  DctfwebPosicaoGeralItem,
  DctfwebUltimaAtualizacao,
} from '../../types/auditores';

const formatDate = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('pt-BR');
};

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('pt-BR');
};

const normalizeText = (value?: string | null) => (value || '').toUpperCase();

const getStatus2099 = (origem?: string | null) => {
  return normalizeText(origem).includes('REINF CP') ? 'OK' : '-';
};

const getStatus4099 = (origem?: string | null) => {
  return normalizeText(origem).includes('REINF RET') ? 'OK' : '-';
};

type StatusFilter = 'all' | 'OK' | '-';

type DctfwebPosicaoGeralRow = DctfwebPosicaoGeralItem & {
  status2099: string;
  status4099: string;
  rowKey: string;
};

const matchesStatusFilter = (status: string, filter: StatusFilter) => {
  if (filter === 'all') return true;
  return status === filter;
};

const Entrega2099Page = () => {
  const [competencias, setCompetencias] = useState<string[]>([]);
  const [competencia, setCompetencia] = useState<string | null>(null);
  const [rows, setRows] = useState<DctfwebPosicaoGeralItem[]>([]);
  const [atualizacoes, setAtualizacoes] = useState<DctfwebUltimaAtualizacao[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [status2099Filter, setStatus2099Filter] = useState<StatusFilter>('all');
  const [status4099Filter, setStatus4099Filter] = useState<StatusFilter>('all');

  const selectedUpdate = useMemo(() => {
    if (!competencia) return null;
    return atualizacoes.find((item) => item.competencia === competencia) || null;
  }, [atualizacoes, competencia]);

  const rowsWithStatus = useMemo<DctfwebPosicaoGeralRow[]>(() => {
    return rows.map((row, index) => ({
      ...row,
      status2099: getStatus2099(row.origem),
      status4099: getStatus4099(row.origem),
      rowKey: `${row.cod_folha}-${row.cnpj_original}-${row.origem}-${index}`,
    }));
  }, [rows]);

  const filteredRows = useMemo(() => {
    return rowsWithStatus.filter((row) => {
      return (
        matchesStatusFilter(row.status2099, status2099Filter) &&
        matchesStatusFilter(row.status4099, status4099Filter)
      );
    });
  }, [rowsWithStatus, status2099Filter, status4099Filter]);

  const loadData = async (competenciaSelecionada?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await auditoresApi.getPosicaoGeral(competenciaSelecionada || undefined);
      setCompetencias(data.competencias || []);
      setCompetencia(data.competencia_selecionada);
      setAtualizacoes(data.ultimas_atualizacoes || []);
      setRows(data.results || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Não foi possível carregar o relatório.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCompetenciaChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    setCompetencia(value);
    loadData(value);
  };

  const handleExport = async (kind: 'csv' | 'excel') => {
    if (exporting) return;
    setExporting(true);
    try {
      const blob = await auditoresApi.exportPosicaoGeral(kind, competencia || undefined);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      const suffix = kind === 'csv' ? 'csv' : 'xlsx';
      const comp = (competencia || 'todas').replace('/', '-');
      link.href = url;
      link.download = `dctfweb_posicao_geral_${comp}.${suffix}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Falha ao exportar relatório.', err);
      setError('Não foi possível exportar o relatório.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="auditores-entrega">
      <section className="auditores-entrega__header">
        <div>
          <h1>Entrega 2099 e 4099</h1>
          <p>Posição geral das empresas com DCTFWeb pendente.</p>
        </div>
      </section>

      <section className="auditores-entrega__card">
        <header className="auditores-entrega__card-header">
          <div>
            <h2>Posição geral</h2>
            <p className="text-muted">Empresas com DCTFWeb pendente</p>
          </div>
          <div className="auditores-entrega__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => handleExport('csv')}
              disabled={exporting || loading}
            >
              Exportar CSV
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => handleExport('excel')}
              disabled={exporting || loading}
            >
              Exportar Excel
            </button>
          </div>
        </header>

        <div className="auditores-entrega__meta">
          <div className="ultima-atualizacao">
            <span className="ultima-atualizacao__titulo">Última atualização</span>
            <div className="ultima-atualizacao__lista">
              <span>{competencia || '—'}</span>
              <span>{formatDateTime(selectedUpdate?.ultima_atualizacao || null)}</span>
            </div>
          </div>

          <div className="auditores-entrega__filters">
            <div className="auditores-entrega__filter">
              <label htmlFor="competencia">Competência:</label>
              <select
                id="competencia"
                value={competencia || ''}
                onChange={handleCompetenciaChange}
                disabled={!competencias.length}
              >
                {!competencias.length && <option value="">Sem dados</option>}
                {competencias.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="auditores-entrega__filter">
              <label htmlFor="status2099">Status 2099:</label>
              <select
                id="status2099"
                value={status2099Filter}
                onChange={(event) => setStatus2099Filter(event.target.value as StatusFilter)}
              >
                <option value="all">Todos</option>
                <option value="OK">OK</option>
                <option value="-">-</option>
              </select>
            </div>

            <div className="auditores-entrega__filter">
              <label htmlFor="status4099">Status 4099:</label>
              <select
                id="status4099"
                value={status4099Filter}
                onChange={(event) => setStatus4099Filter(event.target.value as StatusFilter)}
              >
                <option value="all">Todos</option>
                <option value="OK">OK</option>
                <option value="-">-</option>
              </select>
            </div>
          </div>
        </div>

        <div className="auditores-entrega__table">
          <table>
            <thead>
              <tr>
                <th>Folha</th>
                <th>Razão Social</th>
                <th className="col-cnpj">CNPJ</th>
                <th>Início</th>
                <th>Término</th>
                <th>Sistema</th>
                <th>Status 2099</th>
                <th>Status 4099</th>
                <th>Tipo</th>
                <th>Situação</th>
                <th>Saldo a pagar</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={11}>
                    <div className="empty-state">Carregando...</div>
                  </td>
                </tr>
              )}
              {!loading && error && (
                <tr>
                  <td colSpan={11}>
                    <div className="empty-state">{error}</div>
                  </td>
                </tr>
              )}
              {!loading && !error && !filteredRows.length && (
                <tr>
                  <td colSpan={11}>
                    <div className="empty-state">
                      {rows.length
                        ? 'Sem dados para os filtros selecionados.'
                        : 'Sem dados para a competência selecionada.'}
                    </div>
                  </td>
                </tr>
              )}
              {!loading &&
                !error &&
                filteredRows.map((row) => (
                  <tr key={row.rowKey}>
                    <td>{row.cod_folha}</td>
                    <td>{row.razao_social}</td>
                    <td className="col-cnpj">{row.cnpj_original}</td>
                    <td>{formatDate(row.inicio_contrato)}</td>
                    <td>{formatDate(row.termino_contrato)}</td>
                    <td>{row.sistema}</td>
                    <td>{row.status2099}</td>
                    <td>{row.status4099}</td>
                    <td>{row.tipo}</td>
                    <td>{row.situacao}</td>
                    <td style={{ textAlign: 'right' }}>{row.saldo_pagar_formatado}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default Entrega2099Page;
