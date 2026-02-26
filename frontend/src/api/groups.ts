import axios from 'axios';
import { authApi, authHeaders } from './auth';
import { authStorage } from '../utils/authStorage';
import type { Group } from '../types/group';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const withAuthRetry = async <T>(fn: () => Promise<T>): Promise<T> => {
  try {
    return await fn();
  } catch (error: any) {
    const status = error?.response?.status;
    if (status !== 401) throw error;
    try {
      await authApi.refresh();
    } catch {
      authStorage.clear();
      throw error;
    }
    return fn();
  }
};

export interface GroupPayload {
  nome: string;
  coordenador_id?: number | null;
}

export const groupsApi = {
  list(): Promise<Group[]> {
    return withAuthRetry(async () => {
      const response = await axios.get(`${API_BASE_URL}/api/groups/`, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data.results ?? response.data;
    });
  },
  create(payload: GroupPayload): Promise<Group> {
    return withAuthRetry(async () => {
      const response = await axios.post(`${API_BASE_URL}/api/groups/`, payload, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data;
    });
  },
  update(id: number, payload: Partial<GroupPayload>): Promise<Group> {
    return withAuthRetry(async () => {
      const response = await axios.patch(`${API_BASE_URL}/api/groups/${id}/`, payload, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data;
    });
  },
  delete(id: number): Promise<void> {
    return withAuthRetry(async () => {
      await axios.delete(`${API_BASE_URL}/api/groups/${id}/`, {
        headers: authHeaders(),
        withCredentials: true,
      });
    });
  },
};
