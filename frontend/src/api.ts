export type Envelope<T> = {
  schema_version: string;
  request_id: string;
  data: T | null;
  error: { code: string; message_for_user: string } | null;
  observed_at: string;
};

export type PolygonGeometry = { type: "Polygon"; coordinates: number[][][] };
export type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: number[][][][] };
export type ZoneGeometry = PolygonGeometry | MultiPolygonGeometry;

export type Zone = {
  id: string;
  name: string;
  geometry: ZoneGeometry;
  visibility: "PUBLIC" | "INTERNAL";
  classification: "NO_FLY" | "RESTRICTED" | "DEMO" | "INTERNAL_RESEARCH";
  version: number;
  retrieved_at: string;
  source_id?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

type ApiOptions = RequestInit & { bearer?: string | null; ifMatch?: number; idempotencyKey?: string };

function csrfToken(): string | undefined {
  return document.cookie.split("; ").find((part) => part.startsWith("csrf="))?.slice(5);
}

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (options.bearer) headers.set("Authorization", `Bearer ${options.bearer}`);
  if (options.ifMatch !== undefined) headers.set("If-Match", String(options.ifMatch));
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
  const method = (options.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD" && !options.bearer) {
    const csrf = csrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Không thể kết nối PC server. Hãy kiểm tra dịch vụ API và thử lại.");
  }

  let payload: Envelope<T>;
  try {
    payload = (await response.json()) as Envelope<T>;
  } catch {
    throw new Error(response.ok
      ? "PC server trả về dữ liệu không hợp lệ. Vui lòng thử lại sau."
      : "PC server chưa phản hồi dữ liệu hợp lệ. Hãy kiểm tra dịch vụ API rồi thử lại.");
  }
  if (!response.ok || payload.error) throw new Error(payload.error?.message_for_user ?? "Yêu cầu không thành công. Vui lòng thử lại sau.");
  return payload.data as T;
}

export async function getPublicZones(): Promise<Zone[]> {
  const data = await request<{ items: Zone[] }>("/api/v1/public/zones");
  return data.items ?? [];
}

export async function listInternalZones(): Promise<Zone[]> {
  const data = await request<{ items: Zone[] }>("/api/v1/internal/zones");
  return data.items ?? [];
}

export type ZoneSource = { id: string; publisher: string; source_type: string; license_name: string; checksum: string; retrieved_at: string };

export async function listZoneSources(): Promise<ZoneSource[]> {
  const data = await request<{ items: ZoneSource[] }>("/api/v1/internal/zone-sources");
  return data.items ?? [];
}

export async function createZone(body: { name: string; geometry: Zone["geometry"]; visibility: "PUBLIC" | "INTERNAL"; classification: string; source_id: string }, idempotencyKey = `ui-zone-${crypto.randomUUID()}`) {
  return request<{ id: string; version: number }>("/api/v1/internal/zones", { method: "POST", idempotencyKey, body: JSON.stringify(body) });
}

export async function updateZone(id: string, version: number, body: { name: string; geometry: Zone["geometry"]; visibility: "PUBLIC" | "INTERNAL"; classification: string; source_id: string }, idempotencyKey = `ui-zone-update-${crypto.randomUUID()}`) {
  return request<{ id: string; version: number }>(`/api/v1/internal/zones/${id}`, { method: "PATCH", ifMatch: version, idempotencyKey, body: JSON.stringify({ ...body, version }) });
}

export async function deleteZone(id: string, version: number, idempotencyKey = `ui-zone-delete-${crypto.randomUUID()}`) {
  return request<{ id: string; deleted: boolean; version: number }>(`/api/v1/internal/zones/${id}`, { method: "DELETE", ifMatch: version, idempotencyKey });
}

export type Me = {
  id: string;
  username?: string | null;
  display_name: string;
  email: string | null;
  full_name?: string;
  license_code?: string;
  license_class?: "A" | "B" | null;
  license_expiry?: string;
  status: string;
  role: string;
};
export type RegisterResult = { challenge_id: string; next_step: string; status: string };
export type OtpResendResult = { challenge_id: string; next_step: string; status?: string };
export type EnrollmentResult = { enrollment_token: string; next_step: string };
export type MfaEnrollment = { secret: string; otpauth_uri: string; warning: string };
export type MfaConfirmation = { status: string; role: string; recovery_codes: string[]; warning: string };
export type LoginResult = { login_token: string; challenge_id?: string; next_step: "EMAIL_OTP" | "TOTP" };
export type AuthenticatedResult = { access_token: string; role: string; status: string; next_step: string };

export function register(body: { username: string; email: string; password: string; password_confirm: string; terms_version: string }) {
  return request<RegisterResult>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) });
}

export function verifyEmail(token: string, code: string) {
  return request<EnrollmentResult>("/api/v1/auth/verify-email", { method: "POST", body: JSON.stringify({ challenge_id: token, code }) });
}

export function resendRegistrationOtp(challengeId: string) {
  return request<OtpResendResult>("/api/v1/auth/resend-registration-otp", { method: "POST", body: JSON.stringify({ challenge_id: challengeId }) });
}

export function enrollMfa(token: string) {
  return request<MfaEnrollment>("/api/v1/auth/mfa/enroll", { method: "POST", bearer: token });
}

export function confirmMfa(token: string, code: string) {
  return request<MfaConfirmation>("/api/v1/auth/mfa/confirm", { method: "POST", bearer: token, body: JSON.stringify({ code }) });
}

export function login(body: { identifier: string; password: string; terms_accepted: boolean; terms_version: string }) {
  return request<LoginResult>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(body) });
}

export function verifyLoginOtp(token: string, challengeId: string, code: string) {
  return request<{ login_token?: string; enrollment_token?: string; next_step: "TOTP" | "TOTP_ENROLLMENT" }>("/api/v1/auth/verify-login-otp", { method: "POST", bearer: token, body: JSON.stringify({ challenge_id: challengeId, code }) });
}

export function resendLoginOtp(token: string, challengeId: string) {
  return request<OtpResendResult>("/api/v1/auth/resend-login-otp", { method: "POST", bearer: token, body: JSON.stringify({ challenge_id: challengeId }) });
}

export function verifyTotp(token: string, code: string) {
  return request<AuthenticatedResult>("/api/v1/auth/verify-totp", { method: "POST", bearer: token, body: JSON.stringify({ code }) });
}

export function verifyRecovery(token: string, code: string) {
  return request<AuthenticatedResult>("/api/v1/auth/recovery", { method: "POST", bearer: token, body: JSON.stringify({ code }) });
}

export async function getTermsVersion(): Promise<string> {
  const data = await request<{ terms_version?: string }>("/api/v1/health");
  return data.terms_version ?? "terms-v1";
}

export function getMe() {
  return request<Me>("/api/v1/auth/me");
}

export type ProfileUpdateRequest = {
  current_password: string;
  display_name: string;
  email: string;
  full_name: string;
  new_password?: string;
  license_code?: string;
  license_class?: "A" | "B";
  license_expiry?: string;
};
export type ProfileChallenge = { challenge_id: string; next_step: "CURRENT_EMAIL_OTP" | "NEW_EMAIL_OTP"; email_masked?: string };

export function startProfileUpdate(body: ProfileUpdateRequest) {
  return request<ProfileChallenge>("/api/v1/auth/profile/update-challenge", { method: "POST", body: JSON.stringify(body) });
}

export function verifyProfileCurrentEmail(challengeId: string, code: string) {
  return request<ProfileChallenge | { updated: true; profile: Me }>("/api/v1/auth/profile/verify-current-email", { method: "POST", body: JSON.stringify({ challenge_id: challengeId, code }) });
}

export function verifyProfileNewEmail(challengeId: string, code: string) {
  return request<{ updated: true; profile: Me }>("/api/v1/auth/profile/verify-new-email", { method: "POST", body: JSON.stringify({ challenge_id: challengeId, code }) });
}

export function logout() {
  return request<{ logged_out: boolean }>("/api/v1/auth/logout", { method: "POST" });
}

export type StaffRole = "ADMIN" | "OPERATOR";
export type Account = { id: string; username?: string | null; display_name: string; email: string | null; status: string; role: string; version: number; email_verified: boolean; created_at: string; updated_at: string };
export type FlightDetails = { applicant_full_name?: string; license_code?: string; vehicle?: string; flight_date?: string; flight_time?: string; flight_end_time?: string | null; pi_username?: string; gps?: { lat?: number; lon?: number; fix_state?: string; satellites?: number | null } | null };
export type FlightRequest = { id: string; submitter_user_id: string | null; device_id: string | null; device_name: string | null; summary: string; scheduled_start_at: string; scheduled_end_at: string; status: string; version: number; source: string; request_details?: FlightDetails };

export function listAccounts() {
  return request<{ items: Account[] }>("/api/v1/account-review/users?page_size=100");
}

export function reviewAccount(id: string, version: number, status: "ACTIVE" | "REJECTED" | "SUSPENDED", reason: string, role?: StaffRole, idempotencyKey = `ui-account-status-${crypto.randomUUID()}`) {
  return request<{ account: Account }>(`/api/v1/account-review/users/${id}/status`, { method: "POST", ifMatch: version, idempotencyKey, body: JSON.stringify({ status, reason, role }) });
}

export function setAccountRole(id: string, role: StaffRole) {
  return request<{ account: Account }>(`/api/v1/account-review/users/${id}/role`, { method: "POST", body: JSON.stringify({ role }) });
}

export function listFlights() {
  return request<{ items: FlightRequest[] }>("/api/v1/flight-requests?page_size=100");
}

export function reviewFlight(id: string, version: number, reason: string, idempotencyKey = `ui-flight-review-${crypto.randomUUID()}`) {
  return request<FlightRequest>(`/api/v1/flight-requests/${id}/review`, { method: "POST", ifMatch: version, idempotencyKey, body: JSON.stringify({ reason }) });
}

export function decideFlight(id: string, version: number, decision: "REJECTED" | "APPROVED_SIMULATED", reason: string, idempotencyKey = `ui-flight-decision-${crypto.randomUUID()}`) {
  return request<FlightRequest>(`/api/v1/flight-requests/${id}/decision`, { method: "POST", ifMatch: version, idempotencyKey, body: JSON.stringify({ decision, reason }) });
}
