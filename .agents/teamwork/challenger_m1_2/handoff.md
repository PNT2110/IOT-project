# Challenger 2 Report: Milestone 1 Adversarial Probing & Stress Verification

**Agent**: `challenger_m1_2` (Challenger 2 / Adversarial Tester)  
**Parent Agent**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_2`  
**Timestamp**: 2026-10-03T21:18:00Z  
**Verdict**: **REJECT**

---

## Challenge Summary

**Overall risk assessment**: **CRITICAL**

While the asynchronous email sender in `server/app/mail.py` is robust and non-blocking, and email normalization in `server/app/security.py` satisfies core requirements with minor boundary quirks, an adversarial probe of the firmware altitude limiter in `firmware/FC_can_bang/flight_gate.h` revealed a **critical safety defect**:

When a drone breaches the altitude ceiling at apogee or in level flight where vertical speed is zero (`vspeed_mps == 0.0f`), the limiter falls back to the hardcoded `1100 µs` floor (`ALT_LIMIT_DEFAULT_FLOOR_US`). When the drone hovers above ceiling, throttle decays to 1100 µs. Because 1100 µs is far below hover throttle for an F450 frame (1400–1500 µs), and vertical dampening requires high descent velocity before providing meaningful boost, the drone experiences severe thrust loss and uncontrolled descent, re-introducing the exact defect specified in `ORIGINAL_REQUEST.md Bug 1`.

---

## 1. Observation

### 1.1 Firmware Altitude Limiter: Zero Vertical Speed Floor Collapse
- **File**: `firmware/FC_can_bang/flight_gate.h` lines 86–93:
  ```cpp
  if (min_floor_us > 0.0f) {
    s.floor_us = min_floor_us;
  } else if (vspeed_mps != 0.0f) {
    float dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US;
    s.floor_us = dynamic_base > ALT_LIMIT_DEFAULT_FLOOR_US ? dynamic_base : (float)ALT_LIMIT_DEFAULT_FLOOR_US;
  } else {
    s.floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
  }
  ```
- **File**: `firmware/FC_can_bang/MODE.ino` line 10:
  ```cpp
  throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps);
  ```
  `min_floor_us` is omitted in `MODE.ino`, so it defaults to `0.0f`.
- **Empirical Execution**: Compiled and ran `tests/firmware/test_adversarial_flight_gate.cpp`:
  ```
  === ADVERSARIAL FLIGHT GATE PROBE ===
  [PROBE 1.1] Apogee entry (vspeed=0.0m/s): cap=1470, floor_us=1100.0
    -> OBSERVED BEHAVIOR: floor_us collapsed to 1100 us despite 1500 us hover throttle!
  [PROBE 1.2] After 40s above ceiling: cap=1100 (vspeed=-0.2 m/s)
    -> OBSERVED VULNERABILITY: Capped at 1100 us (severe thrust drop / below hover on F450)!
  [PROBE 1.3] During descent at -0.35 m/s: cap=1100
    -> CONFIRMED: Descent at -0.35 m/s receives only 1100 us throttle (uncontrolled fall)!
  ```

### 1.2 Firmware Altitude Limiter: Low Throttle Coasting Entry Lock-In
- **File**: `firmware/FC_can_bang/flight_gate.h` lines 85, 118–119:
  ```cpp
  s.cap_us = (float)throttle_us - 30.0f;
  ...
  if (s.cap_us < effective_floor) s.cap_us = effective_floor;
  return throttle_us > (int)s.cap_us ? (int)s.cap_us : throttle_us;
  ```
- **Empirical Execution**:
  When a pilot cuts throttle stick to 1150 µs to arrest climb and coasts past 100m ceiling on inertia:
  ```
  [PROBE 2.1] Punch-out entry (throttle=1150 us): cap=1120, floor_us=1100.0
  [PROBE 2.2] Pilot demands 1500 us hover: returned throttle=1119
    -> OBSERVED VULNERABILITY: Output clamped to 1119 us even though pilot commanded 1500 us!
  [PROBE 2.3] Pilot demands 1800 us recovery throttle: returned throttle=1119
  ```
  The pilot's hover command (1500 µs) is locked out at 1119 µs until the drone drops > 1.0 m below ceiling (`rel_alt_m < max_alt_m - 1.0f`).

### 1.3 Firmware Altitude Limiter: Vspeed Dampening Gain Analysis
- **File**: `firmware/FC_can_bang/flight_gate.h` lines 107–113:
  ```cpp
  if (vspeed_mps < -0.4f) {
    effective_floor += (-vspeed_mps - 0.4f) * 100.0f;
    if (effective_floor > (float)throttle_us - 20.0f) {
      effective_floor = (float)throttle_us - 20.0f;
    }
  }
  ```
- If `s.floor_us` collapsed to 1100 µs:
  - At `vspeed = -1.0 m/s`, `effective_floor = 1100 + (1.0 - 0.4) * 100 = 1160 µs`
  - At `vspeed = -2.0 m/s`, `effective_floor = 1100 + (2.0 - 0.4) * 100 = 1260 µs`
  - At `vspeed = -3.0 m/s`, `effective_floor = 1100 + (3.0 - 0.4) * 100 = 1360 µs`
  Only at `vspeed = -3.4 m/s` (over 12 km/h free fall) does `effective_floor` reach 1400 µs (hover throttle).

### 1.4 Email Normalization Bypasses and Quirks
- **File**: `server/app/security.py` lines 30–39:
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
- **Empirical Execution**:
  - Trailing FQDN dot: `normalize_email("john.doe@gmail.com.")` returns `"john.doe@gmail.com."` (dot in local part NOT stripped, domain NOT mapped to `gmail.com`).
  - Upstream defense-in-depth: `RegisterRequest` in `server/app/schemas.py` uses Pydantic `EmailStr`, which rejects `"john.doe@gmail.com."` (`value is not a valid email address: An email address cannot end with a period`).
  - However, in `server/app/schemas.py` `LoginRequest`, `identifier` is a raw string (`Field(min_length=3, max_length=320)`), and CLI `bootstrap_owner` passes raw `args.email`, meaning direct calls to `normalize_email` retain the trailing dot mismatch.

### 1.5 Async Email Non-Blocking Verification
- **File**: `server/app/mail.py` lines 77–78:
  ```python
  async def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
      await asyncio.to_thread(self._send_blocking, recipient, purpose, code, sent_at)
  ```
- **Empirical Execution**: Ran `tests/scope01/test_adversarial_m1.py` (7 tests, all passed in 1.74s):
  - Injected 500ms delay in `_send_blocking`: concurrent background asyncio task recorded 40+ ticks without interruption.
  - Injected `socket.timeout`, `SMTPServerDisconnected`, `SMTPConnectError`: all exceptions caught and propagated cleanly to the caller without corrupting the event loop.
  - Task cancellation: cancelling the awaiter raises `asyncio.CancelledError` cleanly.
  - High concurrency: 25 concurrent calls executed across threads in < 0.2s without event loop starvation.

---

## 2. Logic Chain

1. **Premise 1 (Bug 1 Requirement)**: `ORIGINAL_REQUEST.md` specifically requires that the altitude limiter replace the hardcoded 1100 µs floor with a dynamic floor to prevent uncontrolled descent on heavily loaded F450 frames.
2. **Premise 2 (Sentinel In-Band Collision)**: In `flight_gate.h`, the worker attempted to preserve backward compatibility with legacy 4-argument test callers by checking `else if (vspeed_mps != 0.0f)`. The worker treated `0.0f` as an indicator that the caller did not pass `vspeed_mps`.
3. **Premise 3 (Physical Reality)**: In actual flight, `vspeed_mps` is a physical measurement from `Baro.ino`. A drone reaching ceiling at apogee or hovering level has `vspeed_mps == 0.0f`.
4. **Premise 4 (Production Invocation)**: `MODE.ino` calls `altitude_throttle_cap()` with 5 arguments, omitting `min_floor_us` (defaulting to `0.0f`).
5. **Deduction 1 (Floor Collapse)**: Whenever a drone enters the limiter at `vspeed_mps == 0.0f`, both `min_floor_us > 0.0f` and `vspeed_mps != 0.0f` are false. The code takes the `else` branch and sets `s.floor_us = 1100`.
6. **Deduction 2 (Descent Failure Mode)**: Because `s.floor_us` is only set once upon activation and never refreshed while active, if the drone lingers above the ceiling, `s.cap_us` decreases down to 1100 µs. When descent begins at gentle rates (-0.1 to -0.39 m/s), `effective_floor` remains 1100 µs, which is below hover throttle (1400–1500 µs), causing uncontrolled descent (free-fall).
7. **Deduction 3 (Safety Assessment)**: This directly re-creates the exact failure mode identified in Bug 1. Therefore, Milestone 1 cannot be approved in its current state.

---

## 3. Caveats

1. The test execution was conducted in host C++ simulation (`test_adversarial_flight_gate.cpp` compiled with `g++ -std=c++17`). This accurately reflects the exact C++ algorithm embedded in ESP32 firmware `flight_gate.h`.
2. Physical ESC response lag and barometer measurement noise in physical flight were not simulated; real flight dynamics with sensor noise near 0 m/s would make the trigger frequency of this edge case even higher.
3. No other files were investigated outside Milestone 1 scope (`flight_gate.h`, `MODE.ino`, `security.py`, `mail.py`).

---

## 4. Conclusion & Recommended Fix

### Verdict: **REJECT**

### Required Worker Fixes:
1. **Fix `flight_gate.h` and `MODE.ino` (CRITICAL)**:
   - **Option A (Recommended)**: In `MODE.ino`, pass an explicit safe floor parameter to `altitude_throttle_cap`:
     ```cpp
     #define ALT_LIMIT_SAFE_FLOOR_US 1350.0f
     throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps, ALT_LIMIT_SAFE_FLOOR_US);
     ```
   - **Option B**: In `flight_gate.h`, calculate `dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US` unconditionally whenever `s.active` transitions to `true`, unless a dedicated boolean/sentinel indicates legacy mode.
2. **Harden `normalize_email` in `security.py` (MEDIUM)**:
   - Strip trailing dots from the domain before checking against `GMAIL_DOMAINS`:
     ```python
     domain = domain.rstrip(".")
     ```

---

## 5. Verification Method

### 5.1 Independent Reproduction of Bug 1 Flaw:
```powershell
# Compile and run the adversarial flight gate probe:
powershell -Command "& 'C:\Strawberry\c\bin\g++.exe' -std=c++17 -Wall -Wextra -I firmware/FC_can_bang tests/firmware/test_adversarial_flight_gate.cpp -o test_gate.exe; & './test_gate.exe'"
```
**Expected Failure Output**:
Observe `[PROBE 1.1] Apogee entry (vspeed=0.0m/s): cap=1470, floor_us=1100.0` confirming floor collapses to 1100 µs, and `[PROBE 1.2]` confirming cap reaches 1100 µs during hover.

### 5.2 Independent Verification of Async Mail & Normalization:
```powershell
pytest tests/scope01/test_adversarial_m1.py
```
**Expected Output**:
`7 passed in 1.74s` confirming async mail sender is non-blocking and exception-safe.
