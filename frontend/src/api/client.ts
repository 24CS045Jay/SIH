import { User } from "../types";

// API base — reads from Vite env var; falls back to localhost for local dev.
// After the Part 1 refactor, NO hardcoded "http://localhost:8000" strings
// remain anywhere else in the codebase — only this single fallback.
export const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const TOKEN_KEY = "kmrl_demo_access_token";
export const USER_KEY = "kmrl_demo_user";
export const THEME_KEY = "kmrl_demo_theme";

export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
  database_reachable: boolean;
  migrations_current: boolean;
  demo_users_seeded: boolean;
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function apiFetch(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers: Record<string, string> = {
    ...authHeaders(token),
    ...(options.headers as Record<string, string> | undefined),
  };
  return fetch(`${API}${path}`, { ...options, headers });
}

export async function apiJson<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await apiFetch(path, token, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? `Request failed: ${response.status}`);
  return data as T;
}

export async function checkHealth(): Promise<HealthStatus> {
  let response: Response;
  try {
    response = await fetch(`${API}/health`);
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API}. Confirm the FastAPI server is running and VITE_API_BASE_URL is correct.`
    );
  }

  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error(
        "The backend is running but the database returned an error. Confirm Postgres is running and migrations have been applied (`alembic upgrade head`)."
      );
    }
    throw new Error(`Health check returned status ${response.status}`);
  }

  return (await response.json()) as HealthStatus;
}

export async function getDemoUsers(): Promise<User[]> {
  // 1. Health check first to pinpoint exact failure mode if any
  try {
    const health = await checkHealth();
    if (!health.database_reachable || !health.migrations_current) {
      throw new Error(
        "The backend is running but the database returned an error. Confirm Postgres is running and migrations have been applied (`alembic upgrade head`)."
      );
    }
    if (!health.demo_users_seeded) {
      throw new Error("No demo users found. Run the seed script: `python scripts/seed.py`.");
    }
  } catch (err) {
    // If checkHealth failed with network or database error, propagate immediately
    if (
      err instanceof Error &&
      (err.message.startsWith("Cannot reach the backend") ||
        err.message.startsWith("The backend is running") ||
        err.message.startsWith("No demo users found"))
    ) {
      throw err;
    }
    // Otherwise continue to fetch demo users
  }

  // 2. Fetch demo users from /auth/demo-users
  let response: Response;
  try {
    response = await fetch(`${API}/auth/demo-users`);
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API}. Confirm the FastAPI server is running and VITE_API_BASE_URL is correct.`
    );
  }

  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error(
        "The backend is running but the database returned an error. Confirm Postgres is running and migrations have been applied (`alembic upgrade head`)."
      );
    }
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail ?? `Request failed: ${response.status}`);
  }

  const data: User[] = await response.json();
  if (!Array.isArray(data) || data.length === 0) {
    throw new Error("No demo users found. Run the seed script: `python scripts/seed.py`.");
  }

  return data;
}

