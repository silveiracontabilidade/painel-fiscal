import axios from 'axios';
import { authStorage } from '../utils/authStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface LoginPayload {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh?: string;
}

export interface UserProfile {
  id: number;
  username: string;
  nome?: string;
  email?: string;
}

export interface RefreshResponse {
  access: string;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const response = await axios.post(`${API_BASE_URL}/api/token/`, payload);
    const data = response.data as LoginResponse;
    authStorage.setTokens(data.access, data.refresh);
    return data;
  },
  async refresh(): Promise<string> {
    const refresh = authStorage.getRefreshToken();
    if (!refresh) {
      throw new Error('Refresh token ausente');
    }
    const response = await axios.post<RefreshResponse>(`${API_BASE_URL}/api/token/refresh/`, {
      refresh,
    });
    const token = response.data.access;
    if (!token) {
      throw new Error('Token de acesso não retornado');
    }
    authStorage.setTokens(token, refresh);
    return token;
  },
  async fetchProfile(): Promise<UserProfile> {
    const token = authStorage.getAccessToken();
    const response = await axios.get(`${API_BASE_URL}/api/me`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      withCredentials: true,
    });
    return response.data;
  },
};

export const authHeaders = () => {
  const token = authStorage.getAccessToken();
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
};
