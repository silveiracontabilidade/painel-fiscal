import axios from 'axios';
import type { UserAccount } from '../types/user';
import { authApi, authHeaders } from './auth';
import { authStorage } from '../utils/authStorage';

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

export interface UserPayload {
  username: string;
  email?: string;
  profile: 'administrador' | 'analista';
}

export interface ChangePasswordPayload {
  currentPassword: string;
  newPassword: string;
}

export const usersApi = {
  list(): Promise<UserAccount[]> {
    return withAuthRetry(async () => {
      const response = await axios.get(`${API_BASE_URL}/api/users/`, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data.results ?? response.data;
    });
  },
  create(payload: UserPayload): Promise<UserAccount> {
    return withAuthRetry(async () => {
      const response = await axios.post(`${API_BASE_URL}/api/users/`, payload, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data;
    });
  },
  update(id: number, payload: Partial<UserPayload>): Promise<UserAccount> {
    return withAuthRetry(async () => {
      const response = await axios.patch(`${API_BASE_URL}/api/users/${id}/`, payload, {
        headers: authHeaders(),
        withCredentials: true,
      });
      return response.data;
    });
  },
  delete(id: number): Promise<void> {
    return withAuthRetry(async () => {
      await axios.delete(`${API_BASE_URL}/api/users/${id}/`, {
        headers: authHeaders(),
        withCredentials: true,
      });
    });
  },
  resetPassword(id: number): Promise<void> {
    return withAuthRetry(async () => {
      await axios.post(
        `${API_BASE_URL}/api/users/${id}/reset-password/`,
        {},
        {
          headers: authHeaders(),
          withCredentials: true,
        },
      );
    });
  },
  changeOwnPassword(payload: ChangePasswordPayload): Promise<void> {
    return withAuthRetry(async () => {
      await axios.post(`${API_BASE_URL}/api/users/me/change-password/`, payload, {
        headers: authHeaders(),
        withCredentials: true,
      });
    });
  },
};
