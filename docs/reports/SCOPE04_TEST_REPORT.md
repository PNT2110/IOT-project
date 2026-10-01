# SCOPE-04 Test Report

Tested on PC in the repository virtual environment. This is not Pi hardware
evidence.

## Commands and results

```text
.venv/bin/pytest -q tests/scope04 -W default
17 passed, 1 warning, exit code 0

.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 tests/scope04 -W default
48 passed, 1 warning, exit code 0

git diff --check
exit code 0
```

Warning: Starlette test client imports the deprecated
`anyio.abc.BlockingPortal` alias. It did not fail a test.

## Coverage by requirement

| Requirement | Test evidence | Result |
|---|---|---|
| Local USER/ADMIN auth and separate session domain | `test_local_auth_separate_domain_and_cookie_csrf` | PASS on PC mock |
| CSRF and session invalidation | same test | PASS on PC mock |
| Camera normal frame | `test_camera_normal_frame_and_authenticated_stream` | PASS on PC mock |
| Camera unavailable/permission/busy/format/open/read errors | `test_camera_typed_failures` | PASS on PC mock |
| Empty frame, bounded queue, disconnect | `test_camera_empty_frame_disappears_and_disconnect_is_safe` | PASS on PC mock |
| `/dev/video1` distinction | `test_video1_is_not_guessed_as_camera` | PASS on PC mock |
| Cache unavailable/stale/provenance | `test_cache_provenance_stale_and_unavailable` | PASS on PC mock |
| Mock telemetry/no-fix | `test_telemetry_contract_and_3d_does_not_invent_orientation` | PASS on PC mock |
| Explicit `NO_FIX` and stale telemetry | `test_no_fix_and_stale_telemetry_remain_typed` | PASS on PC mock |
| 3D uses existing orientation only | `test_3d_only_uses_existing_orientation_fields` | PASS on PC mock |
| Reject public bind/no command routes | `test_bind_policy_rejects_public_listener_and_command_routes_do_not_exist` | PASS on PC mock |
| MFA rate limit/no secret disclosure | `test_wrong_mfa_is_rate_limited_without_secret_disclosure` | PASS on PC mock |

The external F450-client browser test and systemd unattended run were not run.
No network mutation was run.

## Live Pi smoke commands/results

```text
python3 -m venv /home/pitan/scope04-pi-web/.venv                 -> PASS
pip install -r pi5/requirements-scope04.lock                    -> PASS
pip check                                                        -> PASS
loopback http://127.0.0.1:8080/health                           -> PASS
loopback local shell                                             -> PASS
HTTPS 192.168.4.1:8443 health                                   -> PASS
upstream-down observer with local HTTPS/camera/cache available    -> PASS
synthetic USER/ADMIN auth over HTTPS                             -> PASS
CSRF reject and valid logout                                     -> PASS
authenticated /camera/stream                                     -> 200 image/jpeg
live /dev/video0 transient frame                                 -> PASS
map cache stale/provenance                                       -> STALE / SYNTHETIC
telemetry                                                         -> MOCK / UNAVAILABLE
3D missing orientation                                            -> disabled / UNAVAILABLE
control route /api/pi/v1/arm                                     -> 404
```

The test-only `httpx2` package was not added to the production venv. The live
auth smoke used real HTTPS requests with ephemeral synthetic users.
