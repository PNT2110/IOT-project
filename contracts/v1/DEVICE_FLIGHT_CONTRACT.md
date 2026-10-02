# Device flight contract (Pi → PC) — v1

The Pi sends a flight-permission request to the PC server and asks for the
decision. Every request body is a sealed envelope; there is no user session.

## Device identity

`python -m server.cli add-device --name <name>` on the PC prints
`PI_DEVICE_ID` and `PI_DEVICE_KEY` (32 random bytes, base64url) once. Both go
into the Pi environment file. The PC stores the key encrypted at rest and can
revoke a device by setting `devices.revoked_at`.

## Envelope

```json
{"device_id": "<uuid>", "ts": 1790000000, "nonce": "<b64url 12 bytes>", "ciphertext": "<b64url>"}
```

- Cipher: AES-256-GCM, key = device key, nonce = 12 random bytes.
- Plaintext: the payload as JSON with sorted keys and `,` `:` separators, UTF-8.
- Associated data: `"<device_id>|<ts>"` (UTF-8).
- base64url without padding.
- The PC rejects (HTTP 401 `DEVICE_AUTH_FAILED`): unknown or revoked device,
  `|now - ts| > 300` seconds, a failed tag, or a `(device_id, nonce)` pair seen
  in the last 600 seconds.

Test vector (key = bytes 0..31, nonce = bytes 100..111):

| Field | Value |
|---|---|
| device_id | `dev-test-0001` |
| ts | `1790000000` |
| payload | `{"client_ref":"ref-0001","vehicle":"F450"}` |
| nonce | `ZGVmZ2hpamtsbW5v` |
| ciphertext | `Mzm9ChCMOOphEDqO-F9IjyekKzq7XMJQi_PaLZPKxiTxy3riCiauNN-Ook0S8-HwGq_HmkLf9-hLyg` |

## `POST /api/v1/device/flight-requests`

Payload:

| Field | Type | Notes |
|---|---|---|
| `client_ref` | string 8–64, `[A-Za-z0-9_.-]` | Chosen by the Pi; resending the same value returns the same request |
| `applicant_full_name` | string | Full name |
| `license_code` | string | Pilot licence code |
| `flight_date` | `YYYY-MM-DD` | Vietnam local date |
| `flight_time` | `HH:MM` | Start of the flight window, Vietnam local time |
| `flight_end_time` | `HH:MM` or absent | End of the window, same day, after `flight_time`; absent means one hour |
| `vehicle` | string | Selected aircraft |
| `pi_username` | string | Pi account that filled in the form |
| `gps` | object or `null` | `{lat, lon, fix_state, satellites}` from the ESP32; `null` when there is no fix |

Response `201`: `{"request_id": "<uuid>", "status": "PENDING"}`. Invalid
fields give `422`.

## `POST /api/v1/device/flight-requests/{request_id}/status`

Payload: `{"request_id": "<uuid>"}`.

Response `200`: `{"request_id", "status": "PENDING" | "APPROVED" | "REJECTED", "reason", "decided_at"}`.
A request that belongs to another device gives `404`.

## What the Pi does with the decision

- `APPROVED`: send `$AUTH,ALLOW,<seconds>,<ref>` to the ESP32 and keep sending
  `$PING` so the authorization stays alive.
- `REJECTED`, or no approved request: send `$AUTH,DENY,<ref>`. The ESP32 also
  boots denied.

Neither side has an ARM, DISARM or motor command.
