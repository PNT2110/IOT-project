// views/camera.js - USB webcam stream with bandwidth-saving pause/resume control
import { h } from "../core/dom.js";
import { API, addCleanup } from "../core/api.js";

export function cameraView() {
  let streaming = true;
  const image = h("img", { class: "camera", alt: "Hình từ webcam USB của Pi", src: `${API}/camera/mjpeg` });
  const note = h("p", { class: "muted" });
  const live = h("span", { class: "chip live" }, "TRỰC TIẾP");

  image.addEventListener("error", () => {
    if (streaming) {
      note.textContent = "Chưa có hình từ webcam USB. Kiểm tra camera đã cắm vào Pi.";
      live.hidden = true;
    }
  });

  image.addEventListener("load", () => {
    if (streaming) {
      live.hidden = false;
    }
  });

  addCleanup(() => {
    streaming = false;
    image.src = "";
  });

  const toggleBtn = h("button", {
    type: "button",
    onclick: () => {
      streaming = !streaming;
      if (streaming) {
        note.textContent = "";
        image.src = `${API}/camera/mjpeg?t=${Date.now()}`;
        toggleBtn.textContent = "Tạm dừng";
        live.textContent = "TRỰC TIẾP";
        live.className = "chip live";
        live.hidden = false;
      } else {
        image.src = "";
        toggleBtn.textContent = "Tiếp tục";
        live.textContent = "TẠM DỪNG";
        live.className = "chip warn";
        live.hidden = false;
        note.textContent = "Luồng video đã tạm dừng để tiết kiệm băng thông.";
      }
    },
  }, "Tạm dừng");

  const reloadBtn = h("button", {
    type: "button",
    onclick: () => {
      note.textContent = "";
      streaming = true;
      toggleBtn.textContent = "Tạm dừng";
      live.textContent = "TRỰC TIẾP";
      live.className = "chip live";
      live.hidden = false;
      image.src = `${API}/camera/mjpeg?t=${Date.now()}`;
    },
  }, "Tải lại");

  return h("section", { class: "card" },
    h("div", { class: "row between", style: "margin-bottom:12px" },
      h("h2", { style: "margin:0" }, "Camera"),
      h("div", { class: "row", style: "gap:8px" }, toggleBtn, reloadBtn)),
    h("div", { class: "camera-frame" }, image, live),
    note);
}
