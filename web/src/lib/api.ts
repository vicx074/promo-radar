export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}
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

export async function apiRequest<T>(
  adminKey: string,
  path: string,
  options: {method?: "GET" | "POST"; body?: unknown} = {},
): Promise<T> {
  if (!path.startsWith("/api/v1/") || path.startsWith("//")) {
    throw new Error("Rota inválida.");
  }
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      "x-admin-key": adminKey,
      ...(options.body === undefined ? {} : {"Content-Type": "application/json"}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
    credentials: "omit",
    referrerPolicy: "no-referrer",
  });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (!response.ok) throw new ApiError("O servidor não retornou JSON válido.", response.status);
    throw new ApiError("Resposta inesperada do servidor.", response.status);
  }
  if (!response.ok) throw new ApiError(extractMessage(payload, response.status), response.status);
  return payload as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "Ocorreu um erro inesperado.";
}
