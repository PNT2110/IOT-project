import { FormEvent, useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import {
  confirmMfa,
  enrollMfa,
  getMe,
  getTermsVersion,
  login,
  register,
  resendLoginOtp,
  resendRegistrationOtp,
  verifyEmail,
  verifyLoginOtp,
  verifyRecovery,
  verifyTotp,
  type Me,
} from "../../api";

type AuthPanelProps = { onAuthenticated: (me: Me) => void; onClose: () => void; initialBootstrapChallengeId?: string };
type Mode = "login" | "register";
type Stage = "credentials" | "email" | "totp" | "recovery" | "enroll" | "complete";

export function AuthPanel({ onAuthenticated, onClose, initialBootstrapChallengeId }: AuthPanelProps) {
  const [mode, setMode] = useState<Mode>(initialBootstrapChallengeId ? "register" : "login");
  const [stage, setStage] = useState<Stage>(initialBootstrapChallengeId ? "email" : "credentials");
  const [ownerBootstrap, setOwnerBootstrap] = useState(Boolean(initialBootstrapChallengeId));
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [termsVersion, setTermsVersion] = useState("terms-v1");
  const [totpQr, setTotpQr] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [code, setCode] = useState("");
  const [terms, setTerms] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const [token, setToken] = useState("");
  const [challengeId, setChallengeId] = useState(initialBootstrapChallengeId ?? "");
  const [totpSecret, setTotpSecret] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [totpSaved, setTotpSaved] = useState(false);
  const [recoverySaved, setRecoverySaved] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const termsCloseButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (termsOpen) setTermsOpen(false);
      else onClose();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown);
    if (termsOpen) termsCloseButtonRef.current?.focus();
    else closeButtonRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose, termsOpen]);

  useEffect(() => { void getTermsVersion().then(setTermsVersion).catch(() => undefined); }, []);

  const showEnrollment = async (enrollmentToken: string) => {
    setToken(enrollmentToken);
    const enrollment = await enrollMfa(enrollmentToken);
    setTotpSecret(enrollment.secret);
    setTotpQr(await QRCode.toDataURL(enrollment.otpauth_uri, { margin: 1, width: 180 }).catch(() => ""));
    setTotpSaved(false);
    setMode("register");
    setStage("enroll");
    setCode("");
  };

  const reset = (nextMode: Mode) => {
    setMode(nextMode);
    setStage("credentials");
    setOwnerBootstrap(false);
    setEmail("");
    setUsername("");
    setTotpQr("");
    setPassword("");
    setPasswordConfirm("");
    setTerms(false);
    setCode("");
    setToken("");
    setChallengeId("");
    setTotpSecret("");
    setRecoveryCodes([]);
    setTotpSaved(false);
    setRecoverySaved(false);
    setNotice(null);
    setError(null);
  };

  const finish = async () => onAuthenticated(await getMe());

  const resendCode = async () => {
    if (busy || stage !== "email" || !challengeId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = mode === "register"
        ? await resendRegistrationOtp(challengeId)
        : await resendLoginOtp(token, challengeId);
      setChallengeId(result.challenge_id);
      setNotice("Đã gửi lại mã tới email của tài khoản.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể gửi lại mã OTP");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === "login" && stage === "credentials") {
        if (!terms) throw new Error("Bạn phải xác nhận đã đọc điều khoản.");
        const result = await login({ identifier: username, password, terms_accepted: terms, terms_version: termsVersion });
        setToken(result.login_token);
        setChallengeId(result.challenge_id ?? "");
        // The default main account has no mailbox, so the server skips email OTP.
        setStage(result.next_step === "TOTP" ? "totp" : "email");
      } else if (mode === "login" && stage === "email") {
        const result = await verifyLoginOtp(token, challengeId, code);
        if (result.next_step === "TOTP_ENROLLMENT" && result.enrollment_token) {
          // Registration was abandoned before the 2FA key was saved: show a new one.
          await showEnrollment(result.enrollment_token);
        } else {
          setToken(result.login_token ?? token);
          setStage("totp");
          setCode("");
        }
      } else if (mode === "login" && stage === "totp") {
        await verifyTotp(token, code);
        await finish();
      } else if (mode === "login" && stage === "recovery") {
        await verifyRecovery(token, code);
        await finish();
      } else if (mode === "register" && stage === "credentials") {
        if (!terms) throw new Error("Bạn phải xác nhận đã đọc điều khoản.");
        if (password !== passwordConfirm) throw new Error("Mật khẩu nhập lại không khớp.");
        const result = await register({ username: username.trim().toLowerCase(), email, password, password_confirm: passwordConfirm, terms_version: termsVersion });
        setChallengeId(result.challenge_id);
        setStage("email");
      } else if (mode === "register" && stage === "email") {
        const result = await verifyEmail(challengeId, code);
        await showEnrollment(result.enrollment_token);
      } else if (mode === "register" && stage === "enroll") {
        const result = await confirmMfa(token, code);
        setRecoveryCodes(result.recovery_codes ?? []);
        setRecoverySaved(false);
        // MFA enrollment is not a login. The API revokes the enrollment token
        // atomically and returns recovery codes without creating a session.
        setStage("complete");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể hoàn tất xác thực");
    } finally {
      setBusy(false);
    }
  };

  const factorTitle = mode === "register" ? stage === "email" ? "Xác nhận email" : "Thiết lập 2FA" : stage === "email" ? "Mã OTP email" : stage === "recovery" ? "Mã khôi phục" : "Mã 2FA";
  const factorHelp = mode === "register"
    ? stage === "email" ? ownerBootstrap ? "Nhập mã xác minh Owner trong email đã đăng ký ở bước bootstrap." : `Nhập mã xác nhận đã gửi tới ${email}.` : "Thêm khóa vào ứng dụng xác thực (Google Authenticator, Authy…), rồi nhập mã 6 số hiện tại."
    : stage === "email" ? "Nhập mã OTP đã gửi tới email của tài khoản." : stage === "recovery" ? "Nhập một mã khôi phục đã lưu trước đó. Mỗi mã chỉ dùng một lần." : "Nhập mã 2FA hiện tại từ ứng dụng xác thực.";

  return (
    <div className="modal-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-content auth-card" role="dialog" aria-modal="true" aria-label="Xác thực tài khoản">
        <div className="auth-heading">
          <div className="auth-brand"><img src="/logo-drone-zone-check.png" alt="" /><div><strong>DRONE ZONE CHECK</strong><small>Bản đồ vùng bay</small></div></div>
          <button ref={closeButtonRef} type="button" onClick={onClose} aria-label="Đóng">×</button>
        </div>
        <h2 className="auth-title">{stage === "credentials" ? mode === "login" ? "Đăng nhập" : "Đăng ký tài khoản" : factorTitle}</h2>
        {stage === "credentials" ? (
          <form className="auth-form" onSubmit={submit}>
            <label>{mode === "login" ? "Tài khoản" : "Tên tài khoản"}<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" minLength={3} maxLength={mode === "login" ? 320 : 32} pattern={mode === "register" ? "[A-Za-z0-9_.\\-]{3,32}" : undefined} title={mode === "register" ? "3–32 ký tự: chữ không dấu, số, dấu _ . -" : undefined} required /></label>
            {mode === "register" && <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>}
            <label>Mật khẩu{mode === "register" ? " (ít nhất 12 ký tự)" : ""}<input type="password" minLength={mode === "register" ? 12 : undefined} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} required /></label>
            {mode === "register" && <label>Nhập lại mật khẩu<input type="password" value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} autoComplete="new-password" required /></label>}
            <div className="terms-row"><input id="pc-terms-accepted" type="checkbox" checked={terms} onChange={(event) => setTerms(event.target.checked)} /><span className="terms-copy"><label htmlFor="pc-terms-accepted">Tôi đã đọc và đồng ý với </label><button className="terms-link" type="button" onClick={() => setTermsOpen(true)}>điều khoản sử dụng</button>.</span></div>
            <button className="primary-button" type="submit" disabled={busy || !terms}>{busy ? "Đang xử lý…" : mode === "login" ? "Tiếp tục" : "Tạo tài khoản"}</button>
          </form>
        ) : stage === "complete" ? (
          <div className="auth-form auth-complete">
            <div className="secret-warning"><strong>{ownerBootstrap ? "Thiết lập MFA cho Owner hoàn tất." : "Đăng ký MFA hoàn tất."}</strong><p>{ownerBootstrap ? "Lưu mã khôi phục. Tài khoản Owner vẫn đang PENDING; người vận hành cần khởi động lại PC server với -ActivateBootstrapOwner để kích hoạt." : "Tài khoản đang chờ tài khoản chính hoặc Admin cấp 1 duyệt."} Lưu các mã khôi phục này ở nơi an toàn; mỗi mã chỉ dùng một lần.</p><code>{recoveryCodes.join(" · ")}</code><label className="terms-row"><input type="checkbox" checked={recoverySaved} onChange={(event) => setRecoverySaved(event.target.checked)} /> Tôi đã lưu mã khôi phục an toàn.</label></div>
            <button className="primary-button" type="button" disabled={!recoverySaved} onClick={() => ownerBootstrap ? onClose() : reset("login")}>{ownerBootstrap ? "Hoàn tất" : "Đăng nhập lại"}</button>
          </div>
        ) : (
          <form className="auth-form" onSubmit={submit}>
            {mode === "register" && stage === "enroll" && <div className="secret-warning"><strong>Lưu khóa 2FA này trước khi tiếp tục:</strong>{totpQr && <img className="totp-qr" src={totpQr} alt="Mã QR để thêm khóa 2FA vào ứng dụng xác thực" width={180} height={180} />}<code>{totpSecret}</code><small>Khóa chỉ hiện một lần. Mất khóa là không đăng nhập được; không gửi khóa cho người khác.</small><label className="terms-row"><input type="checkbox" checked={totpSaved} onChange={(event) => setTotpSaved(event.target.checked)} /> Tôi đã lưu khóa 2FA an toàn.</label></div>}
            <p className="auth-help">{factorHelp}</p>
            <label>{stage === "enroll" ? "Mã 2FA" : stage === "recovery" ? "Mã khôi phục" : "Mã xác nhận"}<input inputMode={stage === "recovery" ? "text" : "numeric"} pattern={stage === "recovery" ? undefined : "[0-9]{6}"} value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" required /></label>
            <button className="primary-button" type="submit" disabled={busy || (mode === "register" && stage === "enroll" && !totpSaved)}>{busy ? "Đang xác thực…" : "Xác nhận"}</button>
            {stage === "email" && <button className="text-button" type="button" onClick={() => void resendCode()} disabled={busy}>Gửi lại mã OTP</button>}
            {mode === "login" && stage === "totp" && <button className="text-button" type="button" onClick={() => { setCode(""); setError(null); setStage("recovery"); }}>Dùng mã khôi phục</button>}
            {mode === "login" && stage === "recovery" && <button className="text-button" type="button" onClick={() => { setCode(""); setError(null); setStage("totp"); }}>Quay lại mã 2FA</button>}
          </form>
        )}
        {recoveryCodes.length > 0 && stage !== "complete" && <div className="secret-warning"><strong>Mã khôi phục — lưu offline:</strong><code>{recoveryCodes.join(" · ")}</code></div>}
        {error && <div className="error-banner">{error}</div>}
        {notice && <div className="success-banner">{notice}</div>}
        {stage === "credentials" && <div className="auth-switch">{mode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}<button type="button" onClick={() => reset(mode === "login" ? "register" : "login")}>{mode === "login" ? "Đăng ký" : "Đăng nhập"}</button></div>}
      </section>
      {termsOpen && <div className="terms-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setTermsOpen(false); }}><section className="terms-dialog" role="dialog" aria-modal="true" aria-labelledby="terms-dialog-title"><div className="auth-heading"><h2 id="terms-dialog-title">Điều khoản sử dụng</h2><button ref={termsCloseButtonRef} type="button" onClick={() => setTermsOpen(false)} aria-label="Đóng điều khoản">×</button></div><div className="terms-body"><p>Đây là mô hình nghiên cứu của đồ án Drone Zone Check, không phải cổng thông tin chính thức của cơ quan nhà nước.</p><ol><li>Dữ liệu vùng cấm bay, hạn chế bay trên bản đồ do cán bộ của hệ thống vẽ và chỉ có giá trị tham khảo. Kết quả duyệt bay trong hệ thống không thay thế giấy phép bay của cơ quan có thẩm quyền.</li><li>Bạn chịu trách nhiệm về thông tin đã khai và về việc giữ bí mật mật khẩu, mã OTP, khóa 2FA và mã khôi phục của mình.</li><li>Hệ thống lưu tên tài khoản, email, nhật ký thao tác và thông tin trong đơn xin bay (họ tên, mã bằng lái, phương tiện, vị trí thiết bị) để vận hành và kiểm tra.</li><li>Tài khoản mới chỉ dùng được sau khi được duyệt, và có thể bị khóa nếu sử dụng sai mục đích.</li><li>Người điều khiển tự chịu trách nhiệm về an toàn bay và phải tuân thủ quy định pháp luật hiện hành về tàu bay không người lái.</li></ol></div></section></div>}
    </div>
  );
}
