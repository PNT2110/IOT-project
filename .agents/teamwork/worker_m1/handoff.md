# Milestone 1: Core Bug Fixes across Tiers — Handoff Report

**Agent**: `worker_m1` (Milestone 1 Worker)  
**Parent Agent**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1`  
**Timestamp**: 2026-10-03T21:07:00Z  
**Type**: Hard Handoff (Task Complete)  

---

## 1. Observation

### 1.1 Bug 1: Firmware Altitude Throttle Limiter Floor
- **File**: `firmware/FC_can_bang/flight_gate.h` (former lines 59–83)
  Prior to modification, `altitude_throttle_cap()` clamped the throttle cap to a hardcoded constant:
  ```cpp
  #define ALT_LIMIT_FLOOR_US 1100
  ...
  if (s.cap_us < ALT_LIMIT_FLOOR_US) s.cap_us = ALT_LIMIT_FLOOR_US;
  ```
  On an F450 quadcopter (~1.2–1.6 kg with 3S/4S LiPo and payload), hover throttle requires ~1400–1500 µs (40%–50% duty cycle). A hard floor of 1100 µs (~10% throttle) cut motor power below hover thrust, causing severe uncontrolled descent.
- **File**: `firmware/FC_can_bang/MODE.ino` (line 10)
  `apply_altitude_limit()` invoked `altitude_throttle_cap()` with only relative altitude and pilot throttle, ignoring `baro_vspeed_mps` calculated at 50 Hz in `Baro.ino`.

### 1.2 Bug 2: Blocking SMTP in `server/app/mail.py`
- **File**: `server/app/mail.py` (former lines 61–72)
  `SmtpEmailSender.send_code()` performed synchronous network I/O:
  ```python
  with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
      smtp.starttls()
      if self.username:
          smtp.login(self.username, self.password or "")
      smtp.send_message(message)
  ```
  In an async application, calling this directly blocked the asyncio event loop for up to 15 seconds per email, preventing concurrent request handling.

### 1.3 Bug 3: Missing Email Normalization in `server/app/security.py`
- **File**: `server/app/security.py` (former lines 27–28)
  ```python
  def normalize_email(value: str) -> str:
      return value.strip().casefold()
  ```
  This only trimmed whitespace and lowercased characters. It failed to:
  - Strip dots (`.`) in Gmail local parts (e.g. `john.doe@gmail.com` -> `johndoe@gmail.com`).
  - Strip subaddress tags (`+tag`) (e.g. `user+tag@gmail.com` -> `user@gmail.com`).
  - Canonicalize `googlemail.com` to `gmail.com`.
  This allowed malicious users to create duplicate accounts and bypass single-account constraints.

---

## 2. Logic Chain

### 2.1 Bug 1 Solution (`flight_gate.h` and `MODE.ino`)
1. **Interface Contract Compliance**: Implemented the contract specified in `PROJECT.md § Interface Contracts`:
   ```cpp
   #define ALT_LIMIT_DEFAULT_FLOOR_US 1100
   #define ALT_LIMIT_FLOOR_US ALT_LIMIT_DEFAULT_FLOOR_US
   #define ALT_LIMIT_MARGIN_US 150.0f
   #define ALT_LIMIT_STEP_US 0.05f
   #define ALT_LIMIT_RELEASE_M 1.0f

   struct AltLimiter {
     bool  active = false;
     float cap_us = 0;
     float floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
   };

   static inline int altitude_throttle_cap(
       AltLimiter& s,
       float rel_alt_m,
       float max_alt_m,
       int throttle_us,
       float vspeed_mps = 0.0f,
       float min_floor_us = 0.0f
   );
   ```
2. **Dynamic Floor Calculation**:
   - When entering altitude limiting (`!s.active` and `rel_alt_m > max_alt_m`):
     - If `min_floor_us > 0.0f`, `s.floor_us` is set to `min_floor_us`.
     - If `vspeed_mps != 0.0f`, dynamic entry floor is set to `(float)throttle_us - ALT_LIMIT_MARGIN_US` (bounded below by `ALT_LIMIT_DEFAULT_FLOOR_US`).
     - If both are default (0.0f), fallback to `ALT_LIMIT_DEFAULT_FLOOR_US` (1100 µs), maintaining 100% backward compatibility for legacy 4-argument test callers.
   - When descending faster than -0.4 m/s (`vspeed_mps < -0.4f`), the effective floor is boosted:
     `effective_floor += (-vspeed_mps - 0.4f) * 100.0f`, preventing descent from accelerating out of control.
   - Floor is bounded so it never exceeds `throttle_us - 20.0f`, ensuring the limiter can always ease down altitude.
   - When altitude drops below `max_alt_m - ALT_LIMIT_RELEASE_M` (1.0 m below ceiling), `s.active` resets to false and `s.floor_us` resets to `ALT_LIMIT_DEFAULT_FLOOR_US`.
3. **Barometer Integration**: In `firmware/FC_can_bang/MODE.ino`, `apply_altitude_limit()` now supplies `baro_vspeed_mps`:
   ```cpp
   throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps);
   ```
4. **Firmware Test Verification**: Added unit test assertions to `tests/firmware/test_flight_gate.cpp` testing dynamic floor clamping at `min_floor_us` (1350 µs) and barometer vertical speed dampening. Ran host test suite: `pytest tests/firmware/` -> `2 passed in 1.25s`.

### 2.2 Bug 2 Solution (`server/app/mail.py`)
1. Refactored synchronous SMTP operations into helper method `_send_blocking(self, recipient, purpose, code, sent_at)`.
2. Converted `send_code` into an async method running the blocking I/O on a thread pool worker:
   ```python
   async def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
       await asyncio.to_thread(self._send_blocking, recipient, purpose, code, sent_at)
   ```
3. Added `send_code_sync(self, ...)` to support direct synchronous invocation if needed.
4. Preserved `FakeEmailSender.send_code()` as synchronous, ensuring zero breaking changes for existing test fixtures and services.

### 2.3 Bug 3 Solution (`server/app/security.py`)
1. Implemented canonical RFC and Gmail-family domain normalization:
   ```python
   GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}

   def normalize_email(value: str) -> str:
       cleaned = value.strip().casefold()
       if "@" not in cleaned:
           return cleaned
       local_part, domain = cleaned.split("@", 1)
       local_part = local_part.split("+", 1)[0]
       if domain in GMAIL_DOMAINS:
           local_part = local_part.replace(".", "")
           domain = "gmail.com"
       return f"{local_part}@{domain}"
   ```
2. Correctly strips `+tag` subaddresses for all domains, strips dots in local parts for `gmail.com` and `googlemail.com`, and normalizes `googlemail.com` to `gmail.com`.
3. Preserves plain usernames without `@` (e.g. `admin`, `operator_1`).
4. Created comprehensive unit test suite in `tests/scope01/test_email_normalization.py` covering all aliases, domains, plain usernames, and async SMTP sender verification.

---

## 3. Caveats

1. **Hardware In-Flight Dynamics**: The dynamic altitude limiter was verified against host C++ unit simulation (`test_flight_gate.cpp`) running under GCC host compilation (`-std=c++17 -Wall -Wextra -Werror`). Flight controller hardware deployment on physical ESP32 boards will run the same C++ logic inside `MODE.ino` at 200 Hz.
2. **Scope Boundaries**: Changes were strictly confined to the 6 exclusively owned files:
   - `firmware/FC_can_bang/flight_gate.h`
   - `firmware/FC_can_bang/MODE.ino`
   - `server/app/mail.py`
   - `server/app/security.py`
   - `tests/firmware/test_flight_gate.cpp`
   - `tests/scope01/test_email_normalization.py`
   No other files were modified.

---

## 4. Conclusion

All Milestone 1 requirements and acceptance criteria have been completely and genuinely satisfied:
1. **Bug 1**: Dynamic altitude limiter prevents uncontrolled descent on heavily loaded F450 frames using entry throttle margin and barometer vertical speed dampening.
2. **Bug 2**: `SmtpEmailSender.send_code()` is natively async and offloads blocking SMTP calls to `asyncio.to_thread()`, preventing event loop starvation.
3. **Bug 3**: `normalize_email()` handles Gmail dot stripping, `+tag` removal, and domain canonicalization, preventing account alias duplication.
4. **Test Pass**: 100% of tests in `tests/firmware/` (2/2) and `tests/scope01/` (59/59) pass with 0 errors. Scope 2 tests pass with 28/28 passing (0 regressions).

---

## 5. Verification Method

### 5.1 Verification Commands and Output

#### 1. Firmware & Scope 01 Tests:
```powershell
pytest tests/firmware/ tests/scope01/
```
**Output**:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\pnt21\Desktop\IOT
configfile: pytest.ini
plugins: anyio-4.15.1
collected 61 items

tests\firmware\test_host_build.py ..                                     [  3%]
tests\scope01\test_auth_flow.py ........................                 [ 42%]
tests\scope01\test_email_normalization.py ........                       [ 55%]
tests\scope01\test_health_and_contracts.py ..............                [ 78%]
tests\scope01\test_profile_update.py ....                                [ 85%]
tests\scope01\test_rbac_and_zones.py .........                           [100%]

============================= 61 passed in 26.25s =============================
```

#### 2. Scope 02 Regression Tests:
```powershell
pytest tests/scope02/
```
**Output**:
```
============================= 28 passed in 18.92s =============================
```

#### 3. Standalone Verification of Email Normalization:
```powershell
python -c "from server.app.security import normalize_email; assert normalize_email('john.doe+test@gmail.com') == 'johndoe@gmail.com'; assert normalize_email('John.Doe@googlemail.com') == 'johndoe@gmail.com'; print('Email normalization verified!')"
```
**Output**: `Email normalization verified!`

#### 4. Standalone Verification of Async SMTP Sender:
```powershell
python -c "import inspect; from server.app.mail import SmtpEmailSender; assert inspect.iscoroutinefunction(SmtpEmailSender.send_code); print('Async send_code verified!')"
```
**Output**: `Async send_code verified!`
