import { TokenResponse } from "./types";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

const ACCESS_TOKEN_KEY = "kip_access_token";
const REFRESH_TOKEN_KEY = "kip_refresh_token";

export class ApiError extends Error {
  status: number;
  isNetwork: boolean;

  constructor(message: string, options: { status?: number; isNetwork?: boolean } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? 0;
    this.isNetwork = options.isNetwork ?? false;
  }
}

/**
 * Tokens live in localStorage so a player stays signed in when she closes the
 * tab or reopens the installed app - sessionStorage logged everyone out.
 */
export const tokenStore = {
  read(): { access: string | null; refresh: string | null } {
    try {
      return {
        access: localStorage.getItem(ACCESS_TOKEN_KEY),
        refresh: localStorage.getItem(REFRESH_TOKEN_KEY),
      };
    } catch {
      return { access: null, refresh: null };
    }
  },
  write(tokens: TokenResponse) {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    } catch {
      /* private mode - session keeps working in memory */
    }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

let accessToken: string | null = tokenStore.read().access;
let refreshToken: string | null = tokenStore.read().refresh;
let refreshInFlight: Promise<string> | null = null;
let onSessionExpired: (() => void) | null = null;

export function setTokens(tokens: TokenResponse | null) {
  if (!tokens) {
    accessToken = null;
    refreshToken = null;
    tokenStore.clear();
    return;
  }
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  tokenStore.write(tokens);
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

async function rawRequest<T>(path: string, init: RequestInit, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string> | undefined) ?? {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("network", { isNetwork: true });
  }

  if (!response.ok) {
    const text = await response.text();
    let detail = text || `HTTP ${response.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: string | { msg?: string }[] };
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      } else if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
        detail = parsed.detail[0].msg as string;
      }
    } catch {
      /* body was not JSON - keep the raw text */
    }
    throw new ApiError(detail, { status: response.status });
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function refreshAccessToken(): Promise<string> {
  if (!refreshToken) {
    throw new ApiError("no refresh token", { status: 401 });
  }
  if (!refreshInFlight) {
    refreshInFlight = rawRequest<TokenResponse>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then((tokens) => {
        setTokens(tokens);
        return tokens.access_token;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

type RequestOptions = RequestInit & { auth?: boolean };

/**
 * Authenticated calls transparently refresh the access token once on 401, so a
 * short-lived token never interrupts a player mid-form.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, ...init } = options;
  if (!auth) {
    return rawRequest<T>(path, init);
  }

  try {
    return await rawRequest<T>(path, init, accessToken);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !refreshToken) {
      throw error;
    }

    let fresh: string;
    try {
      fresh = await refreshAccessToken();
    } catch (refreshError) {
      if (refreshError instanceof ApiError && refreshError.isNetwork) {
        throw refreshError;
      }
      setTokens(null);
      onSessionExpired?.();
      throw new ApiError("session expired", { status: 401 });
    }

    // Only a failed refresh means the session is over. If the retry with a
    // brand-new token still answers 401, the endpoint is saying something
    // about the request itself - a wrong password on a confirmation prompt,
    // for instance - and signing the player out would hide that.
    return await rawRequest<T>(path, init, fresh);
  }
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const tokens = await rawRequest<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setTokens(tokens);
  return tokens;
}

export async function logoutRequest(): Promise<void> {
  const token = refreshToken;
  setTokens(null);
  if (!token) return;
  try {
    await rawRequest("/api/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: token }),
    });
  } catch {
    /* logging out locally is enough if the server is unreachable */
  }
}
