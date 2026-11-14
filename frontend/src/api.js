const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(Array.isArray(detail) ? detail.map(x => x.msg).join(", ") : (detail || "Request failed."));
  }
  return data;
}

export async function submitBug(form) {
  const body = new FormData();
  for (const key of ["title", "project_name", "programming_language", "severity", "description", "stack_trace", "error_logs"]) {
    body.append(key, form[key] || "");
  }
  for (const file of form.files) body.append("files", file);
  return parseResponse(await fetch(`${API_BASE}/bugs`, { method: "POST", body }));
}

export async function fetchBugs() {
  return parseResponse(await fetch(`${API_BASE}/bugs?limit=20`));
}
