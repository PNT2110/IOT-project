# HANDOFF REPORT — Explorer R6-3

**Date**: 2026-09-14  
**Investigator**: Explorer R6-3 (`.agents/explorer_r6_3`)  
**Mission**: Investigate and design implementation for Requirement R4 (Login UI concise "tên đăng nhập") and Requirement R5 (Migrate MOD Server to Google Apps Script `backend/mod_server.gs`, Pi5 `MOD_WEBAPP_URL` integration, and pytest mocking).

---

## 1. Observation

### 1.1 Login UI Adjustment (R4)
1. **Codebase Grep in `frontend/src/`**:
   Search for "tài khoản" and "pi5" revealed only one login field containing "pi5" in `frontend/src/App.tsx`:
   - File: `/home/pnt/IOT/frontend/src/App.tsx`, Lines 76–85:
     ```tsx
     <form onSubmit={submit} className="login-form">
       <label>
         <span>Tài khoản:</span>
         <input
           autoComplete="username"
           value={username}
           onChange={(e) => setUsername(e.target.value)}
           placeholder="pi5 hoặc tên đăng nhập"
           required
         />
       </label>
     ```
2. **Examination of Other Forms**:
   - `frontend/src/Register.tsx`: Lines 119–160 show registration fields ("Họ và tên đầy đủ", "Ngày sinh", "Email", "Mật khẩu"). No "tài khoản pi5" phrase exists.
   - `frontend/src/SetupAccount.tsx`: Lines 56–77 show first-login admin setup ("Email quản trị chính thức", "Mật khẩu mới an toàn"). No "tài khoản pi5" phrase exists.
   - `frontend/src/SessionTab.tsx`: Line 230 has table header `<th>Tên đăng nhập</th>`, Line 305 has `<th>Tài khoản</th>`.
   - `frontend/src/Tabs.tsx`: Line 57 has navigation label `label: 'Tài khoản'`.
   - **Conclusion on Occurrences**: The exact and only occurrence on the login form that exposes "pi5" is the label `<span>Tài khoản:</span>` paired with `placeholder="pi5 hoặc tên đăng nhập"` in `frontend/src/App.tsx:77-82`.

### 1.2 MOD Server (`backend/mod_server.py`) Architecture & Protocol (R5)
1. **Current Implementation**:
   - `backend/mod_server.py` is an 1814-line FastAPI service running on port 9000 backed by SQLite WAL (`mod_database.sqlite3`).
   - Key Endpoints consumed by GCS:
     - `POST /api/v1/mod/flight-requests`: Submits flight permission request.
       - Fields: `drone_id`, `pilot_name`, `license_id`, `flight_date`, `time_from`, `time_to`, `latitude`, `longitude`, `radius_m`, `timestamp`, `nonce`.
       - Anti-replay: Checks `abs(now - timestamp) <= 300` and ensures `nonce` is unique in `mod_used_nonces`.
       - Response: `{"request_id": "REQ-0001", "id": "REQ-0001", "status": "PENDING", "message": "..."}`.
     - `POST /api/v1/mod/flight-requests/{req_id}/approve` (or `/admin/requests/{req_id}/approve`):
       - Generates 1km geodesic circle polygon (64 vertices) around `(latitude, longitude)`.
       - Assigns `permission_token` (e.g. `MOD-20260914-REQ-0001`), `valid_from` (`2026-09-14T08:00:00Z`), `valid_to` (`2026-09-14T17:00:00Z`), and sets status to `"APPROVED"`.
     - `GET /api/v1/mod/flight-requests/{drone_id}/active`:
       - Checks active permit for `drone_id`.
       - Validates expiration against `valid_to`. If expired or force_expired, marks `"EXPIRED"`, `armed_allowed: false`.
       - If approved and active, returns:
         ```json
         {
           "status": "APPROVED",
           "permission_token": "MOD-...",
           "drone_id": "DRONE-PI5-001",
           "center": {"latitude": 10.762622, "longitude": 106.660172},
           "center_lat": 10.762622,
           "center_lon": 106.660172,
           "radius_m": 1000.0,
           "valid_from": "2026-09-14T08:00:00Z",
           "valid_to": "2026-09-14T17:00:00Z",
           "polygon": {"type": "Polygon", "coordinates": [...]},
           "polygon_geojson": {"type": "Polygon", "coordinates": [...]},
           "armed_allowed": true,
           "message": "Giấy phép bay còn hiệu lực."
         }
         ```
     - `GET /api/v1/mod/zones`: Returns GeoJSON `FeatureCollection` with active 1km flight corridors and No-Fly zones.
2. **Geodesic Circle Math (`mod_server.py:264-287`)**:
   - Uses WGS84 Earth radius $R = 6,378,137.0$ m, angular distance $d/R = 1000 / 6378137.0$.
   - Iterates $i \in [0, 64]$ with bearing $\theta = 2\pi i / 64$:
     $$\phi = \arcsin(\sin(\phi_0)\cos(d/R) + \cos(\phi_0)\sin(d/R)\cos(\theta))$$
     $$\lambda = \lambda_0 + \text{atan2}(\sin(\theta)\sin(d/R)\cos(\phi_0), \cos(d/R) - \sin(\phi_0)\sin(\phi))$$
   - Emits 64-vertex GeoJSON Polygon `[[lon, lat], ...]`.

### 1.3 Pi5 Backend Interaction (`backend/app/main.py`)
1. **Current Calls to MOD Server**:
   - `backend/app/main.py:133-147` (`fetch_active_mod_permit`):
     ```python
     async def fetch_active_mod_permit(drone_id: str) -> Optional[Dict[str, Any]]:
         mod_base = os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")
         try:
             async with httpx.AsyncClient(timeout=2.0) as client:
                 resp = await client.get(f"{mod_base}/api/v1/mod/flight-requests/{drone_id}/active")
                 if resp.status_code == 200:
                     data = resp.json()
                     if isinstance(data, dict):
                         return data
         except Exception:
             pass
         return None
     ```
   - `backend/app/main.py:1306-1331` (`submit_flight_request`):
     ```python
     mod_base = os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")
     try:
         async with httpx.AsyncClient(timeout=4.0) as client:
             resp = await client.post(f"{mod_base}/api/v1/mod/flight-requests", json=mod_payload)
             if resp.status_code in (200, 201):
                 data = resp.json()
                 ...
                 return data
     ```
   - `backend/app/main.py:254-285` (ARM safety loop):
     Calls `fetch_active_mod_permit(drone_id)` every 1s, checks `permit.get("status") == "APPROVED"`, `is_permit_time_valid(valid_from, valid_to, now)`, and `haversine_distance_m(...) <= radius_m`.
   - `backend/app/main.py:1088-1124` (`POST /api/v1/commands/arm`):
     Calls `fetch_active_mod_permit(drone_id)` before issuing ARM command.

### 1.4 Google Apps Script Web App Mechanics & Redirect Pitfall
1. **Web App URL Format**:
   - Deployed Google Apps Script URL format: `https://script.google.com/macros/s/<SCRIPT_ID>/exec`.
   - All requests (GET / POST) hit this single URL. Query parameters route GET (`e.parameter`), POST body routes POST (`e.postData.contents`).
2. **Critical HTTP 302 Redirect Behavior**:
   - When Google Apps Script responds from `doGet` or `doPost`, Google's proxy returns an **HTTP 302 Found** redirecting to `https://script.googleusercontent.com/macros/echo?...`.
   - In Python's `httpx.AsyncClient`, `follow_redirects` defaults to `False`!
   - If `follow_redirects=False`, `httpx` returns status `302` and does NOT fetch the body, causing `resp.status_code == 200` to FAIL!
   - Therefore, `httpx.AsyncClient(follow_redirects=True, timeout=8.0)` is **mandatory** for calling Google Apps Script Web Apps.

### 1.5 Existing Tests & Flaws Observed
1. `backend/tests/test_flight_request_submit.py`:
   - Runs against TestClient and monkeypatches `main.httpx.AsyncClient` with `_FakeClient`. All 23 tests PASS.
2. `backend/tests/test_gd5_window_expiry.py`:
   - Monkeypatches `app.main.fetch_active_mod_permit`. All 5 tests PASS with `PYTHONPATH=backend`.
3. `backend/tests/test_mod_server.py`:
   - Line 168 hardcodes `"flight_date": "2026-09-13"`. When run on `2026-09-14`, test 5 fails with `AssertionError: assert 'EXPIRED' == 'APPROVED'` because yesterday's date is immediately treated as expired. This must be updated to use `datetime.now(timezone.utc).strftime("%Y-%m-%d")`.

---

## 2. Logic Chain

```
[Requirement R4: Remove "tài khoản pi5", display "tên đăng nhập"]
  │
  ├─> Observation: App.tsx:77 has "Tài khoản:", App.tsx:82 has placeholder "pi5 hoặc tên đăng nhập"
  │   All other forms (Register, SetupAccount) do not reference "pi5" in login fields.
  │
  └─> Action: Replace label with "Tên đăng nhập:" and placeholder with "tên đăng nhập".
      Result satisfies R4 completely and concisely.

[Requirement R5: Migrate MOD Server to Google Apps Script backend/mod_server.gs]
  │
  ├─> Google Apps Script Web App Architecture:
  │   - Entry points: doGet(e) for active permit checks, zone queries, health check.
  │   - doPost(e) for flight permission submission with anti-replay timestamp/nonce.
  │   - Self-contained storage: PropertiesService.getScriptProperties() avoids dependency on external Google Sheets.
  │   - Anti-replay cache: CacheService.getScriptCache() with 600s TTL for nonces.
  │   - 1km geodesic math: exact port of WGS84 64-vertex circle algorithm to JavaScript.
  │   - Deployment header: Step-by-step instructions for Web App deployment with Anyone access.
  │
  ├─> Pi5 Backend Integration (main.py & config.py):
  │   - Read MOD_WEBAPP_URL from .env (fallback to MOD_SERVER_URL).
  │   - Detect GAS Web App vs local FastAPI via URL (/exec or script.google.com).
  │   - Crucial fix: httpx.AsyncClient(timeout=8.0, follow_redirects=True) to handle GAS 302 redirects.
  │   - Preserve backward compatibility with existing tests.
  │
  └─> Clean Pytest Mocking Strategy:
      - Unit/integration tests mock fetch_active_mod_permit or httpx.AsyncClient.
      - MockMODServer in tests/common.py updated to support /exec and action query parameters.
      - Zero live internet dependency during CI / pytest test runs.
```

---

## 3. Caveats

1. **Google Apps Script Cold Starts**:
   Google Apps Script Web Apps have a cold-start delay of 1.5 to 3.0 seconds on infrequent requests. `fetch_active_mod_permit` timeout must be set to at least 5.0 seconds (up from 2.0s), and `submit_flight_request` to 8.0-10.0 seconds.
2. **Access Control on Google Web App**:
   When deploying the Web App, the user MUST select **"Who has access: Anyone"**. If "Only myself" is selected, Google returns a 401/302 to a Google Accounts login page, which the Pi5 headless backend cannot authenticate.
3. **No-Fly Zones in GAS**:
   In `mod_server.py`, fixed no-fly zones were stored in SQLite. In `mod_server.gs`, no-fly zones can be initialized with default coordinates in `PropertiesService` or dynamically submitted via `action=create_zone`.
4. **`ENABLE_REAL_FLIGHT_COMMANDS`**:
   Must remain `False` across all configurations in compliance with fail-safe safety guidelines.

---

## 4. Conclusion & Implementation Plan

### Part 1: Login UI Adjustment (R4)
**Target File**: `/home/pnt/IOT/frontend/src/App.tsx`  
**Target Lines**: 76–85  

**Before**:
```tsx
          <label>
            <span>Tài khoản:</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="pi5 hoặc tên đăng nhập"
              required
            />
          </label>
```

**After**:
```tsx
          <label>
            <span>Tên đăng nhập:</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="tên đăng nhập"
              required
            />
          </label>
```

---

### Part 2: Complete `backend/mod_server.gs` Specification (R5)
**Target File**: `/home/pnt/IOT/backend/mod_server.gs`  
Below is the complete, production-grade Google Apps Script source code to be placed in `backend/mod_server.gs`:

```javascript
/**
 * ============================================================================
 * BỘ QUỐC PHÒNG (MOD) — UAV FLIGHT AUTHORIZATION & AIRSPACE SERVER
 * Phiên bản Google Apps Script Web App (v2.0.0)
 * ============================================================================
 * 
 * HƯỚNG DẪN TRIỂN KHAI GOOGLE APPS SCRIPT WEB APP:
 * ----------------------------------------------------------------------------
 * 1. Truy cập https://script.google.com/home và đăng nhập tài khoản Google.
 * 2. Bấm nút "New project" ("Dự án mới").
 * 3. Đổi tên dự án thành "MOD_Flight_Server".
 * 4. Xóa toàn bộ mã mặc định trong tệp "Code.gs", dán toàn bộ nội dung tệp này vào.
 * 5. Bấm nút "Deploy" ("Triển khai") ở góc trên bên phải -> chọn "New deployment" ("Triển khai mới").
 * 6. Bấm vào biểu tượng bánh răng bên cạnh "Select type" -> chọn "Web app" ("Ứng dụng web").
 * 7. Cấu hình triển khai:
 *    - Description: "MOD UAV Flight Authorization Server v2"
 *    - Execute as: "Me" ("Tôi" - tài khoản của bạn)
 *    - Who has access: "Anyone" ("Bất kỳ ai")  <-- BẮT BUỘC để Pi5 có thể gọi API mà không bị chặn đăng nhập Google
 * 8. Bấm "Deploy" ("Triển khai") và cấp quyền (Review permissions -> Allow) nếu được yêu cầu.
 * 9. Sao chép URL Web App được tạo ra.
 *    Định dạng URL: https://script.google.com/macros/s/<DEPLOYMENT_ID>/exec
 * 10. Mở tệp .env trên Raspberry Pi 5 (`/home/pnt/IOT/.env`), cấu hình:
 *     MOD_WEBAPP_URL=https://script.google.com/macros/s/<DEPLOYMENT_ID>/exec
 * 11. Khởi động lại dịch vụ backend trên Pi5:
 *     sudo systemctl restart drone-station-backend (hoặc chạy lại python -m app.main)
 * ============================================================================
 */

// --- CẤU HÌNH HỆ THỐNG ---
var CONFIG = {
  AUTO_APPROVE: true,              // Tự động phê duyệt yêu cầu bay hợp lệ (1km corridor)
  DEFAULT_RADIUS_M: 1000.0,        // Bán kính vùng bay mặc định: 1km (1000m)
  EARTH_RADIUS_M: 6378137.0,       // Bán kính Trái đất theo mô hình WGS84
  GEOFENCE_VERTICES: 64,           // Độ phân giải đa giác vùng bay (64 đỉnh)
  MAX_TIMESTAMP_DEVIATION_S: 300,  // Sai lệch thời gian tối đa chống tấn công Replay (300 giây)
  NONCE_CACHE_TTL_S: 600,          // Thời gian lưu cache Nonce chống lặp (600 giây)
  ADMIN_KEY: "mod_admin_2026_sec"  // Khóa bí mật cho các thao tác quản trị đặc biệt
};

/**
 * Endpoint xử lý HTTP GET:
 * - Query active permit: ?action=get_active_permit&drone_id=DRONE-PI5-001 (hoặc ?drone_id=...)
 * - Query zones GeoJSON: ?action=zones (hoặc ?action=get_zones)
 * - Query all requests:  ?action=requests&admin_key=...
 * - Health check:        ?action=health hoặc không truyền tham số
 * - Approve request:     ?action=approve&request_id=REQ-0001&admin_key=...
 * - Reject request:      ?action=reject&request_id=REQ-0001&reason=...&admin_key=...
 */
function doGet(e) {
  try {
    var params = (e && e.parameter) ? e.parameter : {};
    var action = (params.action || "").toLowerCase();

    // 1. Health check
    if (!action || action === "health" || action === "ping") {
      return jsonResponse({
        status: "healthy",
        service: "mod_server_gas",
        version: "2.0.0",
        timestamp: new Date().toISOString(),
        message: "Hệ thống cấp phép bay Bộ Quốc Phòng (Google Apps Script) hoạt động bình thường."
      });
    }

    // 2. Lấy giấy phép bay đang có hiệu lực theo drone_id
    if (action === "get_active_permit" || action === "active" || params.drone_id) {
      var droneId = params.drone_id || "DRONE-PI5-001";
      return jsonResponse(getActivePermit(droneId));
    }

    // 3. Lấy danh sách vùng bay (1km Corridors + No-Fly Zones) định dạng GeoJSON
    if (action === "zones" || action === "get_zones") {
      return jsonResponse(getZonesFeatureCollection());
    }

    // 4. Danh sách toàn bộ yêu cầu bay (dành cho quản trị)
    if (action === "requests" || action === "list") {
      return jsonResponse(listAllRequests(params.admin_key));
    }

    // 5. Quản trị phê duyệt yêu cầu
    if (action === "approve") {
      return jsonResponse(approveRequest(params.request_id, params.admin_key));
    }

    // 6. Quản trị từ chối yêu cầu
    if (action === "reject") {
      return jsonResponse(rejectRequest(params.request_id, params.reason, params.admin_key));
    }

    return jsonResponse({
      status: "error",
      detail: "Hành động không hợp lệ: " + action
    }, 400);

  } catch (err) {
    return jsonResponse({
      status: "error",
      detail: "Lỗi nội bộ máy chủ: " + err.toString()
    }, 500);
  }
}

/**
 * Endpoint xử lý HTTP POST:
 * - Nộp đơn xin phép bay: Payload chứa thông tin chuyến bay (drone_id, pilot_name, v.v.)
 * - Duyệt/Từ chối qua POST: { action: "approve"|"reject", request_id: "..." }
 */
function doPost(e) {
  try {
    var rawContents = (e && e.postData && e.postData.contents) ? e.postData.contents : "{}";
    var payload = {};
    try {
      payload = JSON.parse(rawContents);
    } catch (parseErr) {
      return jsonResponse({ status: "error", detail: "JSON payload không hợp lệ" }, 400);
    }

    var action = (payload.action || (e && e.parameter && e.parameter.action) || "submit_request").toLowerCase();

    // 1. Phê duyệt yêu cầu
    if (action === "approve") {
      return jsonResponse(approveRequest(payload.request_id, payload.admin_key));
    }

    // 2. Từ chối yêu cầu
    if (action === "reject") {
      return jsonResponse(rejectRequest(payload.request_id, payload.reason, payload.admin_key));
    }

    // 3. Thêm vùng cấm bay thủ công
    if (action === "create_zone") {
      return jsonResponse(createZone(payload, payload.admin_key));
    }

    // 4. Mặc định: Nộp hồ sơ xin phép bay (Flight Permission Request)
    return jsonResponse(handleSubmitFlightRequest(payload));

  } catch (err) {
    return jsonResponse({
      status: "error",
      detail: "Lỗi xử lý yêu cầu: " + err.toString()
    }, 500);
  }
}

// ============================================================================
// LOGIC NGHIỆP VỤ CẤP PHÉP BAY & BẢO MẬT
// ============================================================================

/**
 * Xử lý tiếp nhận và thẩm định hồ sơ xin cấp phép bay
 */
function handleSubmitFlightRequest(data) {
  var nowSec = Math.floor(Date.now() / 1000);

  // 1. Kiểm tra chống tấn công phát lại (Anti-Replay: Timestamp Skew)
  if (data.timestamp !== undefined && data.timestamp !== null) {
    var tsVal = parseInt(data.timestamp, 10);
    if (Math.abs(nowSec - tsVal) > CONFIG.MAX_TIMESTAMP_DEVIATION_S) {
      return {
        status: "REJECTED",
        detail: "Độ lệch thời gian timestamp vượt quá 300 giây (Phát hiện tấn công phát lại Replay)."
      };
    }
  }

  // 2. Kiểm tra chống tấn công phát lại (Anti-Replay: Nonce Tracking)
  if (data.nonce) {
    var cache = CacheService.getScriptCache();
    var cachedNonce = cache.get("nonce_" + data.nonce);
    if (cachedNonce) {
      return {
        status: "REJECTED",
        detail: "Mã Nonce đã được sử dụng (Phát hiện tấn công phát lại Replay)."
      };
    }
    cache.put("nonce_" + data.nonce, "used", CONFIG.NONCE_CACHE_TTL_S);
  }

  // 3. Chuẩn hóa dữ liệu đầu vào
  var droneId = (data.drone_id || "DRONE-PI5-001").trim();
  var pilotName = (data.pilot_name || data.full_name || "Phi công").trim();
  var licenseId = (data.license_id || "VN-UAV-DEFAULT").trim();
  var flightDate = data.flight_date || Utilities.formatDate(new Date(), "GMT", "yyyy-MM-dd");
  var timeFrom = data.time_from || "00:00";
  var timeTo = data.time_to || "23:59";
  var latitude = parseFloat(data.latitude || 10.762622);
  var longitude = parseFloat(data.longitude || 106.660172);
  var radiusM = parseFloat(data.radius_m || CONFIG.DEFAULT_RADIUS_M);

  if (isNaN(latitude) || isNaN(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    return { status: "error", detail: "Tọa độ GPS không hợp lệ" };
  }

  // 4. Sinh mã hồ sơ tuần tự REQ-XXXX
  var props = PropertiesService.getScriptProperties();
  var counter = parseInt(props.getProperty("REQUEST_COUNTER") || "0", 10) + 1;
  props.setProperty("REQUEST_COUNTER", counter.toString());
  var reqId = "REQ-" + ("0000" + counter).slice(-4);

  var nowIso = new Date().toISOString();
  var validFromIso = flightDate + "T" + timeFrom + ":00Z";
  var validToIso = flightDate + "T" + timeTo + ":00Z";

  // 5. Tạo hành lang bay 1km geodesic
  var polygon = generateGeodesicCircle(latitude, longitude, radiusM, CONFIG.GEOFENCE_VERTICES);
  var dateTag = Utilities.formatDate(new Date(), "GMT", "yyyyMMdd");
  var token = "MOD-" + dateTag + "-" + reqId;

  var status = CONFIG.AUTO_APPROVE ? "APPROVED" : "PENDING";

  var requestRecord = {
    id: reqId,
    request_id: reqId,
    drone_id: droneId,
    pilot_name: pilotName,
    license_id: licenseId,
    flight_date: flightDate,
    time_from: timeFrom,
    time_to: timeTo,
    latitude: latitude,
    longitude: longitude,
    radius_m: radiusM,
    status: status,
    permission_token: status === "APPROVED" ? token : null,
    valid_from: validFromIso,
    valid_to: validToIso,
    polygon: polygon,
    polygon_geojson: polygon,
    created_at: nowIso,
    reviewed_at: status === "APPROVED" ? nowIso : null,
    reviewed_by: status === "APPROVED" ? "SYSTEM_AUTO_APPROVE" : null
  };

  // 6. Lưu trữ vào PropertiesService
  props.setProperty("MOD_REQ_" + reqId, JSON.stringify(requestRecord));
  if (status === "APPROVED") {
    props.setProperty("MOD_PERMIT_" + droneId, JSON.stringify(requestRecord));
  }

  // Cập nhật danh sách mã hồ sơ
  var reqListStr = props.getProperty("MOD_REQUEST_IDS") || "[]";
  var reqList = JSON.parse(reqListStr);
  reqList.unshift(reqId);
  if (reqList.length > 200) reqList = reqList.slice(0, 200); // Giữ tối đa 200 bản ghi gần nhất
  props.setProperty("MOD_REQUEST_IDS", JSON.stringify(reqList));

  return {
    request_id: reqId,
    id: reqId,
    status: status,
    permission_token: requestRecord.permission_token,
    valid_from: validFromIso,
    valid_to: validToIso,
    polygon: polygon,
    polygon_geojson: polygon,
    message: status === "APPROVED"
      ? "Yêu cầu cấp phép bay đã được phê duyệt tự động. Hành lang bay 1km đã mở."
      : "Yêu cầu đã được lưu trữ, đang chờ Quản trị viên Bộ Quốc Phòng phê duyệt."
  };
}

/**
 * Lấy thông tin giấy phép bay đang hoạt động của Drone
 */
function getActivePermit(droneId) {
  var props = PropertiesService.getScriptProperties();
  var raw = props.getProperty("MOD_PERMIT_" + droneId);
  if (!raw) {
    return {
      status: "NONE",
      drone_id: droneId,
      permission_token: null,
      center_lat: 0.0,
      center_lon: 0.0,
      radius_m: CONFIG.DEFAULT_RADIUS_M,
      valid_from: "",
      valid_to: "",
      armed_allowed: false,
      message: "Không có vùng bay hợp lệ cho thiết bị này."
    };
  }

  var permit = JSON.parse(raw);

  // Kiểm tra thời hạn hiệu lực (Time Window Expiration)
  var now = new Date();
  var validTo = new Date(permit.valid_to);
  var validFrom = new Date(permit.valid_from);

  if (now > validTo || permit.force_expired) {
    permit.status = "EXPIRED";
    permit.permission_token = null;
    permit.armed_allowed = false;
    permit.message = "Giấy phép bay đã hết hạn. Khóa an toàn lệnh cất cánh (ARM).";
    props.setProperty("MOD_PERMIT_" + droneId, JSON.stringify(permit));
    return permit;
  }

  if (permit.status === "APPROVED") {
    permit.armed_allowed = true;
    permit.center = { latitude: permit.latitude, longitude: permit.longitude };
    permit.center_lat = permit.latitude;
    permit.center_lon = permit.longitude;
    permit.message = "Giấy phép bay còn hiệu lực.";
    return permit;
  }

  permit.armed_allowed = false;
  return permit;
}

/**
 * Trả về GeoJSON FeatureCollection của tất cả vùng bay được duyệt và vùng cấm bay
 */
function getZonesFeatureCollection() {
  var props = PropertiesService.getScriptProperties();
  var features = [];

  // Lấy các giấy phép bay đang APPROVED
  var reqListStr = props.getProperty("MOD_REQUEST_IDS") || "[]";
  var reqList = JSON.parse(reqListStr);

  var now = new Date();
  for (var i = 0; i < reqList.length; i++) {
    var raw = props.getProperty("MOD_REQ_" + reqList[i]);
    if (!raw) continue;
    var req = JSON.parse(raw);
    if (req.status === "APPROVED" && new Date(req.valid_to) >= now) {
      features.push({
        type: "Feature",
        id: "approved_" + req.id,
        properties: {
          id: "approved_" + req.id,
          request_id: req.id,
          drone_id: req.drone_id,
          pilot_name: req.pilot_name,
          type: "approved_zone",
          name: "Hành lang bay " + req.drone_id + " (1km)",
          valid_from: req.valid_from,
          valid_to: req.valid_to,
          is_active: true,
          status: "APPROVED"
        },
        geometry: req.polygon
      });
    }
  }

  // Lấy các vùng cấm bay cố định (No-Fly Zones) nếu có
  var customZonesStr = props.getProperty("MOD_CUSTOM_ZONES") || "[]";
  var customZones = JSON.parse(customZonesStr);
  for (var j = 0; j < customZones.length; j++) {
    features.push(customZones[j]);
  }

  return {
    type: "FeatureCollection",
    features: features
  };
}

/**
 * Thuật toán sinh đa giác tròn trắc địa (WGS84 Geodesic Circle) bán kính 1km với 64 đỉnh
 */
function generateGeodesicCircle(lat, lon, radiusM, numPoints) {
  radiusM = radiusM || CONFIG.DEFAULT_RADIUS_M;
  numPoints = numPoints || CONFIG.GEOFENCE_VERTICES;
  var coords = [];
  var rEarth = CONFIG.EARTH_RADIUS_M;
  var latRad = (lat * Math.PI) / 180.0;
  var lonRad = (lon * Math.PI) / 180.0;
  var dDivR = radiusM / rEarth;

  for (var i = 0; i <= numPoints; i++) {
    var bearing = (2.0 * Math.PI * i) / numPoints;
    var ptLat = Math.asin(
      Math.sin(latRad) * Math.cos(dDivR) +
      Math.cos(latRad) * Math.sin(dDivR) * Math.cos(bearing)
    );
    var ptLon = lonRad + Math.atan2(
      Math.sin(bearing) * Math.sin(dDivR) * Math.cos(latRad),
      Math.cos(dDivR) - Math.sin(latRad) * Math.sin(ptLat)
    );
    var degLon = (ptLon * 180.0) / Math.PI;
    var degLat = (ptLat * 180.0) / Math.PI;
    coords.push([Math.round(degLon * 1e6) / 1e6, Math.round(degLat * 1e6) / 1e6]);
  }

  return {
    type: "Polygon",
    coordinates: [coords]
  };
}

/**
 * Phê duyệt yêu cầu bay thủ công
 */
function approveRequest(reqId, adminKey) {
  if (CONFIG.ADMIN_KEY && adminKey !== CONFIG.ADMIN_KEY) {
    return { status: "error", detail: "Khóa quản trị không chính xác" };
  }
  var props = PropertiesService.getScriptProperties();
  var raw = props.getProperty("MOD_REQ_" + reqId);
  if (!raw) return { status: "error", detail: "Không tìm thấy hồ sơ: " + reqId };

  var req = JSON.parse(raw);
  var polygon = generateGeodesicCircle(req.latitude, req.longitude, req.radius_m, CONFIG.GEOFENCE_VERTICES);
  var dateTag = Utilities.formatDate(new Date(), "GMT", "yyyyMMdd");
  var token = "MOD-" + dateTag + "-" + req.id;
  var nowIso = new Date().toISOString();

  req.status = "APPROVED";
  req.permission_token = token;
  req.polygon = polygon;
  req.polygon_geojson = polygon;
  req.reviewed_at = nowIso;
  req.reviewed_by = "ADMIN";

  props.setProperty("MOD_REQ_" + reqId, JSON.stringify(req));
  props.setProperty("MOD_PERMIT_" + req.drone_id, JSON.stringify(req));

  return {
    status: "APPROVED",
    request_id: reqId,
    permission_token: token,
    valid_from: req.valid_from,
    valid_to: req.valid_to,
    polygon: polygon
  };
}

/**
 * Từ chối yêu cầu bay
 */
function rejectRequest(reqId, reason, adminKey) {
  if (CONFIG.ADMIN_KEY && adminKey !== CONFIG.ADMIN_KEY) {
    return { status: "error", detail: "Khóa quản trị không chính xác" };
  }
  var props = PropertiesService.getScriptProperties();
  var raw = props.getProperty("MOD_REQ_" + reqId);
  if (!raw) return { status: "error", detail: "Không tìm thấy hồ sơ: " + reqId };

  var req = JSON.parse(raw);
  req.status = "REJECTED";
  req.rejection_reason = reason || "Từ chối theo quy chế an ninh không phận";
  req.reviewed_at = new Date().toISOString();
  req.reviewed_by = "ADMIN";

  props.setProperty("MOD_REQ_" + reqId, JSON.stringify(req));

  var activePermitRaw = props.getProperty("MOD_PERMIT_" + req.drone_id);
  if (activePermitRaw) {
    var activePermit = JSON.parse(activePermitRaw);
    if (activePermit.id === reqId) {
      props.deleteProperty("MOD_PERMIT_" + req.drone_id);
    }
  }

  return {
    status: "REJECTED",
    request_id: reqId,
    rejection_reason: req.rejection_reason
  };
}

/**
 * Thêm vùng cấm bay thủ công
 */
function createZone(zoneData, adminKey) {
  if (CONFIG.ADMIN_KEY && adminKey !== CONFIG.ADMIN_KEY) {
    return { status: "error", detail: "Khóa quản trị không chính xác" };
  }
  var props = PropertiesService.getScriptProperties();
  var customZonesStr = props.getProperty("MOD_CUSTOM_ZONES") || "[]";
  var customZones = JSON.parse(customZonesStr);

  var zoneId = zoneData.id || "zone_" + Date.now();
  var feature = {
    type: "Feature",
    id: zoneId,
    properties: {
      id: zoneId,
      name: zoneData.name || "Vùng cấm bay",
      type: zoneData.zone_type || "prohibited",
      is_active: true
    },
    geometry: zoneData.geometry
  };
  customZones.push(feature);
  props.setProperty("MOD_CUSTOM_ZONES", JSON.stringify(customZones));
  return { status: "created", zone: feature };
}

/**
 * Liệt kê danh sách hồ sơ xin phép bay
 */
function listAllRequests(adminKey) {
  var props = PropertiesService.getScriptProperties();
  var reqListStr = props.getProperty("MOD_REQUEST_IDS") || "[]";
  var reqList = JSON.parse(reqListStr);
  var list = [];
  for (var i = 0; i < reqList.length; i++) {
    var raw = props.getProperty("MOD_REQ_" + reqList[i]);
    if (raw) list.push(JSON.parse(raw));
  }
  return { requests: list, count: list.length };
}

/**
 * Helper đóng gói phản hồi chuẩn JSON cho Google Apps Script Web App
 */
function jsonResponse(data, statusCode) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
```

---

### Part 3: Pi5 Backend Integration Plan (`backend/app/main.py`)
**Files to update**:
1. `backend/app/config.py`: Add `mod_webapp_url: str` setting with `.env` reading.
2. `backend/app/main.py`:
   - Update `fetch_active_mod_permit` to support both `MOD_WEBAPP_URL` and legacy `MOD_SERVER_URL`.
   - Update `submit_flight_request` to send `action: "submit_request"` when calling GAS Web App.
   - **Crucial**: Set `httpx.AsyncClient(timeout=8.0, follow_redirects=True)` so HTTP 302 redirects from Google Apps Script are followed seamlessly.

#### 1. Update `backend/app/config.py`:
```python
# Insert near line 34 in Settings dataclass:
    mod_webapp_url: str = os.getenv("MOD_WEBAPP_URL", os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")).strip()
```
And at top of `backend/app/config.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

#### 2. Update `fetch_active_mod_permit` in `backend/app/main.py`:
**Before** (Lines 133–147):
```python
async def fetch_active_mod_permit(drone_id: str) -> Optional[Dict[str, Any]]:
    """Query active approved flight permission from MOD server or fallback cache."""
    mod_base = os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")
    # 1. HTTP query to MOD server
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{mod_base}/api/v1/mod/flight-requests/{drone_id}/active")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data
    except Exception:
        pass

    return None
```

**After**:
```python
async def fetch_active_mod_permit(drone_id: str) -> Optional[Dict[str, Any]]:
    """Query active approved flight permission from MOD server (GAS Web App or FastAPI)."""
    mod_url = os.getenv("MOD_WEBAPP_URL", os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")).strip()
    is_gas = "script.google.com" in mod_url or mod_url.endswith("/exec")

    try:
        # Note: follow_redirects=True is mandatory for Google Apps Script 302 redirects!
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            if is_gas:
                resp = await client.get(mod_url, params={"action": "get_active_permit", "drone_id": drone_id})
            else:
                resp = await client.get(f"{mod_url.rstrip('/')}/api/v1/mod/flight-requests/{drone_id}/active")

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        log.debug("fetch_active_mod_permit request error: %s", exc)

    return None
```

#### 3. Update `submit_flight_request` in `backend/app/main.py`:
**Before** (Lines 1320–1331):
```python
    mod_base = os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(f"{mod_base}/api/v1/mod/flight-requests", json=mod_payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                db.audit("flight_request_submitted", user["username"], detail=f"id={data.get('request_id')};drone={drone_id}")
                return data
    except Exception as exc:
        log.warning("MOD server unreachable: %s", exc)

    raise HTTPException(status_code=502, detail="MOD server did not accept the flight request")
```

**After**:
```python
    mod_url = os.getenv("MOD_WEBAPP_URL", os.getenv("MOD_SERVER_URL", "http://127.0.0.1:9000")).strip()
    is_gas = "script.google.com" in mod_url or mod_url.endswith("/exec")
    target_url = mod_url if is_gas else f"{mod_url.rstrip('/')}/api/v1/mod/flight-requests"
    payload_to_send = {**mod_payload, "action": "submit_request"} if is_gas else mod_payload

    try:
        # follow_redirects=True follows GAS 302 to fetch final JSON output
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(target_url, json=payload_to_send)
            if resp.status_code in (200, 201):
                data = resp.json()
                db.audit("flight_request_submitted", user["username"], detail=f"id={data.get('request_id')};drone={drone_id}")
                return data
    except Exception as exc:
        log.warning("MOD server unreachable: %s", exc)

    raise HTTPException(status_code=502, detail="MOD server did not accept the flight request")
```

---

### Part 4: Pytest Mocking Strategy Without Live Internet
To ensure automated testing succeeds offline without calling Google's live network:

1. **In Unit Tests (e.g. `backend/tests/test_flight_request_submit.py`)**:
   Tests already mock `main.httpx.AsyncClient` with `_FakeClient`. We can enhance `_FakeClient` to verify both standard and GAS parameters:
   ```python
   class _FakeClient:
       captured: dict | None = None
       async def __aenter__(self): return self
       async def __aexit__(self, *args): return False
       async def get(self, url, params=None, **kwargs):
           return _FakeResp()
       async def post(self, url, json=None, **kwargs):
           _FakeClient.captured = json
           return _FakeResp()
   ```
2. **In E2E & Scenario Tests (`tests/common.py`)**:
   Update `MockMODServerHandler` in `tests/common.py` to support Google Apps Script Web App endpoints:
   - In `do_GET`:
     If `path.endswith("/exec")` or `"action"` in query params:
     Extract `drone_id` from query parameters and return active permit.
   - In `do_POST`:
     If `path.endswith("/exec")` or `body.get("action") == "submit_request"`:
     Execute flight permission creation and return 201 JSON.
3. **Fix Date Expiration Bug in `backend/tests/test_mod_server.py`**:
   In `backend/tests/test_mod_server.py:168`:
   Change:
   `"flight_date": "2026-09-13"`
   To:
   `"flight_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")`
   This prevents the test from failing due to hardcoded past dates.

---

## 5. Verification Method

### 5.1 Verifying Login UI Adjustment (R4)
1. Inspect `frontend/src/App.tsx`:
   Check that `<span>Tài khoản:</span>` is replaced by `<span>Tên đăng nhập:</span>`.
   Check that `placeholder="pi5 hoặc tên đăng nhập"` is replaced by `placeholder="tên đăng nhập"`.
2. Build frontend:
   ```bash
   cd /home/pnt/IOT/frontend && npm run build
   ```
   Verify zero TypeScript errors and successful production build.

### 5.2 Verifying MOD Google Apps Script File (R5)
1. Inspect file existence and syntax:
   ```bash
   test -f /home/pnt/IOT/backend/mod_server.gs && node -c /home/pnt/IOT/backend/mod_server.gs
   ```
   Verify file exists and JavaScript syntax validates cleanly without errors.
2. Verify deployment guide:
   Inspect the header comments of `backend/mod_server.gs` to confirm clear step-by-step instructions for Google Apps Script deployment as a Web App with Anyone access.

### 5.3 Verifying Backend MOD_WEBAPP_URL Integration & Tests
1. Run backend unit tests with mocking:
   ```bash
   PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/pytest backend/tests/test_flight_request_submit.py
   PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/pytest backend/tests/test_gd5_window_expiry.py
   ```
   Verify 100% tests pass without requiring a live MOD server.
2. Run MOD server tests:
   ```bash
   PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest backend/tests/test_mod_server.py
   ```
   Verify test suite passes with dynamic flight dates.

---

### Invalidation Conditions
- If `follow_redirects=True` is not set on `httpx.AsyncClient`, Google Apps Script calls will fail due to unhandled HTTP 302 redirects.
- If `ENABLE_REAL_FLIGHT_COMMANDS` is set to `True`, the fail-safe safety protocol is violated.
- If Google Web App is deployed with access restricted to "Only myself", Pi5 calls without Google OAuth will be blocked.
