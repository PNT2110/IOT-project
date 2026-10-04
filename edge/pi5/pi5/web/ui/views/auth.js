// views/auth.js - Screen 2: Sign in, 2FA, register, email verification, terms
import { h, banner, field, form, modal } from "../core/dom.js";
import { api, app, clearScreen } from "../core/api.js";

export function showTerms() {
  modal("Điều khoản sử dụng", h("div", { class: "terms" },
    h("p", {}, "Đây là mô hình nghiên cứu của đồ án Drone Zone Check, không phải hệ thống chính thức của cơ quan nhà nước."),
    h("ol", {},
      h("li", {}, "Kết quả duyệt bay trong hệ thống không thay thế giấy phép bay của cơ quan có thẩm quyền."),
      h("li", {}, "Bạn chịu trách nhiệm về thông tin đã khai và về việc giữ bí mật mật khẩu, mã OTP và khóa 2FA."),
      h("li", {}, "Hệ thống lưu tên tài khoản, email, nhật ký thao tác và thông tin đơn xin bay (họ tên, mã bằng lái, phương tiện, vị trí thiết bị)."),
      h("li", {}, "Drone chỉ được phép ARM khi đơn xin bay đã được duyệt và đang trong khung giờ bay."),
      h("li", {}, "Người điều khiển tự chịu trách nhiệm về an toàn bay và tuân thủ pháp luật về tàu bay không người lái."))));
}

export function termsCheck() {
  return h("label", { class: "check" }, h("input", { type: "checkbox", name: "terms", required: true }),
    h("span", {}, "Tôi đã đọc và đồng ý với ", h("button", { class: "link", type: "button", onclick: showTerms }, "điều khoản sử dụng"), "."));
}

export function authScreen(mode = "login", notice = null, onBoot = null) {
  clearScreen();
  const main = app || document.getElementById("app");
  const card = h("section", { class: "card auth" });
  if (main) main.append(card);

  const show = (title, help, ...content) => {
    card.replaceChildren(...h("div", {},
      h("div", { class: "auth-brand" }, h("img", { src: "/assets/logo-drone-zone-check.png", alt: "" }), h("div", {}, h("strong", {}, "F450 PNT PVD"), h("small", {}, "Trạm Pi 5"))),
      h("h2", {}, title), help ? h("p", { class: "muted" }, help) : null, notice ? banner("ok", notice) : null, content).childNodes);
    card.querySelector("input")?.focus();
  };

  const codeField = (label) => field(label, "code", { inputMode: "numeric", pattern: "[0-9]{6}", maxLength: 6, autocomplete: "one-time-code" });

  const totpStep = (mfaChallengeId) => {
    show("Mã 2FA", "Nhập mã 6 số hiện tại trong ứng dụng xác thực.",
      form(codeField("Mã 2FA"), "Đăng nhập", async (data) => {
        await api("/auth/login", { method: "POST", body: { mfa_challenge_id: mfaChallengeId, totp: data.code } });
        if (typeof onBoot === "function") await onBoot();
      }));
  };

  const otpStep = (challengeId) => {
    let current = challengeId;
    show("Mã OTP email", "Nhập mã 6 số vừa gửi tới email của tài khoản.",
      form(codeField("Mã OTP"), "Tiếp tục", async (data) => {
        const result = await api("/auth/login", { method: "POST", body: { challenge_id: current, otp: data.code } });
        totpStep(result.mfa_challenge_id);
      }),
      h("p", { class: "resend" }, h("button", { class: "link", type: "button", onclick: async (event) => {
        try {
          current = (await api("/auth/resend-login-otp", { method: "POST", body: { challenge_id: current } })).challenge_id;
          event.target.textContent = "Đã gửi lại mã";
        } catch (error) {
          event.target.textContent = error.message;
        }
      } }, "Gửi lại mã")));
  };

  const emailSetup = (username, password) => show("Thêm email cho tài khoản", "Tài khoản này chưa có email. Nhập email để nhận mã OTP ở các lần đăng nhập sau.",
    form(field("Email", "email", { type: "email", autocomplete: "email" }), "Gửi mã xác nhận", async (data) => {
      const setup = await api("/auth/email/setup", { method: "POST", body: { username, password, email: data.email, terms_accepted: true } });
      show("Xác nhận email", `Nhập mã 6 số vừa gửi tới ${data.email}.`,
        form(codeField("Mã xác nhận"), "Xác nhận", async (verify) => {
          await api("/auth/email/verify", { method: "POST", body: { challenge_id: setup.challenge_id, code: verify.code } });
          authScreen("login", "Đã lưu email. Hãy đăng nhập lại.", onBoot);
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
    h("p", { class: "switch" }, "Chưa có tài khoản?", h("button", { class: "link", type: "button", onclick: () => authScreen("register", null, onBoot) }, "Đăng ký")));

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
              authScreen("login", "Đăng ký xong. Hãy đăng nhập lại.", onBoot);
            }));
        }));
    }),
    h("p", { class: "switch" }, "Đã có tài khoản?", h("button", { class: "link", type: "button", onclick: () => authScreen("login", null, onBoot) }, "Đăng nhập")));

  (mode === "register" ? register : login)();
}
