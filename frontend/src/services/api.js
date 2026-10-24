import axios from "axios";
export const API_URL = process.env.REACT_APP_API_URL || "/api/v1";
const api = axios.create({ baseURL: API_URL, timeout: 12000 });
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401)
      window.dispatchEvent(new Event("auth-required"));
    const detail = error.response?.data?.detail;
    return Promise.reject(
      new Error(
        typeof detail === "string" ? detail : error.message || "Request failed",
      ),
    );
  },
);
export const get = (path, params) =>
  api.get(path, { params }).then((r) => r.data);
export const post = (path, body = {}) =>
  api.post(path, body).then((r) => r.data);
export const put = (path, body) => api.put(path, body).then((r) => r.data);
export function websocketUrl() {
  const url = new URL(API_URL, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = url.pathname.replace(/\/$/, "") + "/ws";
  return url.toString();
}
