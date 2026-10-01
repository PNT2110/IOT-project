import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  createZone,
  decideFlight,
  deleteZone,
  listAccounts,
  listFlights,
  listInternalZones,
  listZoneSources,
  reviewAccount,
  reviewFlight,
  setAccountRole,
  updateZone,
  type Account,
  type FlightRequest,
  type Me,
  type StaffRole,
  type Zone,
  type ZoneSource,
} from "../../api";
import { MapPanel } from "../map/MapPanel";

type OperationsWorkspaceProps = { user: Me; onPublicZonesChanged?: () => Promise<void> };
type Tab = "zones" | "flights" | "accounts";

const ROLE_LABEL: Record<string, string> = { OWNER: "Tài khoản chính", ADMIN: "Cấp 1 · Admin", OPERATOR: "Cấp 2 · Cán bộ", GUEST: "Chưa phân cấp" };
const ACCOUNT_STATUS_LABEL: Record<string, string> = { PENDING: "Chờ duyệt", ACTIVE: "Đang hoạt động", SUSPENDED: "Đang khóa", REJECTED: "Đã từ chối" };

function flightStatusLabel(status: string): string {
  switch (status) {
    case "APPROVED_SIMULATED": return "Đã duyệt";
    case "REJECTED": return "Đã từ chối";
    case "NEEDS_INFORMATION": return "Cần bổ sung thông tin";
    case "UNDER_REVIEW": return "Đang xem xét";
    case "SUBMITTED": return "Chờ duyệt";
    default: return status;
  }
}

function GpsMap({ lat, lon }: { lat: number; lon: number }) {
  const element = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!element.current) return;
    const map = L.map(element.current, { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false }).setView([lat, lon], 14);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);
    L.circleMarker([lat, lon], { radius: 8, color: "#086eae", fillColor: "#1689d5", fillOpacity: 0.9 }).addTo(map);
    return () => { map.remove(); };
  }, [lat, lon]);
  return <div ref={element} className="gps-map" role="img" aria-label={`Vị trí thiết bị ${lat.toFixed(5)}, ${lon.toFixed(5)}`} />;
}

export function OperationsWorkspace({ user, onPublicZonesChanged }: OperationsWorkspaceProps) {
  const canReviewAccounts = user.role === "OWNER" || user.role === "ADMIN";
  const [tab, setTab] = useState<Tab>("zones");
  const [zones, setZones] = useState<Zone[]>([]);
  const [sources, setSources] = useState<ZoneSource[]>([]);
  const [flights, setFlights] = useState<FlightRequest[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [mapResetKey, setMapResetKey] = useState(0);
  const [name, setName] = useState("");
  const [visibility, setVisibility] = useState<"PUBLIC" | "INTERNAL">("PUBLIC");
  const [classification, setClassification] = useState("NO_FLY");
  const [geometry, setGeometry] = useState<Zone["geometry"] | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [approveRoles, setApproveRoles] = useState<Record<string, StaffRole>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const busyRef = useRef(false);

  const sourceId = selectedZone?.source_id || sources.find((source) => source.source_type === "OPERATOR_DRAWN")?.id || sources[0]?.id || "";

  const run = async (action: string, work: () => Promise<void>, failure: string) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusyAction(action);
    setError(null);
    setMessage(null);
    try { await work(); } catch (cause) { setError(cause instanceof Error ? cause.message : failure); } finally {
      busyRef.current = false;
      setBusyAction(null);
    }
  };

  const refresh = async () => {
    const [zoneItems, sourceItems, flightData] = await Promise.all([listInternalZones(), listZoneSources(), listFlights()]);
    setZones(zoneItems);
    setSources(sourceItems);
    setFlights(flightData.items ?? []);
    setAccounts(canReviewAccounts ? (await listAccounts()).items ?? [] : []);
  };

  useEffect(() => { void refresh().catch((cause) => setError(cause instanceof Error ? cause.message : "Không tải được dữ liệu")); }, [user.id]);

  const beginZoneEdit = (zone: Zone | null) => {
    setMapResetKey((key) => key + 1);
    setSelectedZone(zone);
    setName(zone?.name ?? "");
    setVisibility(zone?.visibility ?? "PUBLIC");
    setClassification(zone?.classification === "RESTRICTED" ? "RESTRICTED" : "NO_FLY");
    setGeometry(zone?.geometry ?? null);
    setMessage(null);
  };

  const saveZone = () => run("zone-save", async () => {
    if (!geometry) throw new Error("Hãy vẽ vùng trên bản đồ trước khi lưu.");
    if (!sourceId) throw new Error("Server chưa có nguồn dữ liệu vùng. Hãy chạy lại bước khởi tạo tài khoản chính.");
    const body = { name: name.trim(), classification, visibility, geometry, source_id: sourceId };
    if (selectedZone) await updateZone(selectedZone.id, selectedZone.version, body);
    else await createZone(body);
    beginZoneEdit(null);
    setMessage("Đã lưu vùng.");
    await refresh();
    await onPublicZonesChanged?.();
  }, "Không lưu được vùng");

  const removeZone = () => run("zone-delete", async () => {
    if (!selectedZone) return;
    if (!window.confirm(`Xóa vùng "${selectedZone.name}"?`)) return;
    await deleteZone(selectedZone.id, selectedZone.version);
    beginZoneEdit(null);
    setMessage("Đã xóa vùng.");
    await refresh();
    await onPublicZonesChanged?.();
  }, "Không xóa được vùng");

  const decide = (flight: FlightRequest, decision: "APPROVED_SIMULATED" | "REJECTED") => run(`flight-${flight.id}`, async () => {
    const reason = (reasons[flight.id] ?? "").trim() || (decision === "REJECTED" ? "" : "Đủ điều kiện bay");
    if (reason.length < 3) throw new Error("Hãy nhập lý do từ chối (ít nhất 3 ký tự).");
    let version = flight.version;
    // Requests filed on the PC web still pass through the explicit review step.
    if (!flight.device_id && flight.status === "SUBMITTED") version = (await reviewFlight(flight.id, version, "Bắt đầu xem xét")).version;
    await decideFlight(flight.id, version, decision, reason);
    setMessage(decision === "REJECTED" ? "Đã từ chối yêu cầu bay." : "Đã duyệt yêu cầu bay.");
    await refresh();
  }, "Không cập nhật được yêu cầu bay");

  const changeStatus = (account: Account, status: "ACTIVE" | "REJECTED" | "SUSPENDED", reason: string) => run(`account-${account.id}`, async () => {
    const role = account.status === "PENDING" && status === "ACTIVE" ? approveRoles[account.id] ?? "OPERATOR" : undefined;
    await reviewAccount(account.id, account.version, status, reason, role);
    setMessage("Đã cập nhật tài khoản.");
    await refresh();
  }, "Không cập nhật được tài khoản");

  const changeRole = (account: Account, role: StaffRole) => run(`account-${account.id}`, async () => {
    await setAccountRole(account.id, role);
    setMessage("Đã đổi cấp tài khoản.");
    await refresh();
  }, "Không đổi được cấp tài khoản");

  const pendingFlights = flights.filter((flight) => flight.status === "SUBMITTED" || flight.status === "UNDER_REVIEW");
  const decidedFlights = flights.filter((flight) => flight.status === "APPROVED_SIMULATED" || flight.status === "REJECTED");
  const pendingAccounts = accounts.filter((account) => account.status === "PENDING");
  const otherAccounts = accounts.filter((account) => account.status !== "PENDING");
  const busy = busyAction !== null;

  const flightCard = (flight: FlightRequest, actionable: boolean) => {
    const details = flight.request_details ?? {};
    const gps = details.gps && typeof details.gps.lat === "number" && typeof details.gps.lon === "number" ? { lat: details.gps.lat, lon: details.gps.lon } : null;
    const when = details.flight_date ? `${details.flight_date} · ${details.flight_time ?? ""}` : new Date(flight.scheduled_start_at).toLocaleString("vi-VN");
    return <article className="flight-card" key={flight.id}>
      <div className="flight-card-body">
        <div className="flight-card-title"><strong>{details.applicant_full_name ?? flight.summary}</strong><span className={`status-chip status-${flight.status.toLowerCase()}`}>{flightStatusLabel(flight.status)}</span></div>
        <dl className="detail-list">
          <div><dt>Mã bằng lái</dt><dd>{details.license_code ?? "—"}</dd></div>
          <div><dt>Ngày, giờ bay</dt><dd>{when}</dd></div>
          <div><dt>Phương tiện</dt><dd>{details.vehicle ?? "—"}</dd></div>
          <div><dt>Thiết bị gửi</dt><dd>{flight.device_name ?? "Web PC"}{details.pi_username ? ` · ${details.pi_username}` : ""}</dd></div>
          <div><dt>Định vị</dt><dd>{gps ? `${gps.lat.toFixed(6)}, ${gps.lon.toFixed(6)}${details.gps?.satellites != null ? ` · ${details.gps.satellites} vệ tinh` : ""}` : "Không có định vị"}</dd></div>
        </dl>
        {actionable && <>
          <label>Lý do (bắt buộc khi từ chối)<textarea rows={2} maxLength={500} value={reasons[flight.id] ?? ""} onChange={(event) => setReasons((current) => ({ ...current, [flight.id]: event.target.value }))} disabled={busy} /></label>
          <div className="inline-actions"><button className="primary-button" type="button" onClick={() => void decide(flight, "APPROVED_SIMULATED")} disabled={busy}>Duyệt</button><button className="danger-button" type="button" onClick={() => void decide(flight, "REJECTED")} disabled={busy}>Từ chối</button></div>
        </>}
      </div>
      {gps ? <GpsMap lat={gps.lat} lon={gps.lon} /> : <div className="gps-map gps-map-empty">Không có định vị</div>}
    </article>;
  };

  return (
    <section className="workspace-section" aria-label="Không gian điều hành" aria-busy={busy}>
      <div className="workspace-header"><div><p className="eyebrow">KHÔNG GIAN ĐIỀU HÀNH <span>·</span> {ROLE_LABEL[user.role] ?? user.role}</p><h2>Quản lý vùng bay</h2><p className="workspace-subtitle">Vùng cấm bay, yêu cầu cấp phép bay và tài khoản cán bộ.</p></div><span className="workspace-identity"><i aria-hidden="true" /> {user.username ?? user.display_name}</span></div>
      <nav className="workspace-tabs" aria-label="Các tab">
        <button className={tab === "zones" ? "active" : ""} type="button" onClick={() => setTab("zones")}>Bản đồ & vùng cấm bay</button>
        <button className={tab === "flights" ? "active" : ""} type="button" onClick={() => setTab("flights")}>Duyệt xin phép bay{pendingFlights.length > 0 ? ` (${pendingFlights.length})` : ""}</button>
        {canReviewAccounts && <button className={tab === "accounts" ? "active" : ""} type="button" onClick={() => setTab("accounts")}>Duyệt tài khoản{pendingAccounts.length > 0 ? ` (${pendingAccounts.length})` : ""}</button>}
      </nav>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {message && <div className="success-banner" role="status">{message}</div>}

      {tab === "zones" && <div className="workspace-grid">
        <div><MapPanel zones={zones} editable resetKey={mapResetKey} selectedZoneId={selectedZone?.id ?? null} onZoneSelect={beginZoneEdit} onDraftInvalidated={() => setGeometry(selectedZone?.geometry ?? null)} onGeometryChange={setGeometry} /></div>
        <div className="editor-card">
          <h3>{selectedZone ? "Sửa vùng" : "Vùng mới"}</h3>
          <p className="workspace-note">{selectedZone ? "Kéo các đỉnh trên bản đồ để đổi hình dạng, rồi bấm Lưu." : "Bấm Vẽ đa giác hoặc Vẽ chữ nhật trên bản đồ, đặt tên rồi bấm Lưu."}</p>
          <label>Tên vùng<input value={name} onChange={(event) => setName(event.target.value)} maxLength={160} disabled={busy} /></label>
          <label>Loại vùng<select value={classification} onChange={(event) => setClassification(event.target.value)} disabled={busy}><option value="NO_FLY">Vùng cấm bay</option><option value="RESTRICTED">Vùng hạn chế bay</option></select></label>
          <label>Hiển thị<select value={visibility} onChange={(event) => setVisibility(event.target.value as "PUBLIC" | "INTERNAL")} disabled={busy}><option value="PUBLIC">Công khai trên bản đồ</option><option value="INTERNAL">Chỉ nội bộ</option></select></label>
          <p className="workspace-note">{geometry ? "Đã có hình vùng." : "Chưa có hình vùng."}</p>
          <div className="editor-actions">
            <button className="primary-button" type="button" onClick={() => void saveZone()} disabled={busy || !name.trim() || !geometry}>{busyAction === "zone-save" ? "Đang lưu…" : "Lưu vùng"}</button>
            {selectedZone && <button className="danger-button" type="button" onClick={() => void removeZone()} disabled={busy}>Xóa vùng</button>}
            {(selectedZone || geometry) && <button type="button" onClick={() => beginZoneEdit(null)} disabled={busy}>Hủy</button>}
          </div>
          <h4>Danh sách vùng ({zones.length})</h4>
          {zones.length === 0 ? <p className="workspace-note">Chưa có vùng nào. Vẽ vùng đầu tiên trên bản đồ.</p> : <div className="zone-list">{zones.map((zone) => <button className={selectedZone?.id === zone.id ? "selected" : ""} type="button" key={zone.id} onClick={() => beginZoneEdit(zone)} disabled={busy}>{zone.name} · {zone.classification === "NO_FLY" ? "Cấm bay" : "Hạn chế bay"}{zone.visibility === "INTERNAL" ? " · nội bộ" : ""}</button>)}</div>}
        </div>
      </div>}

      {tab === "flights" && <div className="table-card">
        <div className="table-heading"><h3>Yêu cầu chờ duyệt</h3><button type="button" onClick={() => void run("refresh", refresh, "Không tải được dữ liệu")} disabled={busy}>Làm mới</button></div>
        <p className="workspace-note">Kết quả duyệt được trả về thiết bị Pi đã gửi yêu cầu. Đây là mô hình nghiên cứu, không phải giấy phép bay của cơ quan có thẩm quyền.</p>
        {pendingFlights.length === 0 ? <p className="workspace-note">Không có yêu cầu nào đang chờ.</p> : <div className="flight-list">{pendingFlights.map((flight) => flightCard(flight, true))}</div>}
        {decidedFlights.length > 0 && <><h4>Đã xử lý</h4><div className="flight-list">{decidedFlights.map((flight) => flightCard(flight, false))}</div></>}
      </div>}

      {tab === "accounts" && canReviewAccounts && <div className="table-card">
        <div className="table-heading"><h3>Tài khoản chờ duyệt</h3><span>{pendingAccounts.length} tài khoản</span></div>
        {pendingAccounts.length === 0 ? <p className="workspace-note">Không có tài khoản nào đang chờ duyệt.</p> : <div className="operations-list">{pendingAccounts.map((account) => <article key={account.id}>
          <div><strong>{account.username ?? account.display_name}</strong><small>{account.email ?? "không có email"}{account.email_verified ? "" : " · chưa xác nhận email"}</small></div>
          <div className="inline-actions">
            <select aria-label="Cấp tài khoản" value={approveRoles[account.id] ?? "OPERATOR"} onChange={(event) => setApproveRoles((current) => ({ ...current, [account.id]: event.target.value as StaffRole }))} disabled={busy}><option value="OPERATOR">Cấp 2 · sửa vùng, duyệt bay</option><option value="ADMIN">Cấp 1 · thêm duyệt tài khoản</option></select>
            <button className="primary-button" type="button" onClick={() => void changeStatus(account, "ACTIVE", "Duyệt tài khoản")} disabled={busy}>Duyệt</button>
            <button className="danger-button" type="button" onClick={() => void changeStatus(account, "REJECTED", "Từ chối tài khoản")} disabled={busy}>Từ chối</button>
          </div>
        </article>)}</div>}
        <h4>Tất cả tài khoản</h4>
        <div className="operations-list">{otherAccounts.map((account) => {
          const locked = account.role === "OWNER" || account.id === user.id;
          return <article key={account.id}>
            <div><strong>{account.username ?? account.display_name}</strong><small>{account.email ?? "không có email"} · {ROLE_LABEL[account.role] ?? account.role} · {ACCOUNT_STATUS_LABEL[account.status] ?? account.status}</small></div>
            {!locked && <div className="inline-actions">
              {account.status === "ACTIVE" && <select aria-label="Đổi cấp" value={account.role === "ADMIN" ? "ADMIN" : "OPERATOR"} onChange={(event) => void changeRole(account, event.target.value as StaffRole)} disabled={busy}><option value="OPERATOR">Cấp 2</option><option value="ADMIN">Cấp 1</option></select>}
              {account.status === "ACTIVE" && <button type="button" onClick={() => void changeStatus(account, "SUSPENDED", "Khóa tài khoản")} disabled={busy}>Khóa</button>}
              {account.status === "SUSPENDED" && <button type="button" onClick={() => void changeStatus(account, "ACTIVE", "Mở khóa tài khoản")} disabled={busy}>Mở khóa</button>}
            </div>}
          </article>;
        })}</div>
      </div>}
    </section>
  );
}
