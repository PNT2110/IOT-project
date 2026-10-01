# SCOPE-05 Repository Preparation Test Report

## CURRENT_CANONICAL_TEST_STATE — 2026-09-27 V3

Older command blocks below are `HISTORICAL_SNAPSHOT` / `SUPERSEDED`.

```text
TEST_SCOPE05=16 passed, exit code 0
TEST_SCOPE01_05=64 passed, 1 deprecation warning, exit code 0
GNSS_PASSIVE_BAUD_PROBE_SYNTHETIC=PASS
GNSS_BAUD_PROBE_WRITE_PATH=ABSENT
GIT_DIFF_CHECK=PASS, exit code 0
```

## CURRENT_CANONICAL_TEST_STATE — 2026-09-27 V2

Older command blocks below are `HISTORICAL_SNAPSHOT` / `SUPERSEDED`. The
current counts are:

```text
TEST_SCOPE05=8 passed, exit code 0
TEST_SCOPE01_05=56 passed, 1 deprecation warning, exit code 0
GIT_DIFF_CHECK=PASS, exit code 0
```

Evidence class: `TESTED_ON_PC_SYNTHETIC`; no hardware or serial device used.

Re-run during hardware-evidence ingestion and USB build-gate review:
`2026-09-26` (Asia/Ho_Chi_Minh).

## Commands and results

```text
.venv/bin/pytest -q tests/scope05 -W default
6 passed, exit code 0

.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -W default
54 passed, 1 deprecation warning, exit code 0

git diff --check
PASS, exit code 0
```

The combined warning is the existing Starlette/AnyIO
`BlockingPortal` deprecation warning. It did not fail a test and this report is
not a hardware validation record.

## Coverage

- valid synthetic NMEA GGA and explicit `NO_FIX`;
- bad checksum, malformed sentence and stale sample;
- explicit sequence gap and unavailable fields;
- validly framed synthetic UBX classified as `UNSUPPORTED_MESSAGE` because no
  actual module payload compatibility is claimed;
- UBX bad checksum, truncated frame and timeout;
- provenance envelope and absence of serial-write/control semantics.

## 2026-09-27 FAST TRACK rerun

The new FAST TRACK report is documentation/evidence only; no firmware source
or test code was changed.

```text
.venv/bin/pytest -q tests/scope05 -W default
6 passed, exit code 0

.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -W default
54 passed, 1 deprecation warning, exit code 0

git diff --check
PASS, exit code 0
```

The hardware identity commands were executed on the Pi, not by this local
pytest suite. No test result is promoted to hardware/build/flash evidence.

## 2026-09-27 MEGA FAST TRACK rerun

```text
.venv/bin/pytest -q tests/scope05 -W default
8 passed, exit code 0

.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -W default
56 passed, 1 deprecation warning, exit code 0

git diff --check
PASS, exit code 0
```

The first V1 PlatformIO attempt was historical and stopped before compilation
because framework installation failed with `Errno 28`. V2 moved staging to a
roomy build root and compiled successfully. No hardware or serial test is
represented by these pytest results.

## 2026-09-27 MEGA FAST TRACK V2 build evidence

```text
BUILD_ORIGINAL_RESULT=PASS
BUILD_GNSS_DISABLED_RESULT=PASS
BUILD_TARGET_USED=esp32dev_generic_compatibility_target
PROGRAM_SIZE=285745_bytes; 21.8_percent_flash_code
RAM_USAGE=22268_bytes; 6.8_percent
PROGRAM_SIZE_DELTA=0
RAM_USAGE_DELTA=0
FLASH_GATE=BLOCKED
```
