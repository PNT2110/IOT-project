// views/firmware.js - ESP32 firmware updates: local .bin OTA upload and release flashing
import { h, banner } from "../core/dom.js";
import { api } from "../core/api.js";

export function firmwareView() {
  const onlineSection = h("div", {}, h("div", { class: "skeleton" }));
  const uploadStatus = h("div");
  const fileInput = h("input", { type: "file", accept: ".bin", "aria-label": "Chọn tệp firmware .bin" });
  const uploadBtn = h("button", { class: "primary", type: "button" }, "Tải lên & Nạp firmware");

  uploadBtn.onclick = async () => {
    const file = fileInput.files?.[0];
    if (!file) {
      uploadStatus.replaceChildren(banner("error", "Vui lòng chọn tệp firmware (.bin) trước khi nạp."));
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      uploadStatus.replaceChildren(banner("error", "Kích thước tệp vượt quá giới hạn 4MB."));
      return;
    }
    if (!window.confirm(`Nạp tệp ${file.name} (${(file.size / 1024).toFixed(0)} KB) vào ESP32? Tháo cánh quạt và không tắt nguồn trong lúc nạp.`)) {
      return;
    }

    uploadBtn.disabled = true;
    uploadStatus.replaceChildren(banner("info", "Đang truyền tệp firmware và nạp vào ESP32, vui lòng đợi…"));

    try {
      const formData = new FormData();
      formData.append("file", file, file.name);
      const job = await api("/firmware/upload", { method: "POST", body: formData });
      if (job.status === "COMPLETED" || job.state === "DONE") {
        uploadStatus.replaceChildren(banner("ok", `Đã nạp thành công firmware ${file.name} (SHA-256: ${job.sha256 ? job.sha256.slice(0, 16) + '…' : 'xác thực'}).`));
        fileInput.value = "";
        await loadOnline();
      } else {
        uploadStatus.replaceChildren(banner("error", `Nạp firmware thất bại: ${job.detail || "lỗi không xác định"}.`));
      }
    } catch (error) {
      uploadStatus.replaceChildren(banner("error", error.message));
    } finally {
      uploadBtn.disabled = false;
    }
  };

  const uploadSection = h("div", { style: "margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.08)" },
    h("h3", { style: "margin-top:0" }, "Nạp tệp firmware (.bin) trực tiếp qua Wi-Fi"),
    h("p", { class: "muted" }, "Khi thực địa không có mạng Internet, chọn tệp firmware đã biên dịch sẵn (.bin) từ máy của bạn để nạp thẳng vào ESP32."),
    uploadStatus,
    h("div", { class: "row", style: "gap:12px; align-items:center; flex-wrap:wrap" },
      fileInput,
      uploadBtn));

  async function loadOnline() {
    try {
      const latest = await api("/firmware/latest");
      const status = h("div");
      const upToDate = latest.current_version === latest.version;
      onlineSection.replaceChildren(
        h("h3", {}, "Bản phát hành trực tuyến (GitHub)"),
        h("dl", { class: "kv" },
          h("dt", {}, "Bản mới nhất"), h("dd", {}, latest.version),
          h("dt", {}, "Bản đã nạp từ Pi"), h("dd", {}, latest.current_version ?? "Chưa nạp lần nào"),
          h("dt", {}, "Dung lượng"), h("dd", {}, `${(latest.size / 1024).toFixed(0)} KB`),
          h("dt", {}, "SHA-256"), h("dd", {}, latest.sha256)),
        status,
        h("button", {
          class: "primary",
          type: "button",
          onclick: async (event) => {
            if (!window.confirm(`Nạp firmware ${latest.version} vào drone? Tháo cánh quạt và không tắt nguồn trong lúc nạp.`)) return;
            event.target.disabled = true;
            status.replaceChildren(banner("info", "Đang tải và nạp firmware, mất khoảng một phút…"));
            try {
              const job = await api("/firmware/flash", { method: "POST", body: { version: latest.version } });
              status.replaceChildren(job.state === "DONE" || job.status === "COMPLETED"
                ? banner("ok", `Đã nạp firmware ${latest.version}.`)
                : banner("error", { SHA256_MISMATCH: "File tải về sai mã kiểm tra; không nạp.", DOWNLOAD_FAILED: "Không tải được firmware.", ESPTOOL_FAILED: "Nạp thất bại. Kiểm tra cáp USB rồi thử lại." }[job.detail] ?? "Nạp thất bại."));
              if (job.state === "DONE" || job.status === "COMPLETED") await loadOnline();
            } catch (error) {
              status.replaceChildren(banner("error", error.message));
            } finally {
              event.target.disabled = false;
            }
          },
        }, upToDate ? "Nạp lại bản này" : "Cập nhật firmware"));
    } catch (error) {
      onlineSection.replaceChildren(
        h("h3", {}, "Bản phát hành trực tuyến (GitHub)"),
        banner(error.code === "FIRMWARE_REPO_NOT_CONFIGURED" ? "info" : "error", error.message),
        h("button", { type: "button", onclick: loadOnline }, "Thử lại"));
    }
  }

  setTimeout(loadOnline);

  return h("section", { class: "card" },
    h("h2", {}, "Cập nhật firmware ESP32"),
    h("p", { class: "muted" }, "Nạp firmware điều khiển bay vào ESP32 qua kết nối USB. Hệ thống tự động kiểm tra mã SHA-256 và tạm dừng luồng serial telemetry trong khi nạp. Chỉ nạp được khi drone không ARM."),
    uploadSection,
    onlineSection);
}
