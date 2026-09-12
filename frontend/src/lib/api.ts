import type { ApiErrorBody } from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  /** The raw `detail` field from FastAPI's error body, when it's a
   * structured object (e.g. the 409 odds-changed payload) rather than a
   * plain string — callers that need more than `message` read this. */
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest<T>(path: string, token: string | undefined, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let message = res.statusText;
    let detail: unknown;
    try {
      const body = (await res.json()) as ApiErrorBody;
      detail = body.detail;
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join(", ");
      else if (body.detail && typeof body.detail === "object" && "message" in body.detail) {
        message = String((body.detail as { message: unknown }).message);
      }
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new ApiError(res.status, message, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
