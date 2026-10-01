# SCOPE-03 PC mock network contract

**Contract:** `scope03.v1` · **Evidence:** `TESTED_ON_PC_MOCK` only

This is an offline design/mock contract. It is not a Pi device protocol, does not authenticate a device and must not be used to exchange PC/Pi data.

```json
{
  "schema_version": "scope03.v1",
  "evidence_class": "TESTED_ON_PC_MOCK",
  "ap_reachable": {"state": "UNKNOWN|UP|DOWN", "observed_at": "UTC", "source": "PC_MOCK", "stale": true, "latency_ms": null, "timeout_ms": null, "error_code": null},
  "external_wifi_connected": {"state": "UNKNOWN|UP|DOWN", "observed_at": "UTC", "source": "PC_MOCK", "stale": true, "latency_ms": null, "timeout_ms": null, "error_code": null},
  "internet_reachable": {"state": "UNKNOWN|UP|DOWN", "observed_at": "UTC", "source": "PC_MOCK", "stale": true, "latency_ms": null, "timeout_ms": null, "error_code": null},
  "central_server_reachable": {"state": "UNKNOWN|UP|DOWN", "observed_at": "UTC", "source": "PC_MOCK", "stale": true, "latency_ms": null, "timeout_ms": null, "error_code": null},
  "ap_state": "AP_UP|AP_DEGRADED",
  "sta_state": "STA_DISCONNECTED|STA_CONNECTING|STA_CONNECTED|STA_FAILED",
  "interfaces": [{"name": "redacted-or-mock", "purpose": "onboard_ap|usb_sta", "verified": false, "physical_path": null}],
  "manual_config_url": null,
  "last_known_good_version": null,
  "retry_count": 0,
  "retry_budget": 3,
  "stale": false,
  "source": "PC_MOCK"
}
```

Rules:

- The three reachability signals are independent. `external_wifi_connected=UP` does not imply Internet or PC reachability.
- `central_server_reachable` remains unknown/unavailable until a separately approved authenticated device identity and endpoint exist; the SCOPE-02 fake client header is not valid here.
- Profile drafts contain only purpose/interface/SSID metadata, `credential_present`, and version. They never store or serialize a password/PSK.
- A proposal has `applied=false`, `requires_live_authorization=true`, and an empty command list. The PC mock has no apply path.
- `manual_config_url` is null unless a real URL has been separately verified; mock tests may use an explicitly marked placeholder.
