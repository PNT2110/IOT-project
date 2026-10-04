// views/flight.js - Flight permission request modals, pilot profile, and role requests
import { h, banner, field, form, modal, closeModal } from "../core/dom.js";
import { api, getMe, setMe } from "../core/api.js";

export const FLIGHT_STATUS = {
  PENDING_SEND: ["Chờ gửi lên máy chủ", "warn"],
  PENDING: ["Chờ duyệt", "warn"],
  APPROVED: ["Đã được duyệt", "ok"],
  REJECTED: ["Bị từ chối", "bad"],
};

export function flightModal(onChange) {
  Promise.all([api("/flight-options"), api("/profile").catch(() => ({}))]).then(([options, profile]) => {
    const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    modal("Xin cấp phép bay", h("p", { class: "muted" }, "Đơn được mã hóa và gửi lên máy chủ kèm vị trí GPS hiện tại của drone. Drone chỉ ARM được khi đơn được duyệt và đang trong khoảng giờ bay đã xin."),
      form([
        field("Họ tên đầy đủ", "full_name", { maxLength: 160, autocomplete: "name", value: profile.full_name ?? "" }),
        field("Mã bằng lái", "license_code", { maxLength: 80, value: profile.license_code ?? "" }),
        field("Ngày bay", "flight_date", { type: "date", min: today, value: today }),
        h("div", { class: "form-grid" }, field("Bay từ giờ", "flight_time", { type: "time" }), field("Đến giờ", "flight_end_time", { type: "time" })),
        h("label", {}, "Phương tiện bay", h("select", { name: "vehicle", required: true }, options.vehicles.map((vehicle) => h("option", { value: vehicle }, vehicle)))),
      ], "Gửi đơn", async (data) => {
        if (data.flight_end_time <= data.flight_time) throw new Error("Giờ kết thúc phải sau giờ bắt đầu.");
        await api("/flight-requests", { method: "POST", body: data });
        closeModal();
        if (typeof onChange === "function") onChange();
      }));
  }).catch((error) => modal("Xin cấp phép bay", banner("error", error.message)));
}

export async function profileModal() {
  let profile;
  try { profile = await api("/profile"); } catch (error) { modal("Thông tin cá nhân", banner("error", error.message)); return; }
  const otpStep = (challengeId, message) => modal("Xác nhận thay đổi", h("p", { class: "muted" }, message),
    form(field("Mã OTP email", "code", { inputMode: "numeric", pattern: "[0-9]{6}", maxLength: 6, autocomplete: "one-time-code" }), "Xác nhận", async (data) => {
      const result = await api("/profile/verify", { method: "POST", body: { challenge_id: challengeId, otp: data.code } });
      if (result.next_step === "NEW_EMAIL_OTP") { otpStep(challengeId, `Nhập mã vừa gửi tới email mới ${result.email_masked ?? ""}.`); return; }
      const me = getMe();
      if (result.profile?.username && me) {
        me.username = result.profile.username;
        setMe(me);
      }
      modal("Thông tin cá nhân", banner("ok", "Đã lưu thông tin cá nhân."));
    }));
  modal("Thông tin cá nhân", h("p", { class: "muted" }, "Họ tên và bằng lái dùng để điền sẵn đơn xin cấp phép bay. Thay đổi được xác nhận bằng mật khẩu hiện tại và mã OTP qua email."),
    form([
      h("div", { class: "form-grid" },
        field("Tên tài khoản", "username", { value: profile.username ?? "", minLength: 3, maxLength: 64, autocomplete: "username" }),
        field("Email", "email", { type: "email", value: profile.email ?? "", autocomplete: "email" }),
        field("Họ và tên", "full_name", { value: profile.full_name ?? "", maxLength: 200, required: false, autocomplete: "name" }),
        field("Mã bằng lái", "license_code", { value: profile.license_code ?? "", maxLength: 100, required: false }),
        h("label", {}, "Hạng giấy phép", h("select", { name: "license_class" },
          [["", "Chưa khai báo"], ["A", "Hạng A — bay trực quan"], ["B", "Hạng B — bay bằng thiết bị / ngoài tầm nhìn"]].map(([value, label]) => h("option", { value, selected: (profile.license_class ?? "") === value }, label)))),
        field("Ngày hết hạn bằng lái", "license_expiry", { type: "date", value: profile.license_expiry ?? "", required: false }),
        h("label", {}, h("span", {}, "Mật khẩu mới ", h("span", { class: "hint" }, "(để trống nếu không đổi)")), h("input", { name: "new_password", type: "password", minLength: 12, autocomplete: "new-password" })),
        field("Mật khẩu hiện tại", "current_password", { type: "password", autocomplete: "current-password" })),
    ], "Lưu và gửi mã OTP", async (data) => {
      if (data.license_code && !data.license_class) throw new Error("Chọn hạng giấy phép cho mã bằng lái.");
      const body = { current_password: data.current_password, username: data.username, email: data.email, full_name: data.full_name, license_code: data.license_code, license_class: data.license_class, license_expiry: data.license_expiry };
      if (data.new_password) body.new_password = data.new_password;
      const challenge = await api("/profile/challenge", { method: "POST", body });
      otpStep(challenge.challenge_id, "Nhập mã 6 số vừa gửi tới email của tài khoản.");
    }));
}

export function roleRequestModal() {
  modal("Xin quyền admin", h("p", { class: "muted" }, "Yêu cầu sẽ chờ admin của Pi duyệt."),
    form(h("label", {}, "Lý do", h("textarea", { name: "reason", required: true, minLength: 3, maxLength: 500, rows: 3 })), "Gửi yêu cầu", async (data) => {
      try { await api("/role-requests", { method: "POST", body: { reason: data.reason } }); }
      catch (error) { throw error.status === 409 ? new Error("Bạn đã có yêu cầu đang chờ duyệt.") : error; }
      modal("Xin quyền admin", banner("ok", "Đã gửi yêu cầu. Hãy chờ admin cấp quyền, rồi đăng nhập lại."));
    }));
}
