// views/wifi.js - Screen 1: upstream Wi-Fi setup and scan
import { h, banner, field, form, modal } from "../core/dom.js";
import { api, app, clearScreen } from "../core/api.js";

export async function wifiScreen(onBoot) {
  clearScreen();
  const main = app || document.getElementById("app");
  const list = h("ul", { class: "list" }, h("li", {}, "Đang quét Wi-Fi…"));
  const status = h("div");
  const connect = (network) => {
    modal(`Kết nối ${network.ssid}`, form(
      network.secure ? field("Mật khẩu Wi-Fi", "password", { type: "password", minLength: 8, maxLength: 63, autocomplete: "off" }) : h("p", { class: "muted" }, "Mạng này không có mật khẩu."),
      "Kết nối",
      async (data) => {
        const result = await api("/network/connect", { method: "POST", body: { ssid: network.ssid, password: data.password || null } });
        if (!result.ok) {
          throw new Error({ WRONG_PASSWORD: "Sai mật khẩu Wi-Fi.", NETWORK_NOT_FOUND: "Không còn thấy mạng này. Hãy quét lại.", INVALID_PASSWORD: "Mật khẩu Wi-Fi phải có 8–63 ký tự.", NOT_AUTHORIZED: "Pi chưa được cấp quyền đổi Wi-Fi. Cần chạy lại pi-setup.sh trên Pi một lần." }[result.error] ?? "Không kết nối được. Hãy thử lại.");
        }
        modal("Đang kết nối", h("p", {}, `Pi đang kết nối tới ${network.ssid}. Nếu máy bạn bị rớt khỏi Wi-Fi của Pi, hãy kết nối lại rồi mở lại trang này.`), h("div", { class: "skeleton" }));
        for (let attempt = 0; attempt < 15; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          try { if ((await api("/network/status")).upstream_connected) break; } catch { /* Pi Wi-Fi is restarting */ }
        }
        if (typeof onBoot === "function") {
          await onBoot();
        }
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
  if (main) {
    main.append(h("section", { class: "card auth" },
      h("p", { class: "eyebrow" }, "KẾT NỐI MẠNG"),
      h("h2", {}, "Kết nối Wi-Fi cho F450"),
      h("p", { class: "muted" }, "Pi chưa kết nối Wi-Fi. Chọn một mạng để Pi gửi mã xác nhận qua email và liên lạc với máy chủ."),
      status, list,
      h("div", { class: "row", style: "margin-top:12px" }, h("button", { type: "button", onclick: scan }, "Quét lại"))));
  }
  await scan();
}
