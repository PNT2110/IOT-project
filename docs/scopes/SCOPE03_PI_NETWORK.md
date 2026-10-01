# SCOPE-03 — Pi Network

**Current owner override (2026-09-24):** target profile is one onboard Wi-Fi PHY with managed `wlan0` as upstream STA and `ap0` as local F450 AP. This supersedes the USB-STA target for the living deployment profile only; historical reports remain unchanged and live validation is pending.

## 1. Mục tiêu và bàn giao

AP `ap0` liên tục, managed STA `wlan0` trên cùng PHY, recovery/captive-portal best-effort và ba reachability signals.

## 2. Bối cảnh/trạng thái

Pi OS/chipset/country/channel và khả năng AP+STA cùng PHY chưa xác minh độc lập; không suy ra role từ tên interface.

## 3. In scope / out of scope

In: NetworkManager adapter, AP, DHCP/DNS/status. Out: drone/FC/firmware.

## 4. Dependencies và prerequisites

Pi inventory, physical safety approval, SCOPE-02 nếu sync status.

## 5. Quyết định áp dụng

ADR-006, network design tại `../12_NETWORK_ARCHITECTURE.md`.

## 6. Files

Chỉ sửa Pi network/config/tests được duyệt; không sửa firmware.

## 7. Tasks

Mock state model → address conflict check → typed profile adapter → DHCP/DNS/firewall → status probes → recovery tests → approved lab test.

## 8. API/data contracts và lỗi

Ba booleans độc lập; invalid profile → 422; failed STA giữ AP và last-known-good.

## 9. Quyền, secrets, privacy, safety

No shell injection, AP segmentation, admin SSH off by default, secret redaction.

## 10. Test plan

Mock NetworkManager, upstream loss, duplicate subnet, malformed SSID, portal manual URL, no Internet/server.

## 11. Acceptance criteria

AP vẫn reachable khi STA fail; ba trạng thái độc lập; config không thực thi input tùy ý. N2/N4 vẫn cần live client evidence.

## 12. Evidence

Redacted config, interface/status outputs, test logs, chipset proof.

## 13. Rollback/failure handling

Restore last-known-good profile; keep AP; no destructive cleanup.

## 14. Definition of Done / gate

Reports complete; owner accepts lab evidence before Pi web.
