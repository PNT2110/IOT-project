import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";
import type { Zone } from "../../api";

type MapPanelProps = {
  zones: Zone[];
  editable?: boolean;
  resetKey?: number;
  selectedZoneId?: string | null;
  onGeometryChange?: (geometry: Zone["geometry"]) => void;
  onDraftInvalidated?: () => void;
  onZoneSelect?: (zone: Zone) => void;
};

function polygonCoordinates(zone: Zone): L.LatLngExpression[][][] {
  const polygons = zone.geometry.type === "Polygon" ? [zone.geometry.coordinates] : zone.geometry.coordinates;
  return polygons.map((polygon) => polygon.map((ring) => ring.map(([longitude, latitude]) => [latitude, longitude] as L.LatLngExpression)));
}

function layerGeometry(layer: L.Polygon): Zone["geometry"] {
  return layer.toGeoJSON().geometry as Zone["geometry"];
}

export function MapPanel({ zones, editable = false, resetKey = 0, selectedZoneId = null, onGeometryChange, onDraftInvalidated, onZoneSelect }: MapPanelProps) {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const zoneLayerRef = useRef<L.LayerGroup | null>(null);
  const draftLayerRef = useRef<L.Polygon | null>(null);
  const measureLayerRef = useRef<L.Layer | null>(null);
  const gridLayerRef = useRef<L.LayerGroup | null>(null);
  const measuringRef = useRef(false);
  const fittedRef = useRef(false);
  const geometryChangeRef = useRef(onGeometryChange);
  const [drawing, setDrawing] = useState<"Polygon" | "Rectangle" | null>(null);
  const [hasDraft, setHasDraft] = useState(false);
  const [measuring, setMeasuring] = useState(false);
  const [measurePoints, setMeasurePoints] = useState<L.LatLng[]>([]);
  const [gridEnabled, setGridEnabled] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [mapNotice, setMapNotice] = useState("");

  geometryChangeRef.current = onGeometryChange;

  const removeDraft = () => {
    draftLayerRef.current?.remove();
    draftLayerRef.current = null;
    setHasDraft(false);
  };

  useEffect(() => {
    if (!mapElement.current) return;
    const map = L.map(mapElement.current, { zoomControl: false, attributionControl: true }).setView([16.15, 106.25], 5);
    mapRef.current = map;
    L.control.zoom({ position: "topright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
    map.on("click", (event) => {
      if (measuringRef.current) setMeasurePoints((points) => points.length >= 2 ? [event.latlng] : [...points, event.latlng]);
    });
    map.on("pm:create", (event) => {
      const layer = event.layer as L.Polygon;
      draftLayerRef.current?.remove();
      draftLayerRef.current = layer;
      layer.setStyle({ color: "#1689d5", fillColor: "#1689d5", fillOpacity: 0.18, dashArray: "5 5" });
      layer.pm.enable({ allowSelfIntersection: false });
      layer.on("pm:edit", () => geometryChangeRef.current?.(layerGeometry(layer)));
      setHasDraft(true);
      setDrawing(null);
      geometryChangeRef.current?.(layerGeometry(layer));
    });
    map.on("pm:drawend", () => setDrawing(null));
    map.on("locationfound", (event) => { map.setView(event.latlng, Math.max(map.getZoom(), 12)); setMapNotice("Đã định vị theo trình duyệt."); });
    map.on("locationerror", () => setMapNotice("Trình duyệt không cấp quyền định vị hoặc thiết bị chưa có GPS."));
    const resize = () => map.invalidateSize();
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    measuringRef.current = false;
    mapRef.current?.pm.disableDraw();
    setDrawing(null);
    setMeasuring(false);
    removeDraft();
    setMeasurePoints([]);
    setMapNotice("");
  }, [resetKey]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    zoneLayerRef.current?.remove();
    const zoneLayer = L.layerGroup().addTo(map);
    const layers = zones.flatMap((zone) => {
      const color = zone.classification === "RESTRICTED" || zone.classification === "INTERNAL_RESEARCH" ? "#f5a524" : "#d6495f";
      const selected = editable && zone.id === selectedZoneId;
      return polygonCoordinates(zone).map((polygon) => {
        const layer = L.polygon(polygon, { color, fillColor: color, fillOpacity: selected ? 0.5 : 0.35, weight: selected ? 3 : 2, pmIgnore: !selected }).addTo(zoneLayer);
        if (selected && zone.geometry.type === "Polygon") {
          // Dragging a vertex of the selected zone edits its geometry in place.
          layer.pm.enable({ allowSelfIntersection: false });
          layer.on("pm:edit", () => geometryChangeRef.current?.(layerGeometry(layer)));
        } else {
          const popup = document.createElement("div");
          const title = document.createElement("strong");
          title.textContent = zone.name;
          const classification = document.createElement("div");
          classification.textContent = zone.classification === "NO_FLY" ? "Vùng cấm bay" : zone.classification === "RESTRICTED" ? "Vùng hạn chế bay" : zone.classification.replaceAll("_", " ");
          popup.append(title, classification);
          if (!editable) layer.bindPopup(popup);
        }
        if (editable && onZoneSelect && !selected) layer.on("click", () => onZoneSelect(zone));
        return layer;
      });
    });
    if (layers.length > 0 && !fittedRef.current) {
      map.fitBounds(L.featureGroup(layers).getBounds().pad(0.35), { maxZoom: 12 });
      fittedRef.current = true;
    }
    zoneLayerRef.current = zoneLayer;
    return () => { zoneLayer.remove(); };
  }, [editable, onZoneSelect, selectedZoneId, zones]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    measureLayerRef.current?.remove();
    measureLayerRef.current = null;
    if (measurePoints.length < 2) return;
    measureLayerRef.current = L.polyline(measurePoints, { color: "#1689d5", dashArray: "6 5", weight: 3, pmIgnore: true }).addTo(map);
    const distanceKm = map.distance(measurePoints[0], measurePoints[1]) / 1000;
    setMapNotice(`Khoảng cách đo: ${distanceKm.toFixed(2)} km`);
    return () => { measureLayerRef.current?.remove(); };
  }, [measurePoints]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const redrawGrid = () => {
      gridLayerRef.current?.remove();
      gridLayerRef.current = null;
      if (!gridEnabled) return;
      const bounds = map.getBounds();
      const step = map.getZoom() >= 9 ? 0.1 : map.getZoom() >= 6 ? 0.5 : 1;
      const grid = L.layerGroup();
      const startLat = Math.floor(bounds.getSouth() / step) * step;
      const startLng = Math.floor(bounds.getWest() / step) * step;
      for (let lat = startLat; lat <= bounds.getNorth(); lat += step) grid.addLayer(L.polyline([[lat, bounds.getWest()], [lat, bounds.getEast()]], { color: "#ffffff", opacity: 0.32, weight: 1, interactive: false, pmIgnore: true }));
      for (let lng = startLng; lng <= bounds.getEast(); lng += step) grid.addLayer(L.polyline([[bounds.getSouth(), lng], [bounds.getNorth(), lng]], { color: "#ffffff", opacity: 0.32, weight: 1, interactive: false, pmIgnore: true }));
      grid.addTo(map);
      gridLayerRef.current = grid;
    };
    redrawGrid();
    map.on("moveend zoomend", redrawGrid);
    return () => { map.off("moveend zoomend", redrawGrid); gridLayerRef.current?.remove(); gridLayerRef.current = null; };
  }, [gridEnabled]);

  const startDrawing = (shape: "Polygon" | "Rectangle") => {
    const map = mapRef.current;
    if (!map) return;
    map.pm.disableDraw();
    if (drawing === shape) { setDrawing(null); return; }
    measuringRef.current = false;
    setMeasuring(false);
    setMeasurePoints([]);
    removeDraft();
    onDraftInvalidated?.();
    map.pm.enableDraw(shape, { snappable: true, allowSelfIntersection: false });
    setDrawing(shape);
    setMapNotice(shape === "Polygon" ? "Bấm từng đỉnh trên bản đồ, bấm lại đỉnh đầu để khép vùng." : "Bấm hai góc đối diện của hình chữ nhật.");
  };
  const clearDraft = () => { mapRef.current?.pm.disableDraw(); setDrawing(null); removeDraft(); onDraftInvalidated?.(); };
  const toggleMeasure = () => {
    const next = !measuring;
    measuringRef.current = next;
    mapRef.current?.pm.disableDraw();
    setDrawing(null);
    setMeasuring(next);
    setMeasurePoints([]);
    setMapNotice(next ? "Chọn hai điểm trên bản đồ để đo khoảng cách." : "");
  };
  const searchMap = () => {
    const pair = searchText.split(",").map((value) => Number(value.trim()));
    const [first, second] = pair;
    if (pair.length === 2 && Number.isFinite(first) && Number.isFinite(second) && first >= -90 && first <= 90 && second >= -180 && second <= 180) {
      mapRef.current?.setView([first, second], 12);
      setMapNotice(`Đã chuyển tới ${first.toFixed(5)}, ${second.toFixed(5)}.`);
      return;
    }
    const found = searchText.trim() ? zones.find((zone) => zone.name.toLowerCase().includes(searchText.trim().toLowerCase())) : undefined;
    if (found && mapRef.current) {
      const searchLayers = polygonCoordinates(found).map((polygon) => L.polygon(polygon));
      mapRef.current.fitBounds(L.featureGroup(searchLayers).getBounds().pad(0.35), { maxZoom: 12 });
      setMapNotice(`Đã tìm vùng: ${found.name}.`);
      return;
    }
    setMapNotice("Nhập tọa độ dạng vĩ độ, kinh độ hoặc tên vùng đã có dữ liệu.");
  };

  return (
    <section className="map-section" aria-label="Bản đồ vùng cấm bay và hạn chế bay">
      <div className="map-toolbar"><div className="map-search-row">
        <button className="map-home-button" type="button" title="Về vị trí ban đầu" onClick={() => mapRef.current?.setView([16.15, 106.25], 5)}>⌂</button>
        <input aria-label="Tìm kiếm địa điểm" placeholder="Tìm tên vùng hoặc tọa độ" value={searchText} onChange={(event) => setSearchText(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") searchMap(); }} />
        <button type="button" onClick={searchMap}>Tìm</button>
        {editable && <button type="button" aria-pressed={drawing === "Polygon"} onClick={() => startDrawing("Polygon")}>{drawing === "Polygon" ? "Hủy vẽ" : "Vẽ đa giác"}</button>}
        {editable && <button type="button" aria-pressed={drawing === "Rectangle"} onClick={() => startDrawing("Rectangle")}>{drawing === "Rectangle" ? "Hủy vẽ" : "Vẽ chữ nhật"}</button>}
        {editable && hasDraft && <button type="button" onClick={clearDraft}>Xóa nét vẽ</button>}
      </div><div className="map-toolbar-status">{editable ? "Vẽ vùng mới, hoặc bấm vào một vùng rồi kéo các đỉnh để sửa" : "Chỉ xem · dữ liệu tham khảo, không thay thế giấy phép bay"}{mapNotice ? ` · ${mapNotice}` : ""}</div></div>
      <div className="map-canvas-wrap"><div ref={mapElement} className="map-canvas" />
        <div className="map-legend" aria-label="Chú giải bản đồ"><label><span className="legend-swatch no-fly" /> Vùng cấm bay</label><label><span className="legend-swatch restricted" /> Vùng hạn chế bay</label></div>
        <div className="map-actions" aria-label="Công cụ bản đồ"><button type="button" title="Đo đạc" aria-pressed={measuring} onClick={toggleMeasure}>⌁</button><button type="button" title="Định vị hiện tại" onClick={() => mapRef.current?.locate({ setView: false, enableHighAccuracy: true })}>⌖</button><button type="button" title="Bật lưới tọa độ" aria-pressed={gridEnabled} onClick={() => setGridEnabled((enabled) => !enabled)}>▦</button><button type="button" title="Toàn màn hình" onClick={() => mapElement.current?.requestFullscreen?.()}>⛶</button></div>
      </div>
    </section>
  );
}
