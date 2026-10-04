# Milestone 1: Empirical Verification & Stress Test — Handoff Report

**Agent**: `challenger_m1_1` (Simulation & Stress Verifier)  
**Parent Agent**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_1`  
**Timestamp**: 2026-10-04T04:22:00Z  
**Type**: Hard Handoff (Task Complete)  
**Verdict**: **REJECT**

---

## 1. Observation

### 1.1 Firmware Altitude Limiter (`firmware/FC_can_bang/flight_gate.h` and `MODE.ino`)

1. **Observation 1.1 — Level-Off Apogee Entry Collapses Floor to 1100 µs**:
   In `firmware/FC_can_bang/flight_gate.h` lines 86–93:
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
   In `firmware/FC_can_bang/MODE.ino` line 10:
   ```cpp
   throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps);
   ```
   `MODE.ino` invokes `altitude_throttle_cap` without `min_floor_us`, which defaults to `0.0f`.
   When an F450 drone climbs to ceiling `max_altitude_m` and levels off or reaches apogee (`baro_vspeed_mps == 0.0f`):
   The condition `vspeed_mps != 0.0f` evaluates to `false`.
   `s.floor_us` is assigned `ALT_LIMIT_DEFAULT_FLOOR_US` (1100 µs).
   **Empirical Run**:
   Compiled and executed `tests/firmware/test_altitude_limiter_stress.cpp`:
   ```
   [VULNERABILITY 1 CONFIRMED] Level-off ceiling entry (vspeed=0) resets floor_us to 1100 us!
   ```
   After 40 seconds above ceiling (e.g. gentle thermal/updraft), `s.cap_us` decays from 1470 µs to 1100 µs. When descent begins at -0.5 m/s, `effective_floor` only adds 10 µs -> 1110 µs, which is 340 µs below hover throttle (~1450 µs), causing severe uncontrolled descent.

2. **Observation 1.2 — High Climb Punch-Out Locks Floor Above Hover**:
   When entering the ceiling during a climb at high throttle (e.g. `throttle_us = 1850`, `vspeed_mps = +4.0 m/s`), line 89 computes:
   `dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US = 1850.0f - 150.0f = 1700.0f`.
   `s.floor_us` is locked at 1700.0 µs.
   **Empirical Run**:
   In `tests/firmware/test_altitude_limiter_stress.cpp`:
   ```
   [VULNERABILITY 2 CONFIRMED] High climb entry locks throttle floor at 1700 us (> 1450 hover)!
                                Drone will climb indefinitely above ceiling!
   ```
   Even after 2 minutes above ceiling, `s.cap_us` cannot decay below `s.floor_us` (1700 µs). At 1700 µs, an F450 drone produces continuous climbing thrust, defeating the upper altitude ceiling entirely.

3. **Observation 1.3 — Line 110 Depresses Effective Floor Below `min_floor` During Descent**:
   In `firmware/FC_can_bang/flight_gate.h` lines 107–113:
   ```cpp
   if (vspeed_mps < -0.4f) {
     effective_floor += (-vspeed_mps - 0.4f) * 100.0f;
     if (effective_floor > (float)throttle_us - 20.0f) {
       effective_floor = (float)throttle_us - 20.0f;
     }
   }
   ```
   When `min_floor_us` is configured (e.g. 1450 µs) and the pilot holds throttle near hover (e.g. 1460 µs), during descent at -1.0 m/s:
   Line 110 clamps `effective_floor` to `1460.0f - 20.0f = 1440.0f`.
   **Empirical Run**:
   In `tests/firmware/test_altitude_limiter_stress.cpp`:
   ```
   [VULNERABILITY 3 CONFIRMED] Rapid descent (-1.0 m/s) depresses throttle cap to 1440 us (< min_floor 1450 us)!
   ```
   The throttle cap drops below the configured `min_floor` (1450 µs) when descending rapidly.

---

### 1.2 Bug 2: Async Email (`server/app/mail.py`)

- `SmtpEmailSender.send_code` is defined as:
  ```python
  async def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
      await asyncio.to_thread(self._send_blocking, recipient, purpose, code, sent_at)
  ```
- **Empirical Run**: Executed `tests/scope01/test_smtp_concurrency_stress.py`:
  - 50 concurrent email dispatches executed in 0.28s (vs 2.50s sequential).
  - Background 5ms event loop ticker recorded jitter < 50ms (0 event loop starvation).
  - 100 concurrent dispatches passed with 100% completion.
  - SMTP socket exceptions propagated cleanly.
  - Test suite result: `4 passed in 2.46s`.
- **Integration Warning**: `server/app/services.py:176` (`create_email_code`) is synchronous and calls `mail.send_code(email, purpose, code, now)` without `await`. When `SmtpEmailSender` is active in production, this generates a `RuntimeWarning: coroutine 'SmtpEmailSender.send_code' was never awaited` and email delivery fails silently. (Must be coordinated for Milestone 2).

---

### 1.3 Bug 3: Email Normalization (`server/app/security.py`)

- `normalize_email` handles casefolding, subaddress `+tag` stripping, dot-stripping on Gmail/Googlemail, and username passthrough.
- **Empirical Run**: Executed `tests/scope01/test_email_normalization_stress.py`:
  - Tested Unicode casefold (Turkish dotted I `İ`, German `ß`, Greek uppercase).
  - Tested Unicode whitespace (`\u00a0`, `\u2003`, `\u3000`).
  - Tested subaddress combinations (`user+tag1+tag2+tag3`, `user++tag`).
  - Tested consecutive and leading/trailing dots.
  - Tested 5,000 fuzzed inputs: zero unhandled exceptions or crashes.
  - Test suite result: `7 passed in 0.10s`.

---

## 2. Logic Chain

1. **Bug 1 Goal**: `ORIGINAL_REQUEST.md` states:
   *"The `altitude_throttle_cap()` function reduces throttle to a hard floor of 1100 µs (`ALT_LIMIT_FLOOR_US`). For a heavily loaded F450 drone, 1100 µs is below hover throttle, causing uncontrolled descent. ... The altitude limiter must prevent uncontrolled descent without disabling altitude limiting entirely."*
2. **Interface Contract Limitation**:
   The worker implemented `else if (vspeed_mps != 0.0f)` to satisfy legacy 4-argument unit tests where `vspeed_mps` defaulted to `0.0f`.
3. **Flaw Mechanism 1**:
   In physical flight, a drone reaching ceiling often levels off at zero vertical speed (`vspeed_mps == 0.0f`). Because `vspeed_mps != 0.0f` is false, `s.floor_us` is assigned 1100 µs. If the drone hovers above ceiling for >35s, the throttle cap decays to 1100 µs. When descent begins, the floor fails to protect hover thrust, causing uncontrolled fall.
4. **Flaw Mechanism 2**:
   If entering ceiling while climbing at 1850 µs throttle, `dynamic_base` is `1850 - 150 = 1700 µs`. The floor is permanently locked at 1700 µs. Since hover is ~1450 µs, 1700 µs creates sustained upward acceleration; the drone can never return to ceiling.
5. **Flaw Mechanism 3**:
   Line 110 blindly caps `effective_floor` at `throttle_us - 20.0f`. When descending, if pilot throttle is within 20 µs of `min_floor`, `effective_floor` drops below `min_floor`.
6. **Verdict Deduction**:
   Because the altitude limiter violates both flight safety requirements (uncontrolled descent on level entry; ceiling runaway on punch-out entry), Milestone 1 cannot be approved in its current state.

---

## 3. Caveats

1. Flight aerodynamics were simulated on host C++ execution rather than in physical outdoor flight.
2. The `services.py` unawaited coroutine issue is an upstream caller flaw outside Worker M1's 6 assigned files; it is noted as an integration risk for Milestone 2.
3. Bug 2 (`mail.py`) and Bug 3 (`security.py`) are solidly implemented and passed 100% of adversarial tests.

---

## 4. Conclusion

**Verdict: REJECT Milestone 1**

Milestone 1 cannot be approved until `firmware/FC_can_bang/flight_gate.h` and `MODE.ino` are revised to fix the 3 altitude limiter failure modes:

### Required Remediation for Worker M1:
1. **In `firmware/FC_can_bang/MODE.ino` line 10**:
   Explicitly pass a safe hover floor for the F450 airframe (e.g. `1350.0f` or `ALT_LIMIT_DEFAULT_FLOOR_US`):
   ```cpp
   throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps, 1350.0f);
   ```
2. **In `firmware/FC_can_bang/flight_gate.h`**:
   - Cap `dynamic_base` at a maximum allowable ceiling floor (e.g. `1450.0f`) so high punch-out entries cannot lock the floor above hover:
     ```cpp
     float dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US;
     if (dynamic_base > 1450.0f) dynamic_base = 1450.0f;
     ```
   - In line 110, do not let `effective_floor` drop below `min_floor_us`:
     ```cpp
     if (effective_floor > (float)throttle_us - 20.0f) {
       effective_floor = (float)throttle_us - 20.0f;
       if (min_floor_us > 0.0f && effective_floor < min_floor_us) {
         effective_floor = min_floor_us;
       }
     }
     ```

---

## 5. Verification Method

### 5.1 Test Files Added by Challenger 1
- `tests/firmware/test_altitude_limiter_stress.cpp`
- `tests/scope01/test_email_normalization_stress.py`
- `tests/scope01/test_smtp_concurrency_stress.py`

### 5.2 Independent Verification Commands
```powershell
# 1. Run firmware stress test suite and observe the 3 confirmed vulnerabilities:
g++ -std=c++17 -Ifirmware/FC_can_bang tests/firmware/test_altitude_limiter_stress.cpp -o tests/firmware/test_altitude_limiter_stress.exe
.\tests\firmware\test_altitude_limiter_stress.exe
Remove-Item -Force tests\firmware\test_altitude_limiter_stress.exe

# 2. Run email normalization & SMTP concurrency stress suites:
pytest tests/scope01/test_email_normalization_stress.py tests/scope01/test_smtp_concurrency_stress.py
```
