import axios from 'axios';
import { authApi, authHeaders } from './auth';
import { authStorage } from '../utils/authStorage';
import type { DctfwebPosicaoGeralResponse } from '../types/auditores';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
type ExportKind = 'csv' | 'excel';

class AuditoresApi {
  async getPosicaoGeral(competencia?: string): Promise<DctfwebPosicaoGeralResponse> {
    const send = async () => {
      const response = await axios.get(`${API_BASE_URL}/api/auditores/posicao-geral/`, {
        withCredentials: true,
        headers: authHeaders(),
        params: competencia ? { competencia } : undefined,
      });
      return response.data;
    };
    return this.withAuthRetry(send);
  }

  async exportPosicaoGeral(kind: ExportKind, competencia?: string): Promise<Blob> {
    const send = async () => {
      const response = await axios.get(`${API_BASE_URL}/api/auditores/posicao-geral/`, {
        withCredentials: true,
        headers: authHeaders(),
        params: {
          export: kind,
          ...(competencia ? { competencia } : {}),
        },
        responseType: 'blob',
      });
      return response.data as Blob;
    };
    return this.withAuthRetry(send);
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

export const auditoresApi = new AuditoresApi();
