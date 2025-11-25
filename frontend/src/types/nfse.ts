export type FileProcessStatus =
  | 'pending'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error'
  | 'skipped'
  | 'ignored';

export type ImportJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ImportJobFile {
  id: string;
  fileName: string;
  size: number;
  status: FileProcessStatus;
  progress: number;
  stage: 'queued' | 'ocr' | 'ai' | 'persisting' | 'done' | 'error';
  message?: string;
  updatedAt: string;
  downloadUrl?: string;
}

export interface ImportJobTotals {
  totalFiles: number;
  uploaded: number;
  processing: number;
  completed: number;
  failed: number;
  ignored: number;
}

export interface ImportJobOptions {
  ocrLanguage: string;
  model: string;
  baseUrl?: string;
  companyCode: string;
  companyName?: string;
  competencePeriod: string;
}

export interface ImportJob {
  id: string;
  createdAt: string;
  status: ImportJobStatus;
  displayStatus?: string;
  options: ImportJobOptions;
  totals: ImportJobTotals;
  files: ImportJobFile[];
  logsUrl?: string;
}

export interface UploadDescriptor {
  fileId: string;
  fileName: string;
  size: number;
  uploadToken: string;
}

export interface CompanyOption {
  code: string;
  name: string;
}
