import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { getLatestTelemetry, type TelemetryData } from "../../api";

export interface TelemetryPanelProps {
  telemetry?: TelemetryData | null;
  telemetryAgeText?: string;
}

function GpsMap({
  lat,
  lon,
  label = "Vị trí trực tiếp của drone",
}: {
  lat: number;
  lon: number;
  label?: string;
}) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.CircleMarker | null>(null);

  useEffect(() => {
    if (!elementRef.current) return;
    const map = L.map(elementRef.current, {
      zoomControl: false,
      attributionControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
    }).setView([lat, lon], 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(map);

    const marker = L.circleMarker([lat, lon], {
      radius: 8,
      color: "#086eae",
      fillColor: "#1689d5",
      fillOpacity: 0.9,
    }).addTo(map);

    mapRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (markerRef.current && mapRef.current) {
      markerRef.current.setLatLng([lat, lon]);
      mapRef.current.panTo([lat, lon]);
    }
  }, [lat, lon]);

  return (
    <div
      ref={elementRef}
      className="gps-map"
      role="img"
      aria-label={`${label} ${lat.toFixed(6)}, ${lon.toFixed(6)}`}
    />
  );
}

/**
 * Real-time Telemetry Panel displaying live GPS coordinates (latitude, longitude),
 * altitude, battery status with threshold styling, and sensor fix state.
 */
export function TelemetryPanel({
  telemetry: externalTelemetry,
  telemetryAgeText: externalAgeText,
}: TelemetryPanelProps) {
  const [internalTelemetry, setInternalTelemetry] = useState<TelemetryData | null>(null);
  const [internalAgeText, setInternalAgeText] = useState<string>("< 2s");
  const lastTelemetryReceivedRef = useRef<number | null>(null);

  // If telemetry is not passed from parent, poll autonomously with strict 1s interval
  useEffect(() => {
    if (externalTelemetry !== undefined) return;

    let active = true;
    const pollTelemetry = async () => {
      try {
        const latest = await getLatestTelemetry();
        if (!active) return;
        if (latest) {
          setInternalTelemetry(latest);
          lastTelemetryReceivedRef.current = Date.now();
          setInternalAgeText("< 2s");
        }
      } catch {
        // Silently handle telemetry polling errors
      }
    };

    void pollTelemetry();
    const telemetryInterval = window.setInterval(pollTelemetry, 1000);

    const ageTicker = window.setInterval(() => {
      const last = lastTelemetryReceivedRef.current;
      if (!last) {
        setInternalAgeText("—");
        return;
      }
      const elapsedSeconds = (Date.now() - last) / 1000;
      if (elapsedSeconds < 2) {
        setInternalAgeText("< 2s");
      } else {
        setInternalAgeText(`${Math.round(elapsedSeconds)}s trước`);
      }
    }, 500);

    return () => {
      active = false;
      window.clearInterval(telemetryInterval);
      window.clearInterval(ageTicker);
    };
  }, [externalTelemetry]);

  const telemetry = externalTelemetry !== undefined ? externalTelemetry : internalTelemetry;
  const ageText = externalAgeText !== undefined ? externalAgeText : internalAgeText;

  // Battery threshold calculation (green >= 50%, amber 20-49%, red < 20%)
  const batteryPct = telemetry?.battery_pct != null ? Math.round(telemetry.battery_pct) : null;
  const batteryClass =
    batteryPct == null
      ? "battery-unknown"
      : batteryPct >= 50
        ? "battery-healthy"
        : batteryPct >= 20
          ? "battery-warning"
          : "battery-critical";

  // Telemetry status chip computation
  const fixState =
    telemetry?.fix_state || (telemetry?.latitude != null ? "VALID_FIX" : "NO_FIX");
  const isFixValid = fixState === "VALID_FIX";
  const isTelemetryStale = telemetry?.stale === true;

  return (
    <div className="telemetry-view">
      <div className="telemetry-header-card">
        <div className="telemetry-header-title">
          <div className="telemetry-live-indicator">
            <span className="telemetry-live-pulse" aria-hidden="true" />
            <strong>TRỰC TIẾP</strong>
            <span className="telemetry-age-chip">{ageText}</span>
          </div>
          <h3>Giám sát đo đạc chuyến bay</h3>
          <p className="workspace-note">
            Dữ liệu được cập nhật thời gian thực mỗi 1 giây từ gateway Raspberry Pi và cảm biến ESP32.
          </p>
        </div>
        <div className="telemetry-quick-status">
          <span
            className={`status-chip status-${isFixValid ? "approved_simulated" : isTelemetryStale ? "rejected" : "under_review"}`}
          >
            {isFixValid
              ? "VALID_FIX · Khóa GPS"
              : isTelemetryStale
                ? "STALE · Mất tín hiệu"
                : "NO_FIX · Đang bắt sóng"}
          </span>
          {telemetry?.device_name && (
            <span className="telemetry-device-tag">
              Thiết bị: {telemetry.device_name}
            </span>
          )}
        </div>
      </div>

      <div className="telemetry-grid">
        {/* Metric 1: GPS Position (latitude & longitude) */}
        <div className="telemetry-metric-card">
          <span className="metric-label">Tọa độ GPS (WGS84)</span>
          <div className="metric-value font-tabular">
            {telemetry?.latitude != null && telemetry?.longitude != null ? (
              <>
                <span>{telemetry.latitude.toFixed(6)}° N</span>
                <span className="metric-divider">, </span>
                <span>{telemetry.longitude.toFixed(6)}° E</span>
              </>
            ) : (
              <span className="metric-empty">Chưa có tọa độ</span>
            )}
          </div>
          <small className="metric-sub">Độ phân giải 6 chữ số thập phân</small>
        </div>

        {/* Metric 2: Altitude */}
        <div className="telemetry-metric-card">
          <span className="metric-label">Độ cao (Khí áp kế & GPS)</span>
          <div className="metric-value font-tabular">
            {telemetry?.altitude_m != null ? (
              <span>{telemetry.altitude_m.toFixed(1)} m</span>
            ) : (
              <span className="metric-empty">—</span>
            )}
          </div>
          <small className="metric-sub">Mét so với mặt đất (AGL)</small>
        </div>

        {/* Metric 3: Battery */}
        <div className="telemetry-metric-card">
          <div className="metric-label-row">
            <span className="metric-label">Dung lượng pin</span>
            <span className={`battery-badge ${batteryClass}`}>
              {batteryPct != null ? `${batteryPct}%` : "—"}
            </span>
          </div>
          <div className="battery-bar-container">
            <div
              className={`battery-bar-fill ${batteryClass}`}
              style={{ width: `${Math.min(100, Math.max(0, batteryPct ?? 0))}%` }}
            />
          </div>
          <small className="metric-sub">
            {telemetry?.voltage_v != null
              ? `Điện áp: ${telemetry.voltage_v.toFixed(2)} V`
              : "Ngưỡng an toàn: > 20%"}
          </small>
        </div>

        {/* Metric 4: Fix State & Signal */}
        <div className="telemetry-metric-card">
          <span className="metric-label">Tình trạng cảm biến</span>
          <div className="metric-value">
            <span className={`chip-fix-state ${isFixValid ? "valid" : "invalid"}`}>
              {fixState}
            </span>
          </div>
          <small className="metric-sub">
            {telemetry?.seq != null ? `Gói tin #${telemetry.seq}` : "Đang chờ gói tin..."}
          </small>
        </div>
      </div>

      {/* Live Position Cartography */}
      <div className="telemetry-map-card">
        <h4>Vị trí drone trên bản đồ</h4>
        {telemetry?.latitude != null && telemetry?.longitude != null ? (
          <GpsMap
            lat={telemetry.latitude}
            lon={telemetry.longitude}
            label="Vị trí trực tiếp của drone"
          />
        ) : (
          <div className="gps-map gps-map-empty">
            Đang đợi dữ liệu định vị GPS từ drone...
          </div>
        )}
      </div>
    </div>
  );
}
