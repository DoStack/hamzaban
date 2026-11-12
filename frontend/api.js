function csrf() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  let payload;
  if (body instanceof FormData) {
    headers["X-CSRFToken"] = csrf();
    payload = body;
  } else if (body) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrf();
    payload = JSON.stringify(body);
  }
  const response = await fetch(path, { method, headers, body: payload, credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.message || "درخواست انجام نشد.");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

export function csrfToken() {
  return csrf();
}
