import axios from 'axios';
import { Upload } from 'tus-js-client';
import { nanoid } from 'nanoid';
import type {
  CompanyOption,
  ImportJob,
  ImportJobOptions,
  UploadDescriptor,
} from '../types/nfse';
import { authApi, authHeaders } from './auth';
import { authStorage } from '../utils/authStorage';

export interface UploadFileOptions {
  onProgress?: (progress: number) => void;
  signal?: AbortSignal;
}

export interface CreateImportJobPayload {
  files: UploadDescriptor[];
  options: ImportJobOptions;
}

export interface ReprocessPayload {
  fileIds: string[];
  options?: Partial<ImportJobOptions>;
}

export interface NfseApi {
  uploadFile(file: File, options?: UploadFileOptions): Promise<UploadDescriptor>;
  createImportJob(payload: CreateImportJobPayload): Promise<ImportJob>;
  listImportJobs(): Promise<ImportJob[]>;
  getImportJob(id: string): Promise<ImportJob>;
  reprocessFiles(jobId: string, payload: ReprocessPayload): Promise<ImportJob>;
  searchCompanies(search: string): Promise<CompanyOption[]>;
  downloadInvoices(
    jobId: string,
    category: 'services' | 'others' | 'services-excel',
  ): Promise<Blob>;
  deleteJob(jobId: string): Promise<void>;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const TUS_ENDPOINT = import.meta.env.VITE_TUS_ENDPOINT || '';
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== 'false';

class HttpNfseApi implements NfseApi {
  async uploadFile(file: File, options?: UploadFileOptions): Promise<UploadDescriptor> {
    const send = async () => {
      if (TUS_ENDPOINT) {
        return this.uploadWithTus(file, options);
      }
      const form = new FormData();
      form.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/api/uploads/`, form, {
        withCredentials: true,
        headers: authHeaders(),
        signal: options?.signal,
        onUploadProgress: (evt) => {
          if (!options?.onProgress || !evt.total) return;
          const progress = Math.round((evt.loaded / evt.total) * 100);
          options.onProgress(progress);
        },
      });
      return response.data;
    };
    return this.withAuthRetry(send);
  }

  async createImportJob(payload: CreateImportJobPayload): Promise<ImportJob> {
    const send = async () => {
      const response = await axios.post(`${API_BASE_URL}/api/nfse/import-jobs/`, payload, {
        withCredentials: true,
        headers: authHeaders(),
      });
      return response.data;
    };
    return this.withAuthRetry(send);
  }

  async listImportJobs(): Promise<ImportJob[]> {
    const send = async () => {
      const response = await axios.get(`${API_BASE_URL}/api/nfse/import-jobs/`, {
        withCredentials: true,
        headers: authHeaders(),
        params: {
          page_size: 50,
        },
      });
      return response.data.results ?? response.data;
    };
    return this.withAuthRetry(send);
  }

  async getImportJob(id: string): Promise<ImportJob> {
    const send = async () => {
      const response = await axios.get(`${API_BASE_URL}/api/nfse/import-jobs/${id}/`, {
        withCredentials: true,
        headers: authHeaders(),
      });
      return response.data;
    };
    return this.withAuthRetry(send);
  }

  async reprocessFiles(jobId: string, payload: ReprocessPayload): Promise<ImportJob> {
    const send = async () => {
      const response = await axios.post(
        `${API_BASE_URL}/api/nfse/import-jobs/${jobId}/reprocess/`,
        payload,
        { withCredentials: true, headers: authHeaders() },
      );
      return response.data;
    };
    return this.withAuthRetry(send);
  }

  async deleteJob(jobId: string): Promise<void> {
    const send = async () => {
      await axios.delete(`${API_BASE_URL}/api/nfse/import-jobs/${jobId}/`, {
        withCredentials: true,
        headers: authHeaders(),
      });
    };
    return this.withAuthRetry(send);
  }

  async searchCompanies(search: string): Promise<CompanyOption[]> {
    const send = async () => {
      const response = await axios.get(`${API_BASE_URL}/api/nfse/companies/`, {
        withCredentials: true,
        headers: authHeaders(),
        params: { search },
      });
      return response.data.results ?? response.data;
    };
    return this.withAuthRetry(send);
  }

  async downloadInvoices(
    jobId: string,
    category: 'services' | 'others' | 'services-excel',
  ): Promise<Blob> {
    const send = async () => {
      const response = await axios.get(
        `${API_BASE_URL}/api/nfse/import-jobs/${jobId}/download/${category}/`,
        {
          withCredentials: true,
          headers: { ...authHeaders() },
          responseType: 'blob',
        },
      );
      return response.data as Blob;
    };
    return this.withAuthRetry(send);
  }

  private uploadWithTus(file: File, options?: UploadFileOptions) {
    return new Promise<UploadDescriptor>((resolve, reject) => {
      const upload = new Upload(file, {
        endpoint: TUS_ENDPOINT,
        metadata: {
          filename: file.name,
          filetype: file.type,
        },
        onError(error) {
          reject(error);
        },
        onProgress(bytesUploaded, bytesTotal) {
          if (!options?.onProgress) return;
          const percentage = Math.round((bytesUploaded / bytesTotal) * 100);
          options.onProgress(percentage);
        },
        onSuccess() {
          resolve({
            fileId: nanoid(),
            fileName: file.name,
            size: file.size,
            uploadToken: upload.url || '',
          });
        },
      });

      if (options?.signal) {
        options.signal.addEventListener('abort', () => {
          upload.abort();
          reject(new DOMException('Upload cancelado', 'AbortError'));
        });
      }

      upload.start();
    });
  }

  private async withAuthRetry<T>(requestFn: () => Promise<T>): Promise<T> {
    try {
      return await requestFn();
    } catch (error: any) {
      const status = error?.response?.status;
      if (status !== 401) throw error;

      try {
        await authApi.refresh();
      } catch {
        authStorage.clear();
        throw error;
      }
      return requestFn();
    }
  }
}

type MutableImportJob = ImportJob & {
  files: (ImportJob['files'][number] & { progress: number })[];
};

const clone = <T>(input: T): T => JSON.parse(JSON.stringify(input));

class MockNfseApi implements NfseApi {
  private jobs: MutableImportJob[] = [];

  constructor() {
    if (typeof globalThis.setInterval === 'function') {
      globalThis.setInterval(() => {
        this.tick();
      }, 1400);
    }
  }

  async uploadFile(file: File, options?: UploadFileOptions): Promise<UploadDescriptor> {
    return new Promise((resolve) => {
      let progress = 0;
      const timer = globalThis.setInterval(() => {
        progress = Math.min(progress + Math.random() * 35 + 10, 100);
        options?.onProgress?.(Math.round(progress));
        if (progress >= 100) {
          globalThis.clearInterval(timer);
          resolve({
            fileId: nanoid(),
            fileName: file.name,
            size: file.size,
            uploadToken: `mock-token-${nanoid()}`,
          });
        }
      }, 180);
    });
  }

  async createImportJob(payload: CreateImportJobPayload): Promise<ImportJob> {
    const job: MutableImportJob = {
      id: nanoid(),
      createdAt: new Date().toISOString(),
      status: 'processing',
      options: payload.options,
      totals: {
        totalFiles: payload.files.length,
        uploaded: payload.files.length,
        processing: payload.files.length,
        completed: 0,
        failed: 0,
        ignored: 0,
      },
      files: payload.files.map((file, index) => ({
        id: file.fileId,
        fileName: file.fileName,
        size: file.size,
        status: index < 3 ? 'processing' : 'pending',
        progress: 0,
        stage: 'queued',
        updatedAt: new Date().toISOString(),
      })),
      logsUrl: undefined,
    };
    this.jobs = [job, ...this.jobs].slice(0, 15);
    return clone(job);
  }

  async listImportJobs(): Promise<ImportJob[]> {
    return this.jobs.map((job) => clone(job));
  }

  async getImportJob(id: string): Promise<ImportJob> {
    const job = this.jobs.find((item) => item.id === id);
    if (!job) {
      throw new Error('Job não encontrado');
    }
    return clone(job);
  }

  async reprocessFiles(jobId: string, payload: ReprocessPayload): Promise<ImportJob> {
    const job = this.jobs.find((item) => item.id === jobId);
    if (!job) {
      throw new Error('Job não encontrado');
    }
    job.status = 'processing';
    job.files = job.files.map((file) =>
      payload.fileIds.includes(file.id)
        ? {
            ...file,
            status: 'pending',
            stage: 'queued',
            progress: 0,
            message: undefined,
          }
        : file,
    );
    this.updateTotals(job);
    return clone(job);
  }

  private tick() {
    let changed = false;
    this.jobs.forEach((job) => {
      job.files.forEach((file) => {
        if (this.isTerminal(file.status)) {
          return;
        }

        const increment = 25 + Math.random() * 30;
        file.progress = Math.min(file.progress + increment, 100);
        if (file.progress < 100) {
          changed = true;
          return;
        }

        file.updatedAt = new Date().toISOString();
        if (file.status === 'pending') {
          file.status = 'uploading';
          file.stage = 'ocr';
          file.progress = 0;
        } else if (file.status === 'uploading') {
          file.status = 'processing';
          file.stage = 'ai';
          file.progress = 0;
        } else if (file.status === 'processing') {
          const failed = Math.random() < 0.1;
          file.status = failed ? 'error' : 'completed';
          file.stage = failed ? 'error' : 'done';
          file.message = failed
            ? 'Falha simulada ao extrair o texto da nota.'
            : 'NF importada com sucesso.';
          file.progress = 100;
        }
        changed = true;
      });
      if (changed) {
        this.updateTotals(job);
      }
    });

    if (!changed) {
      return;
    }
  }

  private updateTotals(job: MutableImportJob) {
    const totals = job.totals;
    totals.totalFiles = job.files.length;
    totals.completed = job.files.filter((f) => f.status === 'completed').length;
    totals.failed = job.files.filter((f) => f.status === 'error').length;
    totals.processing = job.files.filter((f) =>
      ['pending', 'uploading', 'processing'].includes(f.status),
    ).length;
    totals.ignored = job.files.filter((f) => f.status === 'ignored').length;

    if (totals.processing === 0 && totals.failed === 0) {
      job.status = 'completed';
    } else if (totals.processing === 0 && totals.failed > 0) {
      job.status = 'failed';
    } else {
      job.status = 'processing';
    }
  }

  private isTerminal(status: MutableImportJob['files'][number]['status']) {
    return ['completed', 'error', 'ignored', 'skipped'].includes(status);
  }

  async searchCompanies(search: string): Promise<CompanyOption[]> {
    const sample: CompanyOption[] = [
      { code: '100', name: 'Empresa Exemplo 1 LTDA' },
      { code: '200', name: 'Empresa Exemplo 2 SA' },
      { code: '300', name: 'Empresa Serviços Inteligentes' },
    ];
    if (!search) return [];
    const term = search.toLowerCase();
    return sample.filter(
      (item) =>
        item.code.toLowerCase().includes(term) ||
        item.name.toLowerCase().includes(term),
    );
  }

  async downloadInvoices(
    _jobId: string,
    category: 'services' | 'others' | 'services-excel',
  ): Promise<Blob> {
    const blob = new Blob([`Mock download (${category})`], { type: 'text/plain' });
    return blob;
  }
}

export const nfseApi: NfseApi = USE_MOCK_API ? new MockNfseApi() : new HttpNfseApi();
