/**
 * PC Frontend Type Definitions
 * F450 PNT PVD Drone Zone Check
 */

import type { Zone, FlightRequest, Account } from "./api";

export type TelemetryData = {
  device_id?: string | null;
  device_name?: string | null;
  seq?: number | null;
  observed_at?: string | null;
  received_at?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  altitude_m?: number | null;
  battery_pct?: number | null;
  voltage_v?: number | null;
  fix_state?: string | null;
  stale?: boolean;
};

export type ZoneGeoJsonFeature = {
  type: "Feature";
  id: string;
  properties: {
    id: string;
    name: string;
    classification: string;
    visibility: string;
    version: number;
    retrieved_at: string;
    source_id: string | null;
  };
  geometry: Zone["geometry"];
};

export type ZoneGeoJsonCollection = {
  type: "FeatureCollection";
  features: ZoneGeoJsonFeature[];
};

export type FlightNotification = {
  id: string;
  summary: string;
  applicant?: string;
  vehicle?: string;
  timestamp: string;
};

export type { Zone, FlightRequest, Account };
