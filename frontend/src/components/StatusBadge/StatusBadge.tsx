import './StatusBadge.css';

interface Props {
  status: string;
}

const labels: Record<string, string> = {
  pending: 'Pendente',
  uploading: 'Enviando',
  processing: 'Processando',
  completed_with_errors: 'Concluído com erros',
  completed: 'Concluído',
  failed: 'Falhou',
  error: 'Erro',
  skipped: 'Ignorado',
  ignored: 'Ignorado',
};

const StatusBadge = ({ status }: Props) => {
  const normalized = status.toLowerCase();
  const label = labels[normalized] || status;
  return <span className={`status-badge status-badge--${normalized}`}>{label}</span>;
};

export default StatusBadge;
