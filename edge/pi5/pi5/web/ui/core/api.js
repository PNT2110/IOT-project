// core/api.js - API client, screen lifecycle, and cookie helpers

export const API = "/api/pi/v1";
export const app = document.getElementById("app");
export const topActions = document.getElementById("top-actions");

let me = null;
let timers = [];
let cleanup = [];

export function getMe() {
  return me;
}

export function setMe(user) {
  me = user;
}

export function getTimers() {
  return timers;
}

export function getCleanup() {
  return cleanup;
}

export function addCleanup(fn) {
  cleanup.push(fn);
}

export function cookie(name) {
  return document.cookie.split("; ").find((part) => part.startsWith(name + "="))?.slice(name.length + 1);
}

export async function api(path, { method = "GET", body, bearer } = {}) {
  const headers = { Accept: "application/json" };
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isFormData) headers["Content-Type"] = "application/json";
  if (bearer) headers.Authorization = `Bearer ${bearer}`;
  if (method !== "GET") {
    const csrf = cookie("pi_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let response;
  try {
    const requestBody = isFormData ? body : (body === undefined ? undefined : JSON.stringify(body));
    response = await fetch(API + path, { method, headers, credentials: "same-origin", body: requestBody });
  } catch {
    throw Object.assign(new Error("Không kết nối được tới Pi. Kiểm tra Wi-Fi rồi thử lại."), { code: "NETWORK" });
  }
  let payload = null;
  try { payload = await response.json(); } catch { /* non-JSON error */ }
  if (!response.ok || payload?.error) {
    throw Object.assign(new Error(payload?.error?.message_for_user ?? "Yêu cầu không thành công."), { code: payload?.error?.code ?? "ERROR", status: response.status });
  }
  return payload.data;
}

export function clearScreen() {
  timers.forEach(clearInterval);
  timers = [];
  cleanup.forEach((fn) => fn());
  cleanup = [];
  const main = app || document.getElementById("app");
  if (main) main.replaceChildren();
  const top = topActions || document.getElementById("top-actions");
  if (top) top.replaceChildren();
}

export function every(ms, fn) {
  fn();
  const id = setInterval(fn, ms);
  timers.push(id);
  return id;
}
