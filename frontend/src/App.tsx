import { useCallback, useEffect, useState } from "react";
import { getMe, getPublicZones, logout, type Me, type Zone } from "./api";
import { AuthPanel } from "./components/auth/AuthPanel";
import { OperationsWorkspace } from "./components/operations/OperationsWorkspace";
import { MapPanel } from "./components/map/MapPanel";
import { AccountMenu } from "./components/account/AccountMenu";
import { ErrorBanner } from "./components/common/ErrorBanner";

export function App() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<Me | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [ownerBootstrapChallengeId, setOwnerBootstrapChallengeId] = useState("");

  const loadOverview = useCallback(async () => {
    setError(null);
    try {
      setZones(await getPublicZones());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể kết nối PC server");
    }
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể đăng xuất");
    }
  };

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    void getMe().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    const match = window.location.hash.match(/^#owner-bootstrap=([a-f0-9-]{16,64})$/i);
    if (!match) return;
    setOwnerBootstrapChallengeId(match[1]);
    setAuthOpen(true);
    // The challenge ID is only a lookup key, not an authenticator. Keep it in
    // the fragment so it is never sent in an HTTP request, then remove it from
    // the visible URL/history as soon as the UI has captured it.
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }, []);

  return (
    <main className="site-shell">
      <header className="topbar portal-topbar">
        <a className="brand-lockup" href={user?.status === "ACTIVE" && user.role !== "GUEST" ? "#workspace" : "#map-overview"} aria-label="Drone Zone Check — trang chủ">
          <img className="brand-mark" src="/logo-drone-zone-check.png" alt="Drone Zone Check · PNT / PVD" />
          <span className="brand-copy"><strong>DRONE ZONE CHECK</strong><small>PNT / PVD · BẢN ĐỒ VÙNG BAY</small></span>
        </a>
        {!user && <nav className="topbar-nav" aria-label="Điều hướng chính"><a href="#map-overview">Bản đồ vùng bay</a><span className="public-access-label"><span className="public-state-dot" aria-hidden="true" /> Công khai · chỉ đọc</span></nav>}
        <div className="auth-actions">
          {user ? <AccountMenu user={user} onLogout={() => void handleLogout()} onUpdated={setUser} /> : <button className="primary-button" type="button" onClick={() => setAuthOpen(true)}>Đăng nhập / Đăng ký</button>}
        </div>
      </header>

      {user?.status === "ACTIVE" && user.role !== "GUEST" ? <div id="workspace"><OperationsWorkspace user={user} onPublicZonesChanged={async () => setZones(await getPublicZones())} /></div> : <>
        <section id="map-overview" className="content-section map-content-section">
          <div className="portal-heading">
            <div className="portal-heading-copy">
              <p className="eyebrow">BẢN ĐỒ VÙNG BAY · WGS84</p>
              <h1>Bản đồ vùng cấm bay và hạn chế bay.</h1>
              <p>Ai cũng xem được bản đồ. Cán bộ đăng nhập để cập nhật vùng và duyệt yêu cầu bay.</p>
            </div>
            <div className="portal-count" aria-live="polite"><strong>{zones.length}</strong><span>khu vực<br />công khai</span></div>
          </div>
          <ErrorBanner message={error} onDismiss={() => setError(null)} className="portal-error" />
          <MapPanel zones={zones} />
          {!error && zones.length === 0 ? <div className="empty-state map-empty-state"><strong>Chưa có vùng bay được công bố</strong><span>Khu vực bản đồ vẫn hoạt động; hiện chưa có dữ liệu vùng để hiển thị.</span></div> : null}
          {!error && zones.length > 0 && (
            <div className="zone-grid" aria-label="Danh sách vùng công khai">
              {zones.map((zone) => (
                <article className="zone-card" key={zone.id}>
                  <span className={`zone-icon ${zone.classification === "NO_FLY" ? "zone-icon-ban" : "zone-icon-limit"}`} aria-hidden="true" />
                  <div className="zone-body"><h3>{zone.name}</h3><p>{zone.classification === "NO_FLY" ? "Vùng cấm bay" : "Vùng hạn chế bay"}</p></div>
                  <span className="zone-status">CHỈ ĐỌC</span>
                </article>
              ))}
            </div>
          )}
        </section>
        {user && <section className="workspace-section pending-access" aria-label="Trạng thái phê duyệt tài khoản"><p className="eyebrow">TÀI KHOẢN / CHỜ DUYỆT</p><h2>Tài khoản đang chờ duyệt</h2><p>Đã hoàn tất xác nhận email và 2FA. Bạn sẽ dùng được các chức năng sau khi tài khoản chính hoặc Admin cấp 1 duyệt.</p><button type="button" onClick={() => void handleLogout()}>Đăng xuất</button></section>}
      </>}

        <footer className="site-footer">
        <div><strong>DỰ ÁN ĐƯỢC THỰC HIỆN BỞI PHẠM NGỌC TẤN VÀ PHAN VĂN ĐÔNG</strong><small>Mô hình nghiên cứu · không phải cổng thông tin chính thức của Bộ Quốc phòng hay cơ quan nhà nước.</small></div>
        <span>DỮ LIỆU BẢN ĐỒ CHỈ MANG TÍNH THAM KHẢO</span>
      </footer>
      {authOpen && <AuthPanel initialBootstrapChallengeId={ownerBootstrapChallengeId || undefined} onClose={() => setAuthOpen(false)} onAuthenticated={(me) => { setUser(me); setAuthOpen(false); }} />}
    </main>
  );
}
