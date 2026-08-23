const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ProjectResponse {
  id: string;
  title: string | null;
  status: string;
}

export interface AssetResponse {
  id: string;
  project_id: string;
  filename: string;
  order: number;
}

export interface ApiErrorBody {
  error: string;
  code: string;
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error);
    this.code = body.code;
    this.status = status;
  }
}

async function parseOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ error: res.statusText, code: "unknown" }))) as ApiErrorBody;
    throw new ApiError(res.status, body);
  }
  return res.json() as Promise<T>;
}

export function createProject(title?: string): Promise<ProjectResponse> {
  return fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title ?? null }),
  }).then((res) => parseOrThrow<ProjectResponse>(res));
}

export function uploadAsset(projectId: string, file: File): Promise<AssetResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_BASE}/projects/${projectId}/assets`, {
    method: "POST",
    body: formData,
  }).then((res) => parseOrThrow<AssetResponse>(res));
}
