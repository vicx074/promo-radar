import type {OwnerSession} from "../types";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

let csrfToken: string | null = null;

function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as {detail: unknown}).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as {message?: unknown}).message;
      if (typeof message === "string") return message;
    }
    if (Array.isArray(detail)) return "Confira os campos informados e tente novamente.";
  }
  return "Não foi possível completar a solicitação (HTTP " + status + ").";
}

async function requestJson<T>(path: string, options: {
  method?: "GET" | "POST";
  body?: unknown;
  csrf?: boolean;
} = {}): Promise<T> {
  // Apenas URLs relativas da API; nunca encaminhar credenciais a domínios externos.
  if (!path.startsWith("/api/v1/") || path.startsWith("//") || /[\\\s#]/.test(path)) {
    throw new Error("Rota inválida.");
  }
  const unsafe = (options.method || "GET") !== "GET";
  if (unsafe && options.csrf && !csrfToken) {
    throw new ApiError("Sessão expirada. Entre novamente.", 401);
  }
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      ...(options.body === undefined ? {} : {"Content-Type": "application/json"}),
      ...(unsafe && options.csrf ? {"x-csrf-token": csrfToken!} : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
    credentials: "same-origin",
    referrerPolicy: "no-referrer",
  });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (!response.ok) throw new ApiError("O servidor não retornou JSON válido.", response.status);
    throw new ApiError("Resposta inesperada do servidor.", response.status);
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/v1/auth/login") {
      csrfToken = null;
      if (typeof window !== "undefined") window.dispatchEvent(new Event("promo:session-expired"));
    }
    throw new ApiError(extractMessage(payload, response.status), response.status);
  }
  return payload as T;
}

export async function loginOwner(password: string): Promise<OwnerSession> {
  const result = await requestJson<OwnerSession>("/api/v1/auth/login", {
    method: "POST",
    body: {password},
  });
  csrfToken = result.csrf_token;
  return result;
}

export async function restoreSession(): Promise<OwnerSession> {
  const result = await requestJson<OwnerSession>("/api/v1/auth/session");
  csrfToken = result.csrf_token;
  return result;
}

export async function logoutOwner(): Promise<void> {
  try {
    await requestJson("/api/v1/auth/logout", {method: "POST", csrf: true});
  } finally {
    csrfToken = null;
  }
}

export function apiRequest<T>(
  path: string,
  options: {method?: "GET" | "POST"; body?: unknown} = {},
): Promise<T> {
  return requestJson<T>(path, {...options, csrf: true});
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "Ocorreu um erro inesperado.";
}
