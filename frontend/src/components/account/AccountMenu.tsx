import { FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  getMe,
  startProfileUpdate,
  verifyProfileCurrentEmail,
  verifyProfileNewEmail,
  type Me,
  type ProfileUpdateRequest,
} from "../../api";
import { ErrorBanner } from "../common/ErrorBanner";

type AccountMenuProps = { user: Me; onLogout: () => void; onUpdated: (user: Me) => void };
type ProfileStage = "form" | "current-email" | "new-email";

export function AccountMenu({ user, onLogout, onUpdated }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (event.target instanceof Node && !menuRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <>
      <div className="account-menu-anchor" ref={menuRef}>
        <button className="account-trigger" type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          <span className="account-trigger-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="3.4" /><path d="M5.5 20c.6-3.5 2.7-5.4 6.5-5.4s5.9 1.9 6.5 5.4" /></svg>
          </span>
          <span className="account-trigger-copy"><strong>{user.display_name}</strong><small>{user.role}</small></span>
          <span className="account-chevron" aria-hidden="true">⌄</span>
        </button>
        {open && <div className="account-popover" role="menu" aria-label="Tài khoản">
          <div className="account-popover-heading"><span className="account-avatar">{user.display_name.slice(0, 1).toUpperCase()}</span><span><strong>{user.display_name}</strong><small>{user.email ?? user.username ?? ""}</small></span></div>
          <button role="menuitem" type="button" onClick={() => { setOpen(false); setProfileOpen(true); }}>Thông tin cá nhân</button>
          <button className="account-logout-item" role="menuitem" type="button" onClick={onLogout}>Đăng xuất</button>
        </div>}
      </div>
      {profileOpen && createPortal(<ProfileDialog user={user} onClose={() => setProfileOpen(false)} onUpdated={onUpdated} />, document.body)}
    </>
  );
}

function ProfileDialog({ user, onClose, onUpdated }: { user: Me; onClose: () => void; onUpdated: (user: Me) => void }) {
  const [stage, setStage] = useState<ProfileStage>("form");
  const [challengeId, setChallengeId] = useState("");
  const [otp, setOtp] = useState("");
  const [emailMasked, setEmailMasked] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    display_name: user.display_name,
    email: user.email ?? "",
    full_name: user.full_name ?? "",
    new_password: "",
    license_code: user.license_code ?? "",
    license_class: user.license_class ?? "",
    license_expiry: user.license_expiry ?? "",
    current_password: "",
  });
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [busy, onClose]);

  const setField = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const finish = async (profile: Me) => {
    onUpdated(profile);
    setNotice("Thông tin cá nhân đã được cập nhật.");
    setStage("form");
    window.setTimeout(onClose, 800);
  };

  const submitProfile = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const body: ProfileUpdateRequest = {
        current_password: form.current_password,
        display_name: form.display_name.trim(),
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        ...(form.new_password ? { new_password: form.new_password } : {}),
        ...(form.license_code ? { license_code: form.license_code.trim() } : {}),
        ...(form.license_class ? { license_class: form.license_class as "A" | "B" } : {}),
        ...(form.license_expiry ? { license_expiry: form.license_expiry } : {}),
      };
      const result = await startProfileUpdate(body);
      setChallengeId(result.challenge_id);
      setEmailMasked(result.email_masked ?? user.email ?? "");
      setStage("current-email");
      setNotice(`Đã gửi mã xác nhận tới ${result.email_masked ?? user.email ?? ""}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể bắt đầu cập nhật hồ sơ.");
    } finally { setBusy(false); }
  };

  const submitOtp = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !challengeId) return;
    setBusy(true); setError(""); setNotice("");
    try {
      if (stage === "current-email") {
        const result = await verifyProfileCurrentEmail(challengeId, otp);
        if ("updated" in result && result.updated) await finish(result.profile);
        else if ("next_step" in result) {
          setStage("new-email");
          setOtp("");
          setEmailMasked(result.email_masked ?? form.email);
          setNotice(`Đã xác nhận email cũ. Nhập mã vừa gửi tới ${result.email_masked ?? form.email}.`);
        } else throw new Error("PC server trả về trạng thái xác nhận hồ sơ không hợp lệ.");
      } else if (stage === "new-email") {
        const result = await verifyProfileNewEmail(challengeId, otp);
        await finish(result.profile);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Mã OTP không hợp lệ hoặc đã hết hạn.");
    } finally { setBusy(false); }
  };

  return (
    <div className="profile-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section className="profile-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-title">
        <header className="profile-dialog-header">
          <div><p className="eyebrow">TÀI KHOẢN / BẢO MẬT</p><h2 id="profile-title">Thông tin cá nhân</h2><p>Thay đổi hồ sơ được xác nhận bằng mật khẩu hiện tại và OTP email.</p></div>
          <button ref={closeRef} className="icon-button" type="button" aria-label="Đóng" onClick={onClose}>×</button>
        </header>
        {stage === "form" ? <form className="profile-form" onSubmit={submitProfile}>
          <div className="profile-fields">
            <label>Tên người dùng<input value={form.display_name} maxLength={80} autoComplete="username" onChange={(event) => setField("display_name", event.target.value)} required /></label>
            <label>Email<input type="email" value={form.email} autoComplete="email" onChange={(event) => setField("email", event.target.value)} required /></label>
            <label>Mật khẩu mới <span className="field-hint">(để trống nếu không đổi)</span><input type="password" value={form.new_password} minLength={12} autoComplete="new-password" onChange={(event) => setField("new_password", event.target.value)} /></label>
            <label className="profile-password-field">Mật khẩu hiện tại<input type="password" value={form.current_password} autoComplete="current-password" onChange={(event) => setField("current_password", event.target.value)} required /></label>
          </div>
          <div className="profile-dialog-actions"><button className="primary-button" type="submit" disabled={busy}>{busy ? "Đang gửi mã…" : "Lưu và gửi mã OTP"}</button><button className="ghost-button" type="button" onClick={onClose} disabled={busy}>Hủy</button></div>
        </form> : <form className="profile-otp-form" onSubmit={submitOtp}>
          <div className="otp-step-indicator"><span className="step-done">1</span><i /><span className={stage === "new-email" ? "step-done" : "step-current"}>2</span></div>
          <p>{stage === "current-email" ? <>Nhập mã OTP gửi tới <strong>{emailMasked}</strong> để xác nhận yêu cầu.</> : <>Nhập mã OTP gửi tới email mới <strong>{emailMasked}</strong>.</>}</p>
          <label>Mã OTP email<input value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" autoFocus required /></label>
          <div className="profile-dialog-actions"><button className="primary-button" type="submit" disabled={busy || otp.length !== 6}>{busy ? "Đang xác nhận…" : "Xác nhận thay đổi"}</button><button className="ghost-button" type="button" onClick={onClose} disabled={busy}>Hủy</button></div>
        </form>}
        <ErrorBanner message={error || null} onDismiss={() => setError("")} />
        {notice && <div className="success-banner" role="status">{notice}</div>}
      </section>
    </div>
  );
}
