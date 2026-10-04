// F450 PNT PVD · Pi 5 local interface.
// Modular coordinator: imports core and view components, sets up tabs and boots.

import { h, closeModal } from "./core/dom.js";
import { app, topActions, clearScreen, every, api, getMe, setMe, getTimers, getCleanup } from "./core/api.js";
import { wifiScreen } from "./views/wifi.js";
import { authScreen } from "./views/auth.js";
import { cameraView } from "./views/camera.js";
import { mapView } from "./views/map.js";
import { telemetryView } from "./views/telemetry.js";
import { usersView } from "./views/users.js";
import { firmwareView } from "./views/firmware.js";
import { flightModal, profileModal, roleRequestModal, FLIGHT_STATUS } from "./views/flight.js";

function dashboard() {
  clearScreen();
  const me = getMe();
  const admin = me && me.role === "ADMIN";
  const account = h("button", { type: "button", onclick: profileModal }, me?.username || "Tài khoản");
  const logout = h("button", { class: "ghost", type: "button", onclick: async () => { try { await api("/auth/logout", { method: "POST" }); } finally { setMe(null); authScreen("login", null, boot); } } }, "Đăng xuất");

  if (!admin) {
    topActions.append(h("button", { class: "primary", type: "button", onclick: roleRequestModal }, "Xin quyền admin"), account, logout);
    app.append(cameraView());
    return;
  }

  const flightChip = h("span");
  const flightPanel = h("div");
  const refreshFlight = async () => {
    try {
      const items = await api("/flight-requests");
      const latest = items[0];
      if (!latest) {
        flightChip.replaceChildren(h("span", { class: "chip warn" }, "Chưa có phép bay"));
        flightPanel.replaceChildren();
        return;
      }
      const [label, kind] = FLIGHT_STATUS[latest.status] ?? [latest.status, ""];
      const allowed = latest.arm_permission === "ALLOWED";
      flightChip.replaceChildren(h("span", { class: `chip ${allowed ? "ok" : kind}` }, allowed ? "Được phép bay" : label));
      flightPanel.replaceChildren(h("section", { class: "card", style: "margin-bottom:16px" },
        h("div", { class: "row between" },
          h("h3", {}, "Đơn xin bay gần nhất"),
          h("span", { class: `chip ${kind}` }, label)),
        h("dl", { class: "kv" },
          h("dt", {}, "Người bay"), h("dd", {}, latest.full_name),
          h("dt", {}, "Ngày, giờ"), h("dd", {}, `${latest.flight_date} · ${latest.flight_time}${latest.flight_end_time ? ` – ${latest.flight_end_time}` : ""}`),
          h("dt", {}, "Phương tiện"), h("dd", {}, latest.vehicle),
          h("dt", {}, "Định vị gửi kèm"), h("dd", {}, latest.gps ? `${latest.gps.lat.toFixed(6)}, ${latest.gps.lon.toFixed(6)}` : "Không có định vị"),
          latest.reason ? [h("dt", {}, "Ghi chú duyệt"), h("dd", {}, latest.reason)] : null),
        h("p", { class: "muted" }, allowed
          ? "Drone được phép ARM trong khung giờ bay."
          : latest.status === "APPROVED"
            ? "Đơn đã duyệt nhưng chưa tới hoặc đã qua khung giờ bay: drone vẫn khóa ARM."
            : latest.status === "REJECTED"
              ? "Drone bị khóa ARM."
              : "Drone khóa ARM cho tới khi đơn được duyệt.")));
    } catch { /* keep last known state */ }
  };

  topActions.append(flightChip, h("button", { class: "primary", type: "button", onclick: () => flightModal(refreshFlight) }, "Xin cấp phép bay"), account, logout);

  const views = {
    "Camera": cameraView,
    "Bản đồ": mapView,
    "Thông số": telemetryView,
    "Người dùng": usersView,
    "Firmware": firmwareView,
  };
  const content = h("div", { class: "view" });
  const tabs = h("div", { class: "tabs", role: "tablist" });

  const select = (name) => {
    const timers = getTimers();
    timers.forEach(clearInterval);
    timers.length = 0;
    const cleanup = getCleanup();
    cleanup.forEach((fn) => fn());
    cleanup.length = 0;
    for (const button of tabs.children) {
      button.setAttribute("aria-selected", String(button.textContent === name));
    }
    content.replaceChildren(views[name]());
    every(5000, refreshFlight);
  };

  for (const name of Object.keys(views)) {
    tabs.append(h("button", { type: "button", role: "tab", onclick: () => select(name) }, name));
  }
  app.append(flightPanel, tabs, content);
  select("Camera");
}

export async function boot() {
  closeModal();
  try {
    const network = await api("/network/status");
    if (!network.upstream_connected) {
      await wifiScreen(boot);
      return;
    }
  } catch { /* the Pi itself is unreachable; fall through to the sign-in error */ }

  try {
    setMe(await api("/auth/me"));
  } catch {
    setMe(null);
  }

  if (getMe()) {
    dashboard();
  } else {
    authScreen("login", null, boot);
  }
}

// The tab bar sticks right under the top bar, whose height changes when it wraps.
const topBar = document.querySelector(".top");
if (topBar && typeof ResizeObserver !== "undefined") {
  new ResizeObserver(() => document.documentElement.style.setProperty("--top-height", `${topBar.offsetHeight}px`)).observe(topBar);
}

boot();
