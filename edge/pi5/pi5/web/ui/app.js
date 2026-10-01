// F450 PNT PVD · Pi 5 local interface.
// Screen 1: connect the Pi to upstream Wi-Fi. Screen 2: sign in, then the
// dashboard for the account's role.
import * as THREE from "/ui/vendor/three.module.min.js";

const API = "/api/pi/v1";
const app = document.getElementById("app");
const topActions = document.getElementById("top-actions");
const modalRoot = document.getElementById("modal-root");
let me = null;
let timers = [];
let cleanup = [];

// ---- helpers

function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === false || value == null) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key in node && key !== "list") node[key] = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function cookie(name) {
  return document.cookie.split("; ").find((part) => part.startsWith(name + "="))?.slice(name.length + 1);
}

async function api(path, { method = "GET", body, bearer } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (bearer) headers.Authorization = `Bearer ${bearer}`;
  if (method !== "GET") {
    const csrf = cookie("pi_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let response;
  try {
    response = await fetch(API + path, { method, headers, credentials: "same-origin", body: body === undefined ? undefined : JSON.stringify(body) });
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

function clearScreen() {
  timers.forEach(clearInterval);
  timers = [];
  cleanup.forEach((fn) => fn());
  cleanup = [];
  app.replaceChildren();
  topActions.replaceChildren();
}

function every(ms, fn) {
  fn();
  timers.push(setInterval(fn, ms));
}

function banner(kind, text) {
  return h("div", { class: `banner ${kind}`, role: kind === "error" ? "alert" : "status" }, text);
}

function form(fields, submitLabel, onSubmit) {
  const status = h("div");
  const button = h("button", { class: "primary", type: "submit" }, submitLabel);
  const node = h("form", {
    onsubmit: async (event) => {
      event.preventDefault();
      button.disabled = true;
      status.replaceChildren();
      try { await onSubmit(Object.fromEntries(new FormData(node))); }
      catch (error) { status.replaceChildren(banner("error", error.message)); }
      finally { button.disabled = false; }
    },
  }, fields, status, button);
  return node;
}

function field(label, name, attrs = {}) {
  return h("label", {}, label, h("input", { name, required: true, ...attrs }));
}

function closeModal() { modalRoot.replaceChildren(); }

function modal(title, ...content) {
  const dialog = h("section", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-label": title },
    h("div", { class: "row between" }, h("h2", {}, title), h("button", { type: "button", "aria-label": "Đóng", onclick: closeModal }, "×")), content);
  modalRoot.replaceChildren(h("div", { class: "overlay", onmousedown: (event) => { if (event.target === event.currentTarget) closeModal(); } }, dialog));
  dialog.querySelector("input, select, textarea, button.primary")?.focus();
}

function showTerms() {
  modal("Điều khoản sử dụng", h("div", { class: "terms" },
    h("p", {}, "Đây là mô hình nghiên cứu của đồ án Drone Zone Check, không phải hệ thống chính thức của cơ quan nhà nước."),
    h("ol", {},
      h("li", {}, "Kết quả duyệt bay trong hệ thống không thay thế giấy phép bay của cơ quan có thẩm quyền."),
      h("li", {}, "Bạn chịu trách nhiệm về thông tin đã khai và về việc giữ bí mật mật khẩu, mã OTP và khóa 2FA."),
      h("li", {}, "Hệ thống lưu tên tài khoản, email, nhật ký thao tác và thông tin đơn xin bay (họ tên, mã bằng lái, phương tiện, vị trí thiết bị)."),
      h("li", {}, "Drone chỉ được phép ARM khi đơn xin bay đã được duyệt và đang trong khung giờ bay."),
      h("li", {}, "Người điều khiển tự chịu trách nhiệm về an toàn bay và tuân thủ pháp luật về tàu bay không người lái."))));
}

function termsCheck() {
  return h("label", { class: "check" }, h("input", { type: "checkbox", name: "terms", required: true }),
    h("span", {}, "Tôi đã đọc và đồng ý với ", h("button", { class: "link", type: "button", onclick: showTerms }, "điều khoản sử dụng"), "."));
}

// ---- screen 1: upstream Wi-Fi

async function wifiScreen() {
  clearScreen();
  const list = h("ul", { class: "list" }, h("li", {}, "Đang quét Wi-Fi…"));
  const status = h("div");
  const connect = (network) => {
    modal(`Kết nối ${network.ssid}`, form(
      network.secure ? field("Mật khẩu Wi-Fi", "password", { type: "password", minLength: 8, maxLength: 63, autocomplete: "off" }) : h("p", { class: "muted" }, "Mạng này không có mật khẩu."),
      "Kết nối",
      async (data) => {
        const result = await api("/network/connect", { method: "POST", body: { ssid: network.ssid, password: data.password || null } });
        if (!result.ok) {
          throw new Error({ WRONG_PASSWORD: "Sai mật khẩu Wi-Fi.", NETWORK_NOT_FOUND: "Không còn thấy mạng này. Hãy quét lại.", INVALID_PASSWORD: "Mật khẩu Wi-Fi phải có 8–63 ký tự." }[result.error] ?? "Không kết nối được. Hãy thử lại.");
        }
        closeModal();
        await boot();
      }));
  };
  const scan = async () => {
    status.replaceChildren();
    list.replaceChildren(h("li", {}, "Đang quét Wi-Fi…"));
    try {
      const networks = await api("/network/scan");
      list.replaceChildren(...(networks.length ? networks.map((network) => h("li", {},
        h("div", {}, h("strong", {}, network.ssid), h("br"), h("small", {}, `Tín hiệu ${network.signal}%${network.secure ? " · có mật khẩu" : " · mạng mở"}`)),
        h("button", { class: "primary", type: "button", onclick: () => connect(network) }, "Kết nối"))) : [h("li", {}, "Không thấy mạng Wi-Fi nào. Kiểm tra USB Wi-Fi rồi quét lại.")]));
    } catch (error) { status.replaceChildren(banner("error", error.message)); list.replaceChildren(); }
  };
  app.append(h("section", { class: "card narrow" },
    h("p", { class: "eyebrow" }, "BƯỚC 1 · KẾT NỐI MẠNG"),
    h("h2", {}, "Kết nối Wi-Fi cho Pi"),
    h("p", { class: "muted" }, "Pi chưa có mạng ngoài. Chọn một mạng Wi-Fi để Pi gửi mã xác nhận qua email và liên lạc với máy chủ."),
    status, list,
    h("div", { class: "row", style: "margin-top:12px" }, h("button", { type: "button", onclick: scan }, "Quét lại"))));
  await scan();
}

// ---- screen 2: sign in / register

function authScreen(mode = "login", notice = null) {
  clearScreen();
  const card = h("section", { class: "card narrow" });
  app.append(card);
  const show = (title, help, ...content) => {
    card.replaceChildren(...h("div", {}, h("p", { class: "eyebrow" }, "BƯỚC 2 · XÁC THỰC"), h("h2", {}, title), help ? h("p", { class: "muted" }, help) : null, notice ? banner("ok", notice) : null, content).childNodes);
    card.querySelector("input")?.focus();
  };
  const codeField = (label) => field(label, "code", { inputMode: "numeric", pattern: "[0-9]{6}", maxLength: 6, autocomplete: "one-time-code" });

  const totpStep = (mfaChallengeId) => show("Mã 2FA", "Nhập mã 6 số hiện tại trong ứng dụng xác thực.",
    form(codeField("Mã 2FA"), "Đăng nhập", async (data) => {
      await api("/auth/login", { method: "POST", body: { mfa_challenge_id: mfaChallengeId, totp: data.code } });
      await boot();
    }));

  const otpStep = (challengeId) => {
    let current = challengeId;
    show("Mã OTP email", "Nhập mã 6 số vừa gửi tới email của tài khoản.",
      form(codeField("Mã OTP"), "Tiếp tục", async (data) => {
        const result = await api("/auth/login", { method: "POST", body: { challenge_id: current, otp: data.code } });
        totpStep(result.mfa_challenge_id);
      }),
      h("p", {}, h("button", { class: "link", type: "button", onclick: async (event) => {
        try { current = (await api("/auth/resend-login-otp", { method: "POST", body: { challenge_id: current } })).challenge_id; event.target.textContent = "Đã gửi lại mã"; }
        catch (error) { event.target.textContent = error.message; }
      } }, "Gửi lại mã")));
  };

  const emailSetup = (username, password) => show("Thêm email cho tài khoản", "Tài khoản này chưa có email. Nhập email để nhận mã OTP ở các lần đăng nhập sau.",
    form(field("Email", "email", { type: "email", autocomplete: "email" }), "Gửi mã xác nhận", async (data) => {
      const setup = await api("/auth/email/setup", { method: "POST", body: { username, password, email: data.email, terms_accepted: true } });
      show("Xác nhận email", `Nhập mã 6 số vừa gửi tới ${data.email}.`,
        form(codeField("Mã xác nhận"), "Xác nhận", async (verify) => {
          await api("/auth/email/verify", { method: "POST", body: { challenge_id: setup.challenge_id, code: verify.code } });
          authScreen("login", "Đã lưu email. Hãy đăng nhập lại.");
        }));
    }));

  const login = () => show("Đăng nhập", null,
    form([field("Tài khoản", "username", { autocomplete: "username" }), field("Mật khẩu", "password", { type: "password", autocomplete: "current-password" }), termsCheck()], "Tiếp tục", async (data) => {
      try {
        const result = await api("/auth/challenge", { method: "POST", body: { username: data.username, password: data.password, terms_accepted: true } });
        otpStep(result.challenge_id);
      } catch (error) {
        if (error.code === "EMAIL_SETUP_REQUIRED") emailSetup(data.username, data.password);
        else throw error.code === "AUTHENTICATION_FAILED" || error.status === 401 ? new Error("Sai tài khoản hoặc mật khẩu.") : error;
      }
    }),
    h("p", {}, h("button", { class: "link", type: "button", onclick: () => authScreen("register") }, "Tạo tài khoản mới")));

  const register = () => show("Đăng ký tài khoản", "Tài khoản mới có quyền người dùng: chỉ xem camera.",
    form([
      field("Tên tài khoản", "username", { autocomplete: "username", minLength: 3, maxLength: 64, pattern: "[A-Za-z0-9][A-Za-z0-9._\\-]{2,63}", title: "3–64 ký tự: chữ không dấu, số, dấu . _ -" }),
      field("Email", "email", { type: "email", autocomplete: "email" }),
      field("Mật khẩu (ít nhất 12 ký tự)", "password", { type: "password", minLength: 12, autocomplete: "new-password" }),
      field("Nhập lại mật khẩu", "password_confirm", { type: "password", minLength: 12, autocomplete: "new-password" }),
      termsCheck(),
    ], "Tạo tài khoản", async (data) => {
      if (data.password !== data.password_confirm) throw new Error("Mật khẩu nhập lại không khớp.");
      const created = await api("/auth/register", { method: "POST", body: { username: data.username, email: data.email, password: data.password, password_confirm: data.password_confirm, terms_accepted: true } });
      show("Xác nhận email", `Nhập mã 6 số vừa gửi tới ${data.email}.`,
        form(codeField("Mã xác nhận"), "Xác nhận", async (verify) => {
          const token = (await api("/auth/verify-email", { method: "POST", body: { challenge_id: created.challenge_id, code: verify.code } })).enrollment_token;
          const enrollment = await api("/auth/mfa/enroll", { method: "POST", bearer: token });
          show("Lưu khóa 2FA", "Thêm khóa này vào ứng dụng xác thực (Google Authenticator, Authy…). Khóa chỉ hiện một lần; mất khóa là không đăng nhập được.",
            h("code", { class: "secret" }, enrollment.secret),
            form([h("label", { class: "check" }, h("input", { type: "checkbox", required: true }), h("span", {}, "Tôi đã lưu khóa 2FA.")), codeField("Mã 2FA hiện tại")], "Hoàn tất đăng ký", async (confirm) => {
              await api("/auth/mfa/confirm", { method: "POST", bearer: token, body: { code: confirm.code } });
              authScreen("login", "Đăng ký xong. Hãy đăng nhập lại.");
            }));
        }));
    }),
    h("p", {}, h("button", { class: "link", type: "button", onclick: () => authScreen("login") }, "Đã có tài khoản? Đăng nhập")));

  (mode === "register" ? register : login)();
}

// ---- dashboard pieces

function cameraView() {
  const image = h("img", { class: "camera", alt: "Hình từ webcam USB của Pi", src: `${API}/camera/mjpeg` });
  const note = h("p", { class: "muted" });
  image.addEventListener("error", () => { note.textContent = "Chưa có hình từ webcam USB. Kiểm tra camera đã cắm vào Pi."; });
  cleanup.push(() => { image.src = ""; });
  return h("section", { class: "card" }, h("div", { class: "row between" }, h("h2", {}, "Camera"),
    h("button", { type: "button", onclick: () => { note.textContent = ""; image.src = `${API}/camera/mjpeg?t=${Date.now()}`; } }, "Tải lại")), image, note);
}

function mapView() {
  const element = h("div", { id: "map" });
  const info = h("p", { class: "muted" });
  const section = h("section", { class: "card" }, h("div", { class: "row between" }, h("h2", {}, "Bản đồ vùng cấm bay"),
    h("button", { type: "button", onclick: async (event) => {
      event.target.disabled = true;
      try { await api("/map/sync", { method: "POST" }); await loadZones(); } catch (error) { info.textContent = error.message; } finally { event.target.disabled = false; }
    } }, "Đồng bộ từ máy chủ")), element, info);
  let map; let zoneLayer; let marker; let centered = false;

  async function loadZones() {
    const cache = await api("/map/cache");
    zoneLayer.clearLayers();
    const items = cache.payload?.items ?? [];
    for (const zone of items) {
      const color = zone.classification === "RESTRICTED" ? "#f5a524" : "#d6495f";
      const layer = L.geoJSON(zone.geometry, { style: { color, fillColor: color, fillOpacity: .35, weight: 2 } }).addTo(zoneLayer);
      layer.bindPopup(h("div", {}, h("strong", {}, zone.name), h("br"), zone.classification === "RESTRICTED" ? "Vùng hạn chế bay" : "Vùng cấm bay"));
    }
    info.textContent = cache.state === "AVAILABLE" ? `${items.length} vùng · chỉ xem · lấy từ máy chủ lúc ${new Date(cache.provenance.fetched_at).toLocaleString("vi-VN")}` : "Chưa có dữ liệu vùng từ máy chủ. Bấm Đồng bộ khi Pi có mạng.";
    if (items.length && !centered) { map.fitBounds(zoneLayer.getBounds().pad(.3), { maxZoom: 14 }); centered = true; }
  }

  setTimeout(() => {
    map = L.map(element).setView([16.15, 106.25], 5);
    L.tileLayer(`${API}/tiles/{z}/{x}/{y}.png`, { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
    zoneLayer = L.featureGroup().addTo(map);
    cleanup.push(() => map.remove());
    loadZones().catch((error) => { info.textContent = error.message; });
    every(2000, async () => {
      try {
        const sample = await api("/telemetry");
        if (sample.fix_state === "FIX" && sample.latitude != null) {
          const position = [sample.latitude, sample.longitude];
          if (!marker) { marker = L.circleMarker(position, { radius: 8, color: "#086eae", fillColor: "#1689d5", fillOpacity: .95 }).addTo(map).bindPopup("Vị trí hiện tại của drone"); map.setView(position, 15); centered = true; }
          else marker.setLatLng(position);
        } else if (marker) { marker.remove(); marker = null; }
      } catch { /* shown on the telemetry tab */ }
    });
  });
  return section;
}

function droneModel(canvasHost) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 2, .1, 50);
  camera.position.set(0, 2.2, 4.2);
  camera.lookAt(0, 0, 0);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  canvasHost.append(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8aa4b8, 2.4));
  const drone = new THREE.Group();
  const dark = new THREE.MeshStandardMaterial({ color: 0x183650 });
  const blue = new THREE.MeshStandardMaterial({ color: 0x1689d5 });
  const red = new THREE.MeshStandardMaterial({ color: 0xbd3445 });
  drone.add(new THREE.Mesh(new THREE.BoxGeometry(.7, .18, .7), dark));
  for (const [x, z, front] of [[1, 1, false], [-1, 1, false], [1, -1, true], [-1, -1, true]]) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, .06, .1), front ? red : blue);
    arm.position.set(x * .55, 0, z * .55);
    arm.rotation.y = Math.atan2(-z, x);
    drone.add(arm);
    const rotor = new THREE.Mesh(new THREE.CylinderGeometry(.42, .42, .03, 28), new THREE.MeshStandardMaterial({ color: 0x64809a, transparent: true, opacity: .55 }));
    rotor.position.set(x * 1.05, .1, z * 1.05);
    drone.add(rotor);
  }
  scene.add(drone);
  scene.add(new THREE.GridHelper(6, 12, 0xbfd2df, 0xd5e4ef).translateY(-.9));
  const resize = () => { const width = canvasHost.clientWidth; const height = canvasHost.clientHeight; renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.render(scene, camera); };
  window.addEventListener("resize", resize);
  cleanup.push(() => { window.removeEventListener("resize", resize); renderer.dispose(); });
  setTimeout(resize);
  return (roll, pitch, yaw) => {
    const rad = Math.PI / 180;
    drone.rotation.set((pitch ?? 0) * rad, -(yaw ?? 0) * rad, -(roll ?? 0) * rad, "YXZ");
    renderer.render(scene, camera);
  };
}

function telemetryView() {
  const metrics = h("div", { class: "metrics" });
  const rc = h("div", { class: "rc" });
  const state = h("div");
  const host = h("div", { id: "drone3d", role: "img", "aria-label": "Mô hình 3D tư thế drone" });
  const pidRows = h("div");
  const tuningStatus = h("div");
  const altitude = h("input", { type: "number", min: 2, max: 500, step: 1, "aria-label": "Độ cao tối đa (m)" });
  let pidFilled = false;
  const number = (value, digits = 1, unit = "") => value == null ? "—" : `${Number(value).toFixed(digits)}${unit}`;
  const metric = (label, value) => h("div", { class: "metric" }, h("span", {}, label), h("strong", {}, value));
  const send = async (path, body) => {
    tuningStatus.replaceChildren();
    try { const result = await api(path, { method: "POST", body }); tuningStatus.replaceChildren(banner("ok", `Đã gửi tới ESP32: ${result.sent}`)); }
    catch (error) { tuningStatus.replaceChildren(banner("error", error.message)); }
  };
  const inputs = {};
  for (const [axis, label] of [["roll", "Roll"], ["pitch", "Pitch"], ["yaw", "Yaw"], ["angle", "Góc"]]) {
    inputs[axis] = ["kp", "ki", "kd"].map((gain) => h("input", { type: "number", step: "any", min: 0, max: gain === "kd" ? 5 : 50, placeholder: gain.toUpperCase(), "aria-label": `${label} ${gain.toUpperCase()}` }));
    pidRows.append(h("div", { class: "pid-grid" }, h("strong", {}, label), inputs[axis],
      h("button", { type: "button", onclick: () => send("/tuning/pid", { axis, kp: Number(inputs[axis][0].value), ki: Number(inputs[axis][1].value), kd: Number(inputs[axis][2].value) }) }, "Gửi")));
  }
  const section = h("div", {},
    h("section", { class: "card" }, h("h2", {}, "Thông số drone"), state, metrics),
    h("div", { class: "grid2", style: "margin-top:16px" },
      h("section", { class: "card" }, h("h3", {}, "Mô hình 3D"), host),
      h("section", { class: "card" }, h("h3", {}, "Tín hiệu tay điều khiển"), rc)),
    h("section", { class: "card", style: "margin-top:16px" }, h("h3", {}, "Tinh chỉnh thông số bay"),
      h("p", { class: "muted" }, "Chỉ gửi được khi drone không ARM. ESP32 tự lưu giá trị mới."), tuningStatus,
      h("div", { class: "pid-grid" }, h("strong", {}, "Độ cao tối đa"), altitude, h("span", {}, "mét"), h("span"),
        h("button", { type: "button", onclick: () => send("/tuning/max-altitude", { meters: Number(altitude.value) }) }, "Gửi")),
      h("h3", { style: "margin-top:16px" }, "PID"), pidRows));
  let pose;
  setTimeout(() => {
    try { pose = droneModel(host); } catch { host.textContent = "Trình duyệt không hỗ trợ hiển thị 3D."; }
    every(500, async () => {
      let sample;
      try { sample = await api("/telemetry"); } catch (error) { state.replaceChildren(banner("error", error.message)); return; }
      const device = sample.device ?? {};
      if (device.error) {
        state.replaceChildren(banner("info", { ESP_USB_NOT_CONFIGURED: "Chưa cấu hình cổng USB của ESP32.", ESP_USB_TIMEOUT: "Chưa nhận được dữ liệu từ ESP32. Kiểm tra cáp USB.", ESP_USB_READ_FAILED: "Không mở được cổng USB của ESP32.", ESP_FLASH_IN_PROGRESS: "Đang nạp firmware…" }[device.error] ?? `ESP32: ${device.error}`));
      } else {
        const flight = device.flight ?? {};
        state.replaceChildren(h("p", { class: "row" },
          h("span", { class: `chip ${flight.arm_state === "ARMED" ? "bad" : flight.arm_state === "DISARMED" ? "ok" : "warn"}` }, flight.arm_state === "ARMED" ? "ĐANG ARM" : flight.arm_state === "DISARMED" ? "Được phép ARM" : "Khóa ARM"),
          h("span", { class: "chip" }, `Mode ${flight.mode ?? "—"}`),
          flight.arm_block_reason && flight.arm_block_reason !== "READY" ? h("span", { class: "muted" }, `Lý do khóa: ${flight.arm_block_reason}`) : null));
      }
      const baro = device.barometer ?? {}; const power = device.power ?? {}; const flight = device.flight ?? {};
      metrics.replaceChildren(
        metric("Độ cao (baro)", number(baro.altitude_m, 1, " m")),
        metric("Roll", number(sample.roll_deg, 1, "°")),
        metric("Pitch", number(sample.pitch_deg, 1, "°")),
        metric("Yaw", number(sample.heading_deg, 1, "°")),
        metric("Pin", power.battery_pct == null ? "—" : `${Math.round(power.battery_pct)} %`),
        metric("Nhiệt độ", number(device.temperature_c, 1, " °C")),
        metric("Độ cao tối đa", number(flight.max_altitude_m, 0, " m")),
        metric("GPS", sample.fix_state === "FIX" ? `${sample.latitude.toFixed(5)}, ${sample.longitude.toFixed(5)}` : "Chưa có fix"));
      const channels = device.sbus?.channels ?? [];
      rc.replaceChildren(...(channels.length ? channels.map((value, index) => h("div", { class: "rc-row" }, `CH${index + 1}`, h("div", { class: "rc-bar" }, h("i", { style: `width:${Math.max(0, Math.min(100, value / 20.47))}%` })), String(value))) : [h("p", { class: "muted" }, device.sbus?.signal_ok === false ? "Mất tín hiệu tay điều khiển." : "Chưa có dữ liệu tay điều khiển.")]));
      if (!pidFilled && device.pid && Object.keys(device.pid).length) {
        for (const [axis, gains] of Object.entries(device.pid)) inputs[axis]?.forEach((input, index) => { input.value = gains[["kp", "ki", "kd"][index]] ?? ""; });
        if (flight.max_altitude_m != null) altitude.value = flight.max_altitude_m;
        pidFilled = true;
      }
      pose?.(sample.roll_deg, sample.pitch_deg, sample.heading_deg);
    });
  });
  return section;
}

function usersView() {
  const active = h("ul", { class: "list" });
  const requests = h("ul", { class: "list" });
  const all = h("ul", { class: "list" });
  const status = h("div");
  const decide = async (item, decision) => {
    try { await api(`/role-requests/${item.request_id}/decision`, { method: "POST", body: { decision } }); await load(); }
    catch (error) { status.replaceChildren(banner("error", error.message)); }
  };
  async function load() {
    try {
      const [activeUsers, roleRequests, users] = await Promise.all([api("/admin/active"), api("/role-requests"), api("/admin/users")]);
      active.replaceChildren(...activeUsers.map((user) => h("li", {}, h("div", {}, h("strong", {}, user.username), " ", h("span", { class: "chip" }, user.role === "ADMIN" ? "Admin" : "Người dùng")), h("small", {}, `Hoạt động lúc ${new Date(user.last_seen).toLocaleTimeString("vi-VN")}`))));
      const pending = roleRequests.filter((item) => item.status === "PENDING");
      requests.replaceChildren(...(pending.length ? pending.map((item) => h("li", {}, h("div", {}, h("strong", {}, item.requester ?? item.username ?? item.requester_id), h("br"), h("small", {}, item.reason)),
        h("div", { class: "row" }, h("button", { class: "primary", type: "button", onclick: () => decide(item, "APPROVED") }, "Cấp quyền admin"), h("button", { class: "danger", type: "button", onclick: () => decide(item, "REJECTED") }, "Từ chối")))) : [h("li", {}, "Không có yêu cầu nào đang chờ.")]));
      all.replaceChildren(...users.map((user) => h("li", {}, h("div", {}, h("strong", {}, user.username), h("br"), h("small", {}, user.email || "chưa có email")), h("span", { class: "chip" }, user.role === "ADMIN" ? "Admin" : "Người dùng"))));
    } catch (error) { status.replaceChildren(banner("error", error.message)); }
  }
  setTimeout(() => every(10000, load));
  return h("div", {}, status,
    h("section", { class: "card" }, h("h2", {}, "Đang hoạt động"), h("p", { class: "muted" }, "Tài khoản có thao tác trong 5 phút gần đây."), active),
    h("section", { class: "card" }, h("h2", {}, "Yêu cầu xin quyền admin"), requests),
    h("section", { class: "card" }, h("h2", {}, "Tất cả tài khoản"), all));
}

function firmwareView() {
  const body = h("div", {}, h("p", { class: "muted" }, "Đang kiểm tra bản phát hành…"));
  async function load() {
    try {
      const latest = await api("/firmware/latest");
      const status = h("div");
      const upToDate = latest.current_version === latest.version;
      body.replaceChildren(
        h("dl", { class: "kv" }, h("dt", {}, "Bản mới nhất"), h("dd", {}, latest.version), h("dt", {}, "Bản đã nạp từ Pi"), h("dd", {}, latest.current_version ?? "Chưa nạp lần nào"), h("dt", {}, "Dung lượng"), h("dd", {}, `${(latest.size / 1024).toFixed(0)} KB`), h("dt", {}, "SHA-256"), h("dd", {}, latest.sha256)),
        status,
        h("button", { class: "primary", type: "button", onclick: async (event) => {
          if (!window.confirm(`Nạp firmware ${latest.version} vào drone? Tháo cánh quạt và không tắt nguồn trong lúc nạp.`)) return;
          event.target.disabled = true;
          status.replaceChildren(banner("info", "Đang tải và nạp firmware, mất khoảng một phút…"));
          try {
            const job = await api("/firmware/flash", { method: "POST", body: { version: latest.version } });
            status.replaceChildren(job.state === "DONE" ? banner("ok", `Đã nạp firmware ${latest.version}.`) : banner("error", { SHA256_MISMATCH: "File tải về sai mã kiểm tra; không nạp.", DOWNLOAD_FAILED: "Không tải được firmware.", ESPTOOL_FAILED: "Nạp thất bại. Kiểm tra cáp USB rồi thử lại." }[job.detail] ?? "Nạp thất bại."));
            if (job.state === "DONE") await load();
          } catch (error) { status.replaceChildren(banner("error", error.message)); }
          finally { event.target.disabled = false; }
        } }, upToDate ? "Nạp lại bản này" : "Cập nhật firmware"));
    } catch (error) { body.replaceChildren(banner(error.code === "FIRMWARE_REPO_NOT_CONFIGURED" ? "info" : "error", error.message), h("button", { type: "button", onclick: load }, "Thử lại")); }
  }
  setTimeout(load);
  return h("section", { class: "card" }, h("h2", {}, "Cập nhật firmware"), h("p", { class: "muted" }, "Firmware lấy từ bản phát hành của nhà sản xuất, kiểm tra SHA-256 rồi nạp vào ESP32 qua USB. Chỉ nạp được khi drone không ARM."), body);
}

const FLIGHT_STATUS = {
  PENDING_SEND: ["Chờ gửi lên máy chủ", "warn"],
  PENDING: ["Chờ duyệt", "warn"],
  APPROVED: ["Đã được duyệt", "ok"],
  REJECTED: ["Bị từ chối", "bad"],
};

function flightModal(onChange) {
  api("/flight-options").then((options) => {
    const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    modal("Xin cấp phép bay", h("p", { class: "muted" }, "Đơn được mã hóa và gửi lên máy chủ kèm vị trí GPS hiện tại của drone. Drone chỉ ARM được khi đơn được duyệt và đang trong giờ bay."),
      form([
        field("Họ tên đầy đủ", "full_name", { maxLength: 160, autocomplete: "name" }),
        field("Mã bằng lái", "license_code", { maxLength: 80 }),
        field("Ngày bay", "flight_date", { type: "date", min: today, value: today }),
        field("Giờ bay", "flight_time", { type: "time" }),
        h("label", {}, "Phương tiện bay", h("select", { name: "vehicle", required: true }, options.vehicles.map((vehicle) => h("option", { value: vehicle }, vehicle)))),
      ], "Gửi đơn", async (data) => {
        await api("/flight-requests", { method: "POST", body: data });
        closeModal();
        onChange();
      }));
  }).catch((error) => modal("Xin cấp phép bay", banner("error", error.message)));
}

function roleRequestModal() {
  modal("Xin quyền admin", h("p", { class: "muted" }, "Yêu cầu sẽ chờ admin của Pi duyệt."),
    form(h("label", {}, "Lý do", h("textarea", { name: "reason", required: true, minLength: 3, maxLength: 500, rows: 3 })), "Gửi yêu cầu", async (data) => {
      try { await api("/role-requests", { method: "POST", body: { reason: data.reason } }); }
      catch (error) { throw error.status === 409 ? new Error("Bạn đã có yêu cầu đang chờ duyệt.") : error; }
      modal("Xin quyền admin", banner("ok", "Đã gửi yêu cầu. Hãy chờ admin cấp quyền, rồi đăng nhập lại."));
    }));
}

function dashboard() {
  clearScreen();
  const admin = me.role === "ADMIN";
  const logout = h("button", { type: "button", onclick: async () => { try { await api("/auth/logout", { method: "POST" }); } finally { me = null; authScreen("login"); } } }, `Đăng xuất (${me.username})`);
  if (!admin) {
    topActions.append(h("button", { class: "primary", type: "button", onclick: roleRequestModal }, "Xin quyền admin"), logout);
    app.append(cameraView());
    return;
  }
  const flightChip = h("span");
  const flightPanel = h("div");
  const refreshFlight = async () => {
    try {
      const items = await api("/flight-requests");
      const latest = items[0];
      if (!latest) { flightChip.replaceChildren(h("span", { class: "chip warn" }, "Chưa có phép bay")); flightPanel.replaceChildren(); return; }
      const [label, kind] = FLIGHT_STATUS[latest.status] ?? [latest.status, ""];
      const allowed = latest.arm_permission === "ALLOWED";
      flightChip.replaceChildren(h("span", { class: `chip ${allowed ? "ok" : kind}` }, allowed ? "Được phép bay" : label));
      flightPanel.replaceChildren(h("section", { class: "card", style: "margin-bottom:16px" }, h("div", { class: "row between" }, h("h3", {}, "Đơn xin bay gần nhất"), h("span", { class: `chip ${kind}` }, label)),
        h("dl", { class: "kv" }, h("dt", {}, "Người bay"), h("dd", {}, latest.full_name), h("dt", {}, "Ngày, giờ"), h("dd", {}, `${latest.flight_date} · ${latest.flight_time}`), h("dt", {}, "Phương tiện"), h("dd", {}, latest.vehicle), h("dt", {}, "Định vị gửi kèm"), h("dd", {}, latest.gps ? `${latest.gps.lat.toFixed(6)}, ${latest.gps.lon.toFixed(6)}` : "Không có định vị"),
          latest.reason ? [h("dt", {}, "Ghi chú duyệt"), h("dd", {}, latest.reason)] : null),
        h("p", { class: "muted" }, allowed ? "Drone được phép ARM trong khung giờ bay." : latest.status === "APPROVED" ? "Đơn đã duyệt nhưng chưa tới hoặc đã qua khung giờ bay: drone vẫn khóa ARM." : latest.status === "REJECTED" ? "Drone bị khóa ARM." : "Drone khóa ARM cho tới khi đơn được duyệt.")));
    } catch { /* keep the last known state */ }
  };
  topActions.append(flightChip, h("button", { class: "primary", type: "button", onclick: () => flightModal(refreshFlight) }, "Xin cấp phép bay"), logout);

  const views = { "Camera": cameraView, "Bản đồ": mapView, "Thông số": telemetryView, "Người dùng": usersView, "Firmware": firmwareView };
  const content = h("div");
  const tabs = h("div", { class: "tabs", role: "tablist" });
  const select = (name) => {
    timers.forEach(clearInterval); timers = [];
    cleanup.forEach((fn) => fn()); cleanup = [];
    for (const button of tabs.children) button.setAttribute("aria-selected", String(button.textContent === name));
    content.replaceChildren(views[name]());
    every(5000, refreshFlight);
  };
  for (const name of Object.keys(views)) tabs.append(h("button", { type: "button", role: "tab", onclick: () => select(name) }, name));
  app.append(flightPanel, tabs, content);
  select("Camera");
}

// ---- boot

async function boot() {
  closeModal();
  try {
    const network = await api("/network/status");
    if (!network.upstream_connected) { await wifiScreen(); return; }
  } catch { /* the Pi itself is unreachable; fall through to the sign-in error */ }
  try { me = await api("/auth/me"); } catch { me = null; }
  if (me) dashboard(); else authScreen("login");
}

boot();
