// views/telemetry.js - Telemetry metrics, 3D attitude model, RC channels, and tuning
import * as THREE from "/ui/vendor/three.module.min.js";
import { h, banner } from "../core/dom.js";
import { api, every, addCleanup } from "../core/api.js";

export function droneModel(canvasHost) {
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
  const resize = () => {
    const width = canvasHost.clientWidth;
    const height = canvasHost.clientHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  };
  window.addEventListener("resize", resize);
  addCleanup(() => {
    window.removeEventListener("resize", resize);
    renderer.dispose();
  });
  setTimeout(resize);
  return (roll, pitch, yaw) => {
    const rad = Math.PI / 180;
    drone.rotation.set((pitch ?? 0) * rad, -(yaw ?? 0) * rad, -(roll ?? 0) * rad, "YXZ");
    renderer.render(scene, camera);
  };
}

export function telemetryView() {
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
    try {
      const result = await api(path, { method: "POST", body });
      tuningStatus.replaceChildren(banner("ok", `Đã gửi tới ESP32: ${result.sent}`));
    } catch (error) {
      tuningStatus.replaceChildren(banner("error", error.message));
    }
  };
  const inputs = {};
  for (const [axis, label] of [["roll", "Roll"], ["pitch", "Pitch"], ["yaw", "Yaw"], ["angle", "Góc"]]) {
    inputs[axis] = ["kp", "ki", "kd"].map((gain) => h("input", { type: "number", step: "any", min: 0, max: gain === "kd" ? 5 : 50, placeholder: gain.toUpperCase(), "aria-label": `${label} ${gain.toUpperCase()}` }));
    pidRows.append(h("div", { class: "pid-grid" }, h("strong", {}, label), inputs[axis],
      h("button", { type: "button", onclick: () => send("/tuning/pid", { axis, kp: Number(inputs[axis][0].value), ki: Number(inputs[axis][1].value), kd: Number(inputs[axis][2].value) }) }, "Gửi")));
  }
  const section = h("div", { class: "view" },
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
