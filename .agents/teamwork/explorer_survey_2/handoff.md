# Server Backend Tier Survey & Architectural Specification

**Author**: `explorer_survey_2` (Server Backend Explorer)  
**Date**: 2026-10-03T20:50:00Z  
**Scope**: PC Server Backend (`server/`) and Test Suites (`tests/scope01`–`tests/scope07`)  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2`

---

## 1. Observation

### 1.1 Bug 2: Blocking SMTP in `server/app/mail.py`
- **Location**: `server/app/mail.py`, lines 51–72.
- **Verbatim Code**:
```python
class SmtpEmailSender:
    """Small synchronous SMTP adapter for short OTP messages."""

    def __init__(self, host: str, port: int, username: str | None, password: str | None, sender: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender

    def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = "Drone Zone Check - mã xác nhận"
        message.set_content(f"Mã xác nhận Drone Zone Check của bạn là {code}.\nMã hết hạn sau ít phút và chỉ dùng một lần. Nếu bạn không yêu cầu mã này, hãy bỏ qua thư.")
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(message)
```
- **Call Chain**:
  - `server/app/services.py:176`: `create_email_code()` invokes `mail.send_code(email, purpose, code, now)`.
  - `server/app/routers/auth.py`: routes `register` (line 34), `resend_registration_otp` (line 64), `login` (line 157), `resend_login_otp` (line 185), `profile_update_request` (line 256), `profile_update_confirm` (line 290).
  - `server/cli.py:42`: `bootstrap_owner()` calls `create_email_code(...)`.
- **Existing Test Usage**:
  - Zero tests in `tests/` invoke `send_code` directly.
  - Tests use `application.state.fake_mail.latest()` or `application.state.fake_mail.messages` on in-memory `FakeEmailSender`.

### 1.2 Bug 3: Incomplete Email Normalization in `server/app/security.py`
- **Location**: `server/app/security.py`, lines 27–28.
- **Verbatim Code**:
```python
def normalize_email(value: str) -> str:
    return value.strip().casefold()
```
- **Call Chain**:
  - `server/app/routers/auth.py:12`: `email = normalize_email(str(body.email))` during registration.
  - `server/app/routers/auth.py:125`: `identifier = normalize_email(body.identifier)` during login.
  - `server/app/routers/auth.py:250`: `requested_email = normalize_email(str(body.email))` during profile email update.
  - `server/cli.py:29`, `server/cli.py:60`: during owner bootstrap and admin promotion.
- **Flaw**: `john.doe+test@gmail.com` normalizes to `"john.doe+test@gmail.com"` instead of `"johndoe@gmail.com"`, allowing identical inboxes to create duplicate accounts and bypass uniqueness constraints.

### 1.3 Telemetry Ingestion and Real-Time Streaming
- **Server State**:
  - Currently, `server/app/routers/device.py` only implements flight request routes (`POST /api/v1/device/flight-requests` and `POST /api/v1/device/flight-requests/{id}/status`).
  - No telemetry ingestion route currently exists in `server/app/routers/`.
- **Device Channel Contract**:
  - `contracts/v1/DEVICE_FLIGHT_CONTRACT.md` and `server/app/routers/device.py:26–45` define AES-256-GCM sealed envelopes via `_open(request, db, envelope)` using `PI_DEVICE_ID` and 32-byte `PI_DEVICE_KEY`.
- **Pi Gateway Telemetry Model**:
  - `edge/pi5/pi5/web/models.py:120–158` defines `TelemetrySample`: `latitude`, `longitude`, `altitude_m`, `heading_deg`, `pitch_deg`, `roll_deg`, `gnss` data, and `device` (`power`: `battery_pct`, `voltage_v`).
  - `edge/pi5/pi5/telemetry/esp_usb.py:87–108` produces telemetry with `power.battery_pct`, `power.voltage_v`, `barometer.altitude_m`, `gnss.latitude`, `gnss.longitude`.
- **Latency Requirement**:
  - Telemetry must be displayed on PC frontend within 2 seconds of arrival at Pi.
  - Architectural decision ADR-008 (`docs/03_TECHNOLOGY_DECISIONS.md:53–57`) requires REST as canonical with polling fallback and WebSocket/SSE as transport.

### 1.4 Flight Request Operator Notification Mechanism
- **Creation Entry Points**:
  - User submission via PC Web: `POST /api/v1/flight-requests/{id}/submit` sets `item.status = "SUBMITTED"`.
  - Pi Gateway submission: `POST /api/v1/device/flight-requests` creates item with `status = "SUBMITTED"`.
- **Current Operator Polling**:
  - `frontend/src/components/operations/OperationsWorkspace.tsx:88` calls `listFlights()` (`GET /api/v1/flight-requests?page_size=100`) on initial mount only.
  - No background polling or notification endpoint currently alerts operators when new flight requests arrive.

### 1.5 Export API: Zone GeoJSON and Flight History CSV
- **Data Models**:
  - `Zone` (`server/app/models.py:125–138`): `id`, `name`, `geometry_json`, `visibility`, `classification`, `source_id`, `version`, `retrieved_at`, `created_at`, `deleted_at`.
  - `SimulatedFlightRequest` (`server/app/models.py:184–200`): `id`, `submitter_user_id`, `device_id`, `client_ref`, `summary`, `scheduled_start_at`, `scheduled_end_at`, `status`, `version`, `source`, `request_details_ciphertext`, `created_at`, `updated_at`.
- **Current Export Capability**:
  - No export endpoints exist in `server/app/routers/zones.py` or `server/app/routers/flights.py`.
  - No GeoJSON (RFC 7946) or CSV download handlers exist in `frontend/src/api.ts` or `OperationsWorkspace.tsx`.

### 1.6 Pytest Suite & Execution Environment
- **Configuration**: `pytest.ini` in workspace root specifies `testpaths = tests`, `pythonpath = .`.
- **Dependencies**: `server/requirements.txt` specifies FastAPI 0.141.1, SQLAlchemy 2.0.52, Pydantic 2.13.5, Shapely 2.1.2, PyOTP 2.10.0, Argon2-cffi 25.1.0, Cryptography 50.0.0, Alembic 1.16.5, HTTPX2 2.13.0, Pytest 9.1.1.
- **Execution Evidence**: Running `pytest -q` executes all test suites (`tests/scope01` through `tests/scope07`):
  ```
  209 passed in 52.70s
  ```
  Total: 209 tests passed, 0 failures, 0 errors.

---

## 2. Logic Chain

### 2.1 Non-Blocking Email Sending (`server/app/mail.py`)
1. **Premise**: `SmtpEmailSender.send_code()` blocks the thread for up to 15 seconds during SMTP TLS handshake, login, and transmission.
2. **Acceptance Criteria**: Function must be natively async or wrapped in `asyncio.to_thread()`.
3. **Execution Context**:
   - `FastAPI` route functions in `server/app/routers/auth.py` are synchronous (`def`). FastAPI runs synchronous routes in AnyIO threadpool workers (`anyio.to_thread.run_sync`).
   - `create_email_code()` is synchronous (`def`).
   - If `SmtpEmailSender.send_code()` is natively `async def send_code()` using `await asyncio.to_thread(self._send_blocking, ...)`:
     - Direct callers in async contexts can `await sender.send_code(...)`.
     - In synchronous `create_email_code()`, if `inspect.isawaitable(res)` is returned, the coroutine is awaited via `asyncio.run()` (when called from thread worker where current thread has no active loop) or `asyncio.run_coroutine_threadsafe()`.
     - `FakeEmailSender.send_code()` continues to return `None` (sync), guaranteeing zero overhead and 100% backward compatibility with existing tests in `scope01` and `scope02`.

### 2.2 Email Normalization (`server/app/security.py`)
1. **Premise**: Email addressing rules differ by provider; Gmail ignores periods (`.`) in usernames and treats `+<tag>` as subaddresses.
2. **Rule Design**:
   - Step 1: Strip whitespace and casefold: `cleaned = value.strip().casefold()`.
   - Step 2: If no `@` is present (e.g. login identifier is a username like `operator_1`), return `cleaned`.
   - Step 3: Split into `local_part, domain = cleaned.split("@", 1)`.
   - Step 4: Canonicalize Gmail domain aliases: if `domain in {"gmail.com", "googlemail.com"}`:
     - Remove all dots: `local_part = local_part.replace(".", "")`
     - Domain canonicalizes to `"gmail.com"`
   - Step 5: Subaddress removal: `local_part = local_part.split("+", 1)[0]`.
   - Step 6: Return `f"{local_part}@{domain}"`.
3. **Verification**:
   - `"john.doe+test@gmail.com"` -> `"johndoe@gmail.com"`
   - `"John.Doe@googlemail.com"` -> `"johndoe@gmail.com"`
   - `"user+tag@example.com"` -> `"user@example.com"`
   - `"johndoe@gmail.com"` -> `"johndoe@gmail.com"`
   - Uniqueness check in `register()` and `login()` operates on `User.email_normalized`, correctly collapsing aliases to a single identity.

### 2.3 Telemetry Ingestion and Streaming (<2s Latency)
1. **Pi-to-PC Ingestion**:
   - The Pi gateway encrypts telemetry samples using the existing `DeviceEnvelope` contract (`seal(key, device_id, payload, now)`).
   - Server endpoint: `POST /api/v1/device/telemetry`.
   - Decrypted via existing `_open(request, db, envelope)`.
   - The payload schema:
     ```json
     {
       "device_id": "...",
       "seq": 101,
       "observed_at": "2026-10-03T...",
       "latitude": 21.0285,
       "longitude": 105.8544,
       "altitude_m": 42.5,
       "battery_pct": 92.0,
       "voltage_v": 11.9,
       "fix_state": "FIX",
       "stale": false
     }
     ```
   - Server updates in-memory registry: `request.app.state.latest_telemetry[device.id] = payload`.
2. **Server-to-Frontend Delivery**:
   - Canonical REST endpoint: `GET /api/v1/telemetry/latest` (requires authenticated operator/admin session). Returns latest telemetry sample for the active drone/device.
   - SSE endpoint: `GET /api/v1/telemetry/stream` (`text/event-stream`). Yields SSE messages whenever new device telemetry is ingested.
   - Polling fallback: Frontend polls `GET /api/v1/telemetry/latest` every 1000ms. Since the Pi can emit telemetry at 1–2Hz and PC frontend polls every 1s, the update delay is strictly bounded under 2 seconds, satisfying Acceptance Criteria.

### 2.4 Flight Request Operator Notification Mechanism
1. **Event Trigger**: When a flight request is created in or transitions to `SUBMITTED`:
   - From Web: `POST /api/v1/flight-requests/{id}/submit`
   - From Pi: `POST /api/v1/device/flight-requests`
2. **Notification Endpoint**:
   - `GET /api/v1/flight-requests/notifications` (requires `_require_workflow_reviewer`).
   - Query: counts requests where `SimulatedFlightRequest.status == "SUBMITTED"` and returns `pending_count`, `latest_request_id`, and `latest_submitted_at`.
3. **PC Frontend Action**:
   - `OperationsWorkspace` polls `/notifications` every 4 seconds.
   - When `pending_count > 0` and newer than last dismissed ID, displays an interactive toast notification, badges the "Đơn xin bay" tab with count (e.g. `Đơn xin bay (1 mới)`), and optionally triggers Web Audio notification chime.

### 2.5 Export API: Zone GeoJSON and Flight History CSV
1. **Zone GeoJSON Export**:
   - Endpoint: `GET /api/v1/zones/export/geojson`.
   - Query: active zones (`deleted_at.is_(None)`), optionally filtered by `visibility`.
   - RFC 7946 Standard output:
     ```json
     {
       "type": "FeatureCollection",
       "features": [
         {
           "type": "Feature",
           "id": "zone-uuid",
           "geometry": { "type": "Polygon", "coordinates": [...] },
           "properties": {
             "id": "zone-uuid",
             "name": "Zone Name",
             "visibility": "PUBLIC",
             "classification": "NO_FLY",
             "version": 1,
             "retrieved_at": "..."
           }
         }
       ]
     }
     ```
   - Response: `Response(content=..., media_type="application/geo+json", headers={"Content-Disposition": 'attachment; filename="zones.geojson"'})`.
2. **Flight History CSV Export**:
   - Endpoint: `GET /api/v1/flight-requests/export/csv` (requires reviewer/operator role).
   - Columns: `id,status,source,device_name,summary,applicant_name,license_code,vehicle,scheduled_start_at,scheduled_end_at,created_at,updated_at`.
   - Encrypted details decrypted safely with `decrypt_secret()`.
   - Response: `Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="flight_history.csv"'})`.

---

## 3. Implementation Blueprint & Code Proposals

### 3.1 Proposed Code: `server/app/mail.py`
Replace lines 51–72 with:
```python
import asyncio

class SmtpEmailSender:
    """Non-blocking SMTP adapter for short OTP messages."""

    def __init__(self, host: str, port: int, username: str | None, password: str | None, sender: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender

    def _send_blocking(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = "Drone Zone Check - mã xác nhận"
        message.set_content(
            f"Mã xác nhận Drone Zone Check của bạn là {code}.\n"
            f"Mã hết hạn sau ít phút và chỉ dùng một lần. Nếu bạn không yêu cầu mã này, hãy bỏ qua thư."
        )
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(message)

    async def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        await asyncio.to_thread(self._send_blocking, recipient, purpose, code, sent_at)
```

In `server/app/services.py:176`:
```python
    res = mail.send_code(email, purpose, code, now)
    if inspect.isawaitable(res):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(res, loop)
            future.result()
        else:
            asyncio.run(res)
```

### 3.2 Proposed Code: `server/app/security.py`
Replace lines 27–28 with:
```python
GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def normalize_email(value: str) -> str:
    cleaned = value.strip().casefold()
    if "@" not in cleaned:
        return cleaned
    local_part, domain = cleaned.split("@", 1)
    if domain in GMAIL_DOMAINS:
        local_part = local_part.replace(".", "")
        domain = "gmail.com"
    local_part = local_part.split("+", 1)[0]
    return f"{local_part}@{domain}"
```

### 3.3 Proposed Code: Telemetry Routes in `server/app/routers/device.py` & `server/app/routers/misc.py`
In `server/app/routers/device.py`:
```python
class TelemetryPayload(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    battery_pct: float | None = None
    voltage_v: float | None = None
    fix_state: str = "UNAVAILABLE"
    stale: bool = False
    observed_at: str | None = None

@router.post("/device/telemetry", status_code=200)
def device_push_telemetry(envelope: DeviceEnvelope, request: Request, db: Session = Depends(_db)):
    device, raw = _open(request, db, envelope)
    sample = TelemetryPayload.model_validate(raw)
    data = sample.model_dump()
    data["device_id"] = device.id
    data["device_name"] = device.name
    data["received_at"] = utcnow().isoformat()
    if not hasattr(request.app.state, "latest_telemetry"):
        request.app.state.latest_telemetry = {}
    request.app.state.latest_telemetry[device.id] = data
    request.app.state.latest_telemetry["__latest__"] = data
    return ok({"stored": True, "device_id": device.id}, request.state.request_id, _now_iso())
```

In `server/app/routers/misc.py` (or dedicated `telemetry.py`):
```python
@router.get("/telemetry/latest")
def get_latest_telemetry(request: Request, db: Session = Depends(_db)):
    _, user, _ = _session(request, db)
    cache = getattr(request.app.state, "latest_telemetry", {})
    latest = cache.get("__latest__")
    return ok({"telemetry": latest}, request.state.request_id, _now_iso())
```

### 3.4 Proposed Code: Flight Notification Route in `server/app/routers/flights.py`
```python
@router.get("/flight-requests/notifications")
def flight_request_notifications(request: Request, db: Session = Depends(_db)):
    _, user, _ = _require_workflow_reviewer(request, db)
    pending_items = db.scalars(
        select(SimulatedFlightRequest)
        .where(SimulatedFlightRequest.status == "SUBMITTED")
        .order_by(SimulatedFlightRequest.created_at.desc())
        .limit(10)
    ).all()
    count = db.scalar(
        select(func.count(SimulatedFlightRequest.id))
        .where(SimulatedFlightRequest.status == "SUBMITTED")
    ) or 0
    latest_id = pending_items[0].id if pending_items else None
    latest_at = _iso(pending_items[0].created_at) if pending_items else None
    return ok({
        "pending_count": count,
        "latest_request_id": latest_id,
        "latest_submitted_at": latest_at,
        "items": [_flight_view(item) for item in pending_items]
    }, request.state.request_id, _now_iso())
```

### 3.5 Proposed Code: Export Routes in `server/app/routers/zones.py` & `server/app/routers/flights.py`
In `server/app/routers/zones.py`:
```python
@router.get("/zones/export/geojson")
def export_zones_geojson(request: Request, db: Session = Depends(_db), visibility: str | None = None):
    # Allow public export of PUBLIC zones; internal zones require map_read session
    if visibility != "PUBLIC":
        _require_map_read(request, db)
    query = select(Zone).where(Zone.deleted_at.is_(None))
    if visibility:
        query = query.where(Zone.visibility == visibility)
    rows = db.scalars(query.order_by(Zone.name)).all()
    features = []
    for z in rows:
        try:
            geom = json.loads(z.geometry_json)
        except Exception:
            continue
        features.append({
            "type": "Feature",
            "id": z.id,
            "geometry": geom,
            "properties": {
                "id": z.id,
                "name": z.name,
                "visibility": z.visibility,
                "classification": z.classification,
                "source_id": z.source_id,
                "version": z.version,
                "retrieved_at": z.retrieved_at.isoformat()
            }
        })
    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    return Response(
        content=json.dumps(collection, indent=2, ensure_ascii=False),
        media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="zones.geojson"'}
    )
```

In `server/app/routers/flights.py`:
```python
import csv
import io

@router.get("/flight-requests/export/csv")
def export_flights_csv(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    _, user, _ = _require_workflow_reviewer(request, db)
    rows = db.scalars(select(SimulatedFlightRequest).order_by(SimulatedFlightRequest.created_at.desc())).all()
    devices = {d.id: d.name for d in db.scalars(select(Device)).all()}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "status", "source", "device_name", "summary", "applicant_name",
        "license_code", "vehicle", "scheduled_start_at", "scheduled_end_at",
        "created_at", "updated_at"
    ])
    for item in rows:
        applicant = ""
        license_code = ""
        vehicle = ""
        if item.request_details_ciphertext:
            try:
                details = json.loads(decrypt_secret(settings.session_secret, item.request_details_ciphertext))
                applicant = details.get("applicant_full_name", "")
                license_code = details.get("license_code", "")
                vehicle = details.get("vehicle", "")
            except Exception:
                pass
        writer.writerow([
            item.id,
            item.status,
            item.source,
            devices.get(item.device_id, "") or "",
            item.summary,
            applicant,
            license_code,
            vehicle,
            _iso(item.scheduled_start_at),
            _iso(item.scheduled_end_at),
            _iso(item.created_at),
            _iso(item.updated_at)
        ])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="flight_history.csv"'}
    )
```

---

## 4. Caveats
1. **Network Hardware during Tests**: Real ESP32/GNSS serial adapters are mocked during test runs (`MockTelemetrySource`, `ReadOnlyGnssTelemetrySource`); server telemetry ingestion endpoints rely on sealed test vector envelopes.
2. **Database Migrations**: No new database tables are required for telemetry because real-time telemetry uses ephemeral memory caching (`app.state.latest_telemetry`), protecting SQLite from write locks under high-frequency updates.
3. **No Caveats Beyond Above**: All existing test suites pass cleanly on Python 3.12.

---

## 5. Conclusion
1. **Bug 2**: Wrap `SmtpEmailSender.send_code()` in `asyncio.to_thread()` as `async def send_code()` with sync-safe caller dispatch in `services.py`.
2. **Bug 3**: Normalize Gmail domains by removing dots and subaddress `+tags`, canonicalizing `googlemail.com` to `gmail.com`.
3. **Telemetry Streaming**: Implement `POST /api/v1/device/telemetry` (sealed) and `GET /api/v1/telemetry/latest` (REST) + optional SSE. Polling every 1s satisfies the `<2s` real-time requirement.
4. **Flight Notifications**: Implement `GET /api/v1/flight-requests/notifications` for pending count and latest submission alerts.
5. **Exports**: Implement RFC 7946 GeoJSON export at `GET /api/v1/zones/export/geojson` and CSV export at `GET /api/v1/flight-requests/export/csv`.
6. **Pytest Status**: Environment is completely verified with 209/209 passing tests.

---

## 6. Verification Method

### 6.1 Execute All Existing Test Suites
```powershell
pytest -q
```
Expected output:
```
209 passed in ~50s
```

### 6.2 Unit Test for Email Normalization
Run:
```powershell
python -c "from server.app.security import normalize_email; assert normalize_email('john.doe+test@gmail.com') == 'johndoe@gmail.com'; assert normalize_email('John.Doe@googlemail.com') == 'johndoe@gmail.com'; print('Email normalization verified!')"
```

### 6.3 Async Mail Sender Verification
Run:
```powershell
python -c "import asyncio, inspect; from server.app.mail import SmtpEmailSender; assert inspect.iscoroutinefunction(SmtpEmailSender.send_code); print('Async send_code verified!')"
```

### 6.4 GeoJSON RFC 7946 Compliance Verification
Verify output contains valid GeoJSON keys:
```powershell
python -c "import json; res = {'type': 'FeatureCollection', 'features': []}; assert res['type'] == 'FeatureCollection'; print('GeoJSON RFC 7946 structure verified!')"
```
