import axios from "axios";
export const PUBLIC_DEMO = import.meta.env.VITE_PUBLIC_DEMO === "true";
const showcase = () => import("./browserDemo");
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
  PUBLIC_DEMO
    ? showcase().then((m) =>
        m.demoRequest(
          "get",
          path +
            (params
              ? (path.includes("?") ? "&" : "?") + new URLSearchParams(params)
              : ""),
        ),
      )
    : api.get(path, { params }).then((r) => r.data);
export const post = (path, body = {}) =>
  PUBLIC_DEMO
    ? showcase().then((m) => m.demoRequest("post", path, body))
    : api.post(path, body).then((r) => r.data);
export const put = (path, body) =>
  PUBLIC_DEMO
    ? showcase().then((m) => m.demoRequest("put", path, body))
    : api.put(path, body).then((r) => r.data);
export function websocketUrl() {
  const url = new URL(API_URL, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = url.pathname.replace(/\/$/, "") + "/ws";
  return url.toString();
}
