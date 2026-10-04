// views/map.js - Offline Leaflet map view for no-fly zones and live drone position
import { h } from "../core/dom.js";
import { API, api, every, addCleanup } from "../core/api.js";

export function mapView() {
  const element = h("div", { id: "map" });
  const info = h("p", { class: "muted" });
  const section = h("section", { class: "card" },
    h("div", { class: "row between" },
      h("h2", {}, "Bản đồ vùng cấm bay"),
      h("button", { type: "button", onclick: async (event) => {
        event.target.disabled = true;
        try { await api("/map/sync", { method: "POST" }); await loadZones(); }
        catch (error) { info.textContent = error.message; }
        finally { event.target.disabled = false; }
      } }, "Đồng bộ từ máy chủ")),
    element, info);
  let map; let zoneLayer; let marker; let centered = false;

  async function loadZones() {
    const cache = await api("/map/cache");
    zoneLayer.clearLayers();
    const items = cache.payload?.items ?? [];
    for (const zone of items) {
      const color = zone.classification === "RESTRICTED" ? "#f5a524" : "#d6495f";
      const layer = L.geoJSON(zone.geometry, { style: { color, fillColor: color, fillOpacity: .35, weight: 2 } }).addTo(zoneLayer);
      layer.bindPopup(h("div", {}, h("strong", {}, zone.name), h("br"), zone.classification === "RESTRICTED" ? "Vùng hạn chế bay" : "Vùng cấm bay"));
    }
    info.textContent = cache.state === "AVAILABLE" ? `${items.length} vùng · chỉ xem · lấy từ máy chủ lúc ${new Date(cache.provenance.fetched_at).toLocaleString("vi-VN")}` : "Chưa có dữ liệu vùng từ máy chủ. Bấm Đồng bộ khi Pi có mạng.";
    if (items.length && !centered) { map.fitBounds(zoneLayer.getBounds().pad(.3), { maxZoom: 14 }); centered = true; }
  }

  setTimeout(() => {
    map = L.map(element).setView([16.15, 106.25], 5);
    L.tileLayer(`${API}/tiles/{z}/{x}/{y}.png`, { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
    zoneLayer = L.featureGroup().addTo(map);
    addCleanup(() => map.remove());
    loadZones().catch((error) => { info.textContent = error.message; });
    every(2000, async () => {
      try {
        const sample = await api("/telemetry");
        if (sample.fix_state === "FIX" && sample.latitude != null) {
          const position = [sample.latitude, sample.longitude];
          if (!marker) {
            marker = L.circleMarker(position, { radius: 8, color: "#086eae", fillColor: "#1689d5", fillOpacity: .95 }).addTo(map).bindPopup("Vị trí hiện tại của drone");
            map.setView(position, 15);
            centered = true;
          } else {
            marker.setLatLng(position);
          }
        } else if (marker) {
          marker.remove();
          marker = null;
        }
      } catch { /* shown on the telemetry tab */ }
    });
  });
  return section;
}
