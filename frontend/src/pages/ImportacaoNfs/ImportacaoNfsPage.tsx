import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { nanoid } from 'nanoid';
import {
  AlertTriangle,
  ChevronRight,
  CloudUpload,
  Download,
  FileText,
  Settings,
  Trash,
  Eye,
  Loader2,
  RefreshCcw,
  RotateCcw,
  UploadCloud,
} from 'lucide-react';
import StatusBadge from '../../components/StatusBadge/StatusBadge';
import { nfseApi } from '../../api/nfse';
import type { CompanyOption, ImportJobOptions } from '../../types/nfse';
import './ImportacaoNfsPage.css';

type QueueStatus = 'waiting' | 'uploading' | 'uploaded' | 'error';

interface QueuedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  status: QueueStatus;
  progress: number;
  error?: string;
}

const formatBytes = (size: number) => {
  if (!size) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.floor(Math.log(size) / Math.log(1024));
  return `${(size / 1024 ** index).toFixed(1)} ${units[index]}`;
};

const formatDateTime = (iso: string) => {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatCompetence = (value?: string) => {
  if (!value) return '—';
  if (value.length === 6) {
    return `${value.slice(0, 2)}/${value.slice(2)}`;
  }
  return value;
};

const TERMINAL_STATUSES = new Set(['error', 'skipped', 'ignored', 'completed']);

const ImportacaoNfsPage = () => {
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [options, setOptions] = useState<ImportJobOptions>({
    ocrLanguage: 'por',
    model: 'gpt-4o-mini',
    baseUrl: '',
    companyCode: '',
    competencePeriod: '',
  });
  const [companyQuery, setCompanyQuery] = useState('');
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([]);
  const [isSearchingCompany, setIsSearchingCompany] = useState(false);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [competenceTouched, setCompetenceTouched] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [totalUploadProgress, setTotalUploadProgress] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyFilterCompany, setHistoryFilterCompany] = useState('');
  const [historyFilterCompetence, setHistoryFilterCompetence] = useState('');
  const [filesPage, setFilesPage] = useState(1);
  const [filesStatusFilter, setFilesStatusFilter] = useState<string>('all');
  const filesSectionRef = useRef<HTMLDivElement | null>(null);

  const JOBS_PAGE_SIZE = 5;
  const FILES_PAGE_SIZE = 10;
  const queryClient = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: ['nfse-jobs'],
    queryFn: () => nfseApi.listImportJobs(),
    refetchInterval: 5000,
  });

  const selectedJobQuery = useQuery({
    queryKey: ['nfse-job', selectedJobId],
    queryFn: () => nfseApi.getImportJob(selectedJobId!),
    enabled: Boolean(selectedJobId),
    refetchInterval: 4000,
    initialData: () => jobsQuery.data?.find((job) => job.id === selectedJobId),
  });

  const filteredFiles = useMemo(() => {
    if (!selectedJobQuery.data) return [];
    const files = selectedJobQuery.data.files || [];
    if (filesStatusFilter === 'all') return files;
    return files.filter((file) => file.status === filesStatusFilter);
  }, [filesStatusFilter, selectedJobQuery.data]);

  useEffect(() => {
    setFilesPage(1);
  }, [filesStatusFilter, selectedJobId]);

  const totalFilesPages = Math.max(1, Math.ceil(filteredFiles.length / FILES_PAGE_SIZE));
  const paginatedFiles = filteredFiles.slice(
    (filesPage - 1) * FILES_PAGE_SIZE,
    filesPage * FILES_PAGE_SIZE,
  );

  useEffect(() => {
    setHistoryPage(1);
  }, [historyFilterCompany, historyFilterCompetence]);

  useEffect(() => {
    const handler = setTimeout(() => {
      const term = companyQuery.trim();
      if (term.length < 2) {
        setCompanyOptions([]);
        setCompanyError(null);
        return;
      }
      setIsSearchingCompany(true);
      setCompanyError(null);
      nfseApi
        .searchCompanies(term)
        .then((data) => setCompanyOptions(data))
        .catch(() => setCompanyError('Não foi possível carregar empresas.'))
        .finally(() => setIsSearchingCompany(false));
    }, 250);
    return () => clearTimeout(handler);
  }, [companyQuery]);

  useEffect(() => {
    if (options.companyCode && !companyQuery) {
      const label = options.companyName
        ? `${options.companyCode} - ${options.companyName}`
        : options.companyCode;
      setCompanyQuery(label);
    }
  }, [companyQuery, options.companyCode, options.companyName]);

  const jobStats = useMemo(() => {
    const jobs = jobsQuery.data ?? [];
    return {
      total: jobs.length,
      processing: jobs.filter((job) => job.status === 'processing').length,
      completed: jobs.filter((job) => job.status === 'completed').length,
      failed: jobs.filter((job) => job.status === 'failed').length,
    };
  }, [jobsQuery.data]);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/zip': ['.zip'],
    },
    onDropAccepted: (files) => handleAddFiles(files),
    maxSize: 150 * 1024 * 1024,
    multiple: true,
  });

  const totalQueueSize = useMemo(
    () => queuedFiles.reduce((sum, item) => sum + item.size, 0),
    [queuedFiles],
  );

  const filteredJobs = useMemo(() => {
    const jobs = jobsQuery.data ?? [];
    return jobs.filter((job) => {
      const companyMatch = historyFilterCompany
        ? job.options.companyCode.toLowerCase().includes(historyFilterCompany.toLowerCase()) ||
          (job.options.companyName || '').toLowerCase().includes(historyFilterCompany.toLowerCase())
        : true;
      const competenceMatch = historyFilterCompetence
        ? (job.options.competencePeriod || '').includes(
            historyFilterCompetence.replace(/\D/g, ''),
          )
        : true;
      return companyMatch && competenceMatch;
    });
  }, [historyFilterCompany, historyFilterCompetence, jobsQuery.data]);

  const totalHistoryPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PAGE_SIZE));
  const paginatedJobs = filteredJobs.slice(
    (historyPage - 1) * JOBS_PAGE_SIZE,
    historyPage * JOBS_PAGE_SIZE,
  );

  useEffect(() => {
    if (!fileRejections.length) return;
    const [first] = fileRejections;
    if (first.errors[0]) {
      setUploadError(first.errors[0].message);
    }
  }, [fileRejections]);

  const handleAddFiles = useCallback((files: File[]) => {
    setUploadError(null);
    setQueuedFiles((prev) => {
      const existingKeys = new Set(prev.map((item) => `${item.name}-${item.size}-${item.file.lastModified}`));
      const append = files
        .filter((file) => {
          const key = `${file.name}-${file.size}-${file.lastModified}`;
          return !existingKeys.has(key);
        })
        .map((file) => ({
          id: nanoid(),
          file,
          name: file.name,
          size: file.size,
          status: 'waiting' as QueueStatus,
          progress: 0,
        }));
      return [...prev, ...append];
    });
  }, []);

  const handleCompanyInput = (value: string) => {
    setCompanyQuery(value);
    const code = value.split('-')[0]?.trim() || '';
    if (!code) {
      setOptions((prev) => ({ ...prev, companyCode: '', companyName: '' }));
      return;
    }
    const match = companyOptions.find((item) => item.code === code);
    if (match) {
      setOptions((prev) => ({ ...prev, companyCode: match.code, companyName: match.name }));
      setCompanyQuery(`${match.code} - ${match.name}`);
      return;
    }
    setOptions((prev) => ({ ...prev, companyCode: code }));
  };

  const handleSelectCompany = (option: CompanyOption) => {
    setCompanyQuery(`${option.code} - ${option.name}`);
    setOptions((prev) => ({ ...prev, companyCode: option.code, companyName: option.name }));
  };

  const clearQueue = () => {
    setQueuedFiles([]);
    setTotalUploadProgress(0);
  };

  const updateQueuedFile = (id: string, patch: Partial<QueuedFile>) => {
    setQueuedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  };

  const buildDescriptors = async () => {
    const descriptors = [];
    const totalBytes = totalQueueSize || 1;
    let uploadedBytes = 0;
    for (const item of queuedFiles) {
      updateQueuedFile(item.id, { status: 'uploading', progress: 0, error: undefined });
      let uploadedForFile = 0;
      try {
        const descriptor = await nfseApi.uploadFile(item.file, {
          onProgress: (progress) => {
            const bytesForFile = Math.round((progress / 100) * item.size);
            uploadedForFile = bytesForFile;
            const overall = Math.min(
              99,
              Math.round(((uploadedBytes + uploadedForFile) / totalBytes) * 100),
            );
            setTotalUploadProgress(overall);
          },
        });
        descriptors.push(descriptor);
        uploadedBytes += item.size;
        setTotalUploadProgress(Math.round((uploadedBytes / totalBytes) * 100));
        updateQueuedFile(item.id, { status: 'uploaded', progress: 100 });
      } catch (error) {
        console.error(error);
        updateQueuedFile(item.id, {
          status: 'error',
          error: 'Falha ao enviar arquivo.',
        });
        setTotalUploadProgress(0);
        throw new Error(`Falha ao enviar ${item.name}. Tente novamente.`);
      }
    }
    return descriptors;
  };

  const handleUpload = async () => {
    if (!queuedFiles.length) return;
    setIsSubmitting(true);
    setUploadError(null);
    setDownloadError(null);
    try {
      const descriptors = await buildDescriptors();
      const job = await nfseApi.createImportJob({
        files: descriptors,
        options,
      });
      setQueuedFiles([]);
      setTotalUploadProgress(0);
      setSelectedJobId(job.id);
      queryClient.setQueryData(['nfse-job', job.id], job);
      await jobsQuery.refetch();
    } catch (error) {
      const responseData = (error as any)?.response?.data;
      const nestedMessage =
        responseData?.detail ||
        responseData?.companyCode?.[0] ||
        responseData?.options?.companyCode?.[0] ||
        responseData?.options?.competencePeriod?.[0] ||
        (error instanceof Error ? error.message : undefined);
      const message =
        typeof nestedMessage === 'string'
          ? nestedMessage
          : 'Não foi possível iniciar o processamento. Verifique a API e tente novamente.';
      setUploadError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownload = async (
    jobId: string,
    category: 'services' | 'others' | 'services-excel',
  ) => {
    setDownloadError(null);
    setDownloading(`${jobId}-${category}`);
    try {
      const blob = await nfseApi.downloadInvoices(jobId, category);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const extension = category === 'services-excel' ? 'xlsx' : 'zip';
      link.download = `job-${jobId.slice(0, 8)}-${category}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      setDownloadError('Não foi possível gerar o download.');
    } finally {
      setDownloading(null);
    }
  };

  const reprocessMutation = useMutation({
    mutationFn: (fileIds: string[]) =>
      nfseApi.reprocessFiles(selectedJobId!, {
        fileIds,
      }),
    onSuccess: async (job) => {
      queryClient.setQueryData(['nfse-job', job.id], job);
      setSelectedFiles([]);
      await jobsQuery.refetch();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => nfseApi.deleteJob(jobId),
    onSuccess: async () => {
      setSelectedFiles([]);
      setSelectedJobId(null);
      await jobsQuery.refetch();
    },
  });

  const selectedJob = selectedJobQuery.data;
  const isCompetenceValid = /^\d{6}$/.test(options.competencePeriod);
  const hasRequiredMetadata = Boolean(options.companyCode.trim()) && isCompetenceValid;
  const showCompetenceError = competenceTouched && !isCompetenceValid;
  const canSubmit = queuedFiles.length > 0 && !isSubmitting && hasRequiredMetadata;
  const canReprocess = selectedFiles.length > 0 && selectedJobId && !reprocessMutation.isPending;

  const toggleSelectedFile = (fileId: string) => {
    setSelectedFiles((prev) =>
      prev.includes(fileId) ? prev.filter((id) => id !== fileId) : [...prev, fileId],
    );
  };

  return (
    <div className="import-page">
      <section className="page-hero">
        <div>
          <p className="page-hero__eyebrow">Ferramentas / Importação de NFs</p>
          <h1>Importação Inteligente de NFSe</h1>
          {/* <div className="page-hero__meta">
            <span>Verificação automática se a nota é de serviço</span>
            <span>Fallback para Ollama ou GPT configurável</span>
          </div> */}
        </div>
        <div className="page-hero__actions">
          <button type="button" className="btn btn--ghost" onClick={() => jobsQuery.refetch()}>
            <RefreshCcw size={16} />
            Atualizar
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => setShowSettings(true)}>
            <Settings size={16} />
            Configurações
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <span>Processos ativos</span>
          <strong>{jobStats.processing}</strong>
          <small>{jobStats.total} totais</small>
        </article>
        <article className="stat-card">
          <span>Concluídos</span>
          <strong>{jobStats.completed}</strong>
          <small>Últimas execuções</small>
        </article>
        <article className="stat-card">
          <span>Falhas recentes</span>
          <strong>{jobStats.failed}</strong>
          <small>Verifique os arquivos na tabela</small>
        </article>
      </section>

      <div className="grid-two-columns">
        <section className="card upload-card">
          <header className="card__header">
            <div>
              <h2>Enviar novos arquivos</h2>
            </div>
          </header>

          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'dropzone--active' : ''}`}
          >
            <input {...getInputProps()} />
            <CloudUpload size={32} />
            <p>
              Arraste até 1000 PDFs ou um arquivo .zip
              <br />
              <span>ou clique para selecionar</span>
            </p>
          </div>

          {queuedFiles.length > 0 && (
            <div className="upload-summary">
              <div>
                <strong>{queuedFiles.length} arquivo(s) selecionado(s)</strong>
                <small>Tamanho total: {formatBytes(totalQueueSize)}</small>
              </div>
              <div className="upload-summary__meta">
                <span>
                  {isSubmitting
                    ? 'Enviando lote...'
                    : 'Tudo ou nada: o envio é cancelado se algum arquivo falhar.'}
                </span>
                <button type="button" className="text-button" onClick={clearQueue}>
                  Limpar seleção
                </button>
              </div>
              {(isSubmitting || totalUploadProgress > 0) && (
                <div className="upload-summary__progress">
                  <div className="progress">
                    <div
                      className="progress__bar"
                      style={{ width: `${totalUploadProgress}%` }}
                    />
                  </div>
                  <span>{totalUploadProgress}%</span>
                </div>
              )}
            </div>
          )}

          <div className="options-grid">
            <label className="company-field">
              Empresa (código - razão social)
              <input
                type="text"
                placeholder="Busque por código ou nome"
                value={companyQuery}
                list="company-options"
                onChange={(event) => handleCompanyInput(event.target.value)}
              />
              <datalist id="company-options">
                {companyOptions.map((company) => (
                  <option key={company.code} value={`${company.code} - ${company.name}`} />
                ))}
              </datalist>
              <small className="field-hint">
                {isSearchingCompany
                  ? 'Buscando empresas...'
                  : 'Digite pelo menos 2 caracteres para buscar pela razão social ou código.'}
              </small>
              {options.companyCode && (
                <small className="field-hint">
                  Selecionada: {options.companyCode}
                  {options.companyName ? ` - ${options.companyName}` : ''}
                </small>
              )}
              {companyError && (
                <small className="field-hint field-hint--error">{companyError}</small>
              )}
            </label>
            <label>
              Competência (MMYYYY)
              <input
                type="text"
                placeholder="MMYYYY"
                inputMode="numeric"
                maxLength={6}
                value={options.competencePeriod}
                onChange={(event) => {
                  const digits = event.target.value.replace(/\D/g, '').slice(0, 6);
                  if (!digits) {
                    setCompetenceTouched(false);
                  }
                  setOptions((prev) => ({ ...prev, competencePeriod: digits }));
                }}
                onBlur={() => setCompetenceTouched(true)}
              />
              {showCompetenceError && (
                <small className="field-hint field-hint--error">Use o formato MMYYYY.</small>
              )}
            </label>
          </div>

          {uploadError && (
            <div className="alert alert--error">
              <AlertTriangle size={16} />
              <span>{uploadError}</span>
            </div>
          )}

          <div className="card__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={!canSubmit}
              onClick={handleUpload}
            >
              {isSubmitting ? <Loader2 className="spin" size={16} /> : <UploadCloud size={16} />}
              Enviar para processamento
            </button>
          </div>
        </section>

      </div>

      {showSettings && (
        <div className="modal">
          <div className="modal__backdrop" onClick={() => setShowSettings(false)} />
          <div className="modal__content">
            <header className="modal__header">
              <h3>Configurações de processamento</h3>
              <button type="button" className="text-button" onClick={() => setShowSettings(false)}>
                Fechar
              </button>
            </header>
            <div className="modal__body">
              <div className="options-grid">
                <label>
                  Idioma do OCR
                  <select
                    value={options.ocrLanguage}
                    onChange={(event) =>
                      setOptions((prev) => ({ ...prev, ocrLanguage: event.target.value }))
                    }
                  >
                    <option value="por">Português</option>
                    <option value="eng">Inglês</option>
                    <option value="spa">Espanhol</option>
                  </select>
                </label>
                <label>
                  Modelo LLM
                  <select
                    value={options.model}
                    onChange={(event) =>
                      setOptions((prev) => ({ ...prev, model: event.target.value }))
                    }
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                    <option value="gpt-4o-mini-fast">gpt-4o-mini-fast</option>
                    <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                  </select>
                </label>
                <label>
                  Base URL (opcional)
                  <input
                    type="text"
                    placeholder="http://127.0.0.1:11434/v1"
                    value={options.baseUrl}
                    onChange={(event) =>
                      setOptions((prev) => ({ ...prev, baseUrl: event.target.value }))
                    }
                  />
                </label>
              </div>
            </div>
            <footer className="modal__footer">
              <button type="button" className="btn btn--primary" onClick={() => setShowSettings(false)}>
                Salvar
              </button>
            </footer>
          </div>
        </div>
      )}

      <section className="card">
        <header className="card__header">
          <div>
            <h3>Histórico de cargas</h3>
          </div>
        </header>
        <div className="filters-row">
          <input
            type="text"
            placeholder="Filtrar por empresa"
            value={historyFilterCompany}
            onChange={(e) => setHistoryFilterCompany(e.target.value)}
          />
          <input
            type="text"
            placeholder="Competência (MMYYYY)"
            value={historyFilterCompetence}
            onChange={(e) =>
              setHistoryFilterCompetence(e.target.value.replace(/\D/g, '').slice(0, 6))
            }
          />
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Processo</th>
                <th>Empresa</th>
                <th>Competência</th>
                <th>Criado em</th>
                <th>Arquivos</th>
                <th>Status</th>
                <th>Serviços</th>
                <th>Outros</th>
                <th>Planilha</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {paginatedJobs.map((job) => (
                <tr
                  key={job.id}
                  className={selectedJobId === job.id ? 'row--active' : undefined}
                  onClick={() => {
                    setSelectedJobId(job.id);
                    setSelectedFiles([]);
                    setFilesPage(1);
                    setTimeout(() => {
                      filesSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
                    }, 50);
                  }}
                >
                  <td>{job.id.slice(0, 8)}</td>
                  <td>
                    <div className="company-badge">
                      <strong>{job.options.companyCode || '—'}</strong>
                      <span>{job.options.companyName || 'Empresa não informada'}</span>
                    </div>
                  </td>
                  <td>{formatCompetence(job.options.competencePeriod)}</td>
                  <td>{formatDateTime(job.createdAt)}</td>
                  <td>
                    {job.totals.completed}/{job.totals.totalFiles}
                  </td>
              <td>
                    <StatusBadge status={job.displayStatus || job.status} />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="text-button"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDownload(job.id, 'services');
                      }}
                      disabled={downloading === `${job.id}-services`}
                    >
                      {downloading === `${job.id}-services` ? (
                        <Loader2 className="spin" size={14} />
                      ) : (
                        <Download size={14} />
                      )}
                      Serviços
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="text-button"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDownload(job.id, 'others');
                      }}
                      disabled={downloading === `${job.id}-others`}
                    >
                      {downloading === `${job.id}-others` ? (
                        <Loader2 className="spin" size={14} />
                      ) : (
                        <Download size={14} />
                      )}
                      Outros
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="text-button"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDownload(job.id, 'services-excel');
                      }}
                      disabled={downloading === `${job.id}-services-excel`}
                    >
                      {downloading === `${job.id}-services-excel` ? (
                        <Loader2 className="spin" size={14} />
                      ) : (
                        <Download size={14} />
                      )}
                      Planilha
                    </button>
                  </td>
                  <td className="actions-cell">
                    <button
                      type="button"
                      className="icon-button icon-button--danger"
                      title="Excluir processo"
                      disabled={deleteMutation.isPending}
                      onClick={(event) => {
                        event.stopPropagation();
                        deleteMutation.mutate(job.id);
                      }}
                    >
                      {deleteMutation.isPending ? <Loader2 className="spin" size={14} /> : <Trash size={16} />}
                    </button>
                  </td>
                </tr>
              ))}
              {paginatedJobs.length === 0 && (
                <tr>
                  <td colSpan={10}>
                    <div className="empty-state">
                      <p>Sem processos ainda. Inicie um upload para preencher este histórico.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <button
            type="button"
            className="text-button"
            disabled={historyPage === 1}
            onClick={() => setHistoryPage(1)}
          >
            {'<<'}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={historyPage === 1}
            onClick={() => setHistoryPage((prev) => Math.max(1, prev - 1))}
          >
            {'<'}
          </button>
          <span>
            Página {historyPage} de {totalHistoryPages}
          </span>
          <button
            type="button"
            className="text-button"
            disabled={historyPage === totalHistoryPages}
            onClick={() =>
              setHistoryPage((prev) => Math.min(totalHistoryPages, prev + 1))
            }
          >
            {'>'}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={historyPage === totalHistoryPages}
            onClick={() => setHistoryPage(totalHistoryPages)}
          >
            {'>>'}
          </button>
        </div>
        {downloadError && (
          <div className="alert alert--error">
            <AlertTriangle size={16} />
            <span>{downloadError}</span>
          </div>
        )}
      </section>

      {selectedJob && (
        <section className="card">
          <header className="card__header">
            <div>
              <h3>Arquivos do processo</h3>
              <div className="process-summary">
                <strong>Processo:</strong> {selectedJob.id.slice(0, 8)} ·{' '}
                <strong>Empresa:</strong> {selectedJob.options.companyCode}
                {selectedJob.options.companyName ? ` - ${selectedJob.options.companyName}` : ''} ·{' '}
                <strong>Competência:</strong> {formatCompetence(selectedJob.options.competencePeriod)}
              </div>
            </div>
          </header>
          <div className="table-wrapper table-wrapper--files" ref={filesSectionRef}>
            <div className="filters-row">
              <label>
                Status
                <select
                  value={filesStatusFilter}
                  onChange={(e) => setFilesStatusFilter(e.target.value)}
                >
                  <option value="all">Todos</option>
                  <option value="pending">Pendente</option>
                  <option value="uploading">Enviando</option>
                  <option value="processing">Processando</option>
                  <option value="completed">Concluído</option>
                  <option value="error">Erro</option>
                  <option value="ignored">Ignorado</option>
                  <option value="skipped">Ignorado (pulado)</option>
                </select>
              </label>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Status</th>
                  <th>Etapa</th>
                  <th>Atualizado</th>
                  <th>Mensagem</th>
                </tr>
              </thead>
              <tbody>
                {paginatedFiles.map((file) => (
                  <tr key={file.id}>
                    <td>
                      <div className="file-name">
                        <FileText size={14} />
                        <span>{file.fileName}</span>
                        <small>{formatBytes(file.size)}</small>
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={file.status} />
                    </td>
                    <td>{file.stage}</td>
                    <td>{formatDateTime(file.updatedAt)}</td>
                    <td className="file-message">{file.message || '—'}</td>
                  </tr>
                ))}
                {paginatedFiles.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-state">
                        <p>
                          {selectedJob
                            ? 'Nenhum arquivo encontrado para este filtro.'
                            : 'Selecione um processo para listar os arquivos.'}
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className="pagination">
              <button
                type="button"
            className="text-button"
            disabled={filesPage === 1}
            onClick={() => setFilesPage(1)}
          >
            {'<<'}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={filesPage === 1}
            onClick={() => setFilesPage((prev) => Math.max(1, prev - 1))}
          >
            {'<'}
          </button>
          <span>
            Página {filesPage} de {totalFilesPages}
          </span>
              <button
                type="button"
                className="text-button"
                disabled={filesPage === totalFilesPages}
                onClick={() => setFilesPage((prev) => Math.min(totalFilesPages, prev + 1))}
              >
                {'>'}
              </button>
              <button
                type="button"
                className="text-button"
                disabled={filesPage === totalFilesPages}
                onClick={() => setFilesPage(totalFilesPages)}
              >
                {'>>'}
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default ImportacaoNfsPage;
