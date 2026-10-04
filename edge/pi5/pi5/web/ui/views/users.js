// views/users.js - Active users, role elevation requests, and user directory
import { h, banner } from "../core/dom.js";
import { api, every } from "../core/api.js";

export function usersView() {
  const active = h("ul", { class: "list" }, h("li", { class: "skeleton" }));
  const requests = h("ul", { class: "list" }, h("li", { class: "skeleton" }));
  const all = h("ul", { class: "list" }, h("li", { class: "skeleton" }));
  const status = h("div");
  const decide = async (item, decision) => {
    try {
      await api(`/role-requests/${item.request_id}/decision`, { method: "POST", body: { decision } });
      await load();
    } catch (error) {
      status.replaceChildren(banner("error", error.message));
    }
  };
  async function load() {
    try {
      const [activeUsers, roleRequests, users] = await Promise.all([api("/admin/active"), api("/role-requests"), api("/admin/users")]);
      active.replaceChildren(...activeUsers.map((user) => h("li", {}, h("div", {}, h("strong", {}, user.username), " ", h("span", { class: "chip" }, user.role === "ADMIN" ? "Admin" : "Người dùng")), h("small", {}, `Hoạt động lúc ${new Date(user.last_seen).toLocaleTimeString("vi-VN")}`))));
      const pending = roleRequests.filter((item) => item.status === "PENDING");
      requests.replaceChildren(...(pending.length ? pending.map((item) => h("li", {}, h("div", {}, h("strong", {}, item.requester ?? item.username ?? item.requester_id), h("br"), h("small", {}, item.reason)),
        h("div", { class: "row" }, h("button", { class: "primary", type: "button", onclick: () => decide(item, "APPROVED") }, "Cấp quyền admin"), h("button", { class: "danger", type: "button", onclick: () => decide(item, "REJECTED") }, "Từ chối")))) : [h("li", {}, "Không có yêu cầu nào đang chờ.")]));
      all.replaceChildren(...users.map((user) => h("li", {}, h("div", {}, h("strong", {}, user.username), h("br"), h("small", {}, user.email || "chưa có email")), h("span", { class: "chip" }, user.role === "ADMIN" ? "Admin" : "Người dùng"))));
    } catch (error) {
      status.replaceChildren(banner("error", error.message));
    }
  }
  setTimeout(() => every(10000, load));
  return h("div", { class: "view" }, status,
    h("section", { class: "card" }, h("h2", {}, "Đang hoạt động"), h("p", { class: "muted" }, "Tài khoản có thao tác trong 5 phút gần đây."), active),
    h("section", { class: "card" }, h("h2", {}, "Yêu cầu xin quyền admin"), requests),
    h("section", { class: "card" }, h("h2", {}, "Tất cả tài khoản"), all));
}
