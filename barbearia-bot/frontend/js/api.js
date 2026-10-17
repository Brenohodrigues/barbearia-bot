/*
 * Cliente HTTP simples para consumir a API do backend a partir do painel.
 * O token JWT é guardado em localStorage (apenas neste painel administrativo
 * local, servido pelo próprio backend - não é um artifact hospedado).
 */
const API_BASE = "/api/v1";

const Api = {
  getToken() {
    return localStorage.getItem("barbearia_token");
  },
  setToken(token) {
    localStorage.setItem("barbearia_token", token);
  },
  clearToken() {
    localStorage.removeItem("barbearia_token");
  },

  async request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const token = this.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = "/painel/login.html";
      throw new Error("Sessão expirada. Faça login novamente.");
    }

    if (response.status === 204) return null;

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Erro ao comunicar com o servidor.");
    }
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  del(path) { return this.request("DELETE", path); },
};
