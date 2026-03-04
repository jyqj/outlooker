import { TIMING } from '../constants';

const STORAGE_KEYS = {
  access: 'admin_token',
  accessExp: 'admin_token_expires_at',
  publicToken: 'public_api_token',
} as const;

export { STORAGE_KEYS };

export interface AuthTokensInput {
  accessToken: string;
  expiresIn: number;
}

export function setAuthTokens({ accessToken, expiresIn }: AuthTokensInput): void {
  const now = Date.now();
  if (accessToken && expiresIn) {
    sessionStorage.setItem(STORAGE_KEYS.access, accessToken);
    sessionStorage.setItem(STORAGE_KEYS.accessExp, String(now + expiresIn * 1000));
  }
}

export function clearAuthTokens(): void {
  sessionStorage.removeItem(STORAGE_KEYS.access);
  sessionStorage.removeItem(STORAGE_KEYS.accessExp);
}

export function getStoredAccessToken(): string | null {
  return sessionStorage.getItem(STORAGE_KEYS.access);
}

export function isAccessTokenValid(): boolean {
  const expiresAt = Number(sessionStorage.getItem(STORAGE_KEYS.accessExp) || 0);
  if (!expiresAt) return false;
  return expiresAt - Date.now() > TIMING.TOKEN_CLOCK_SKEW;
}
