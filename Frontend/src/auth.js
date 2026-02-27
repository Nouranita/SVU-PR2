const TOKEN_KEY = "access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function authHeader() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginWithPassword(API_BASE, username, password) {
  const res = await fetch(`${API_BASE}/api/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    throw new Error(data?.detail || `Login failed (${res.status})`);
  }

  // DRF SimpleJWT returns: { access, refresh }
  localStorage.setItem(TOKEN_KEY, data.access);
  localStorage.setItem("refresh_token", data.refresh || "");
  return data;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem("refresh_token");
}
// export so App.jsx can import it
export const clearToken = logout;