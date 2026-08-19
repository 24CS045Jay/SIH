const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const TOKEN_KEY = "kmrl_demo_access_token";

export class ApiError extends Error {
  status: number;
  code: "network" | "timeout" | "http" | "parse";
  detail?: string;

  constructor(message: string, status = 0, code: ApiError["code"] = "http", detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

function expireSession() {
  localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new CustomEvent("kmrl:session-expired"));
}

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    const raw = await response.text();
    let data: any = null;
    try { data = raw ? JSON.parse(raw) : null; } catch { throw new ApiError("The server returned an unreadable response.", response.status, "parse"); }
    if (response.status === 401) {
      expireSession();
      throw new ApiError("Your session expired — please sign in again.", 401, "http");
    }
    if (!response.ok) {
      const detail = typeof data?.detail === "string" ? data.detail : undefined;
      if (response.status === 403) throw new ApiError(detail ?? "You do not have permission to perform this action.", 403, "http", detail);
      if (response.status === 404) throw new ApiError(detail ?? "The requested portal resource was not found.", 404, "http", detail);
      if (response.status >= 500) throw new ApiError(detail ?? "The portal service is temporarily unavailable.", response.status, "http", detail);
      throw new ApiError(detail ?? `The request could not be completed (HTTP ${response.status}).`, response.status, "http", detail);
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new ApiError("This is taking longer than expected — try again or rephrase the question.", 408, "timeout");
    throw new ApiError("Unable to connect to the portal service. Check the backend and try again.", 0, "network");
  } finally {
    window.clearTimeout(timeout);
  }
}

export function apiUrl(path: string) { return `${API_BASE}${path}`; }
export function authHeaders(token: string) { return { Authorization: `Bearer ${token}` }; }
export { API_BASE };
