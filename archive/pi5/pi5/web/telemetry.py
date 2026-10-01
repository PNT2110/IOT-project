from __future__ import annotations

from datetime import datetime, timezone

from .models import FixState, TelemetrySample


class MockTelemetrySource:
    def __init__(self, sample: TelemetrySample | None = None) -> None:
        self.sample = sample or TelemetrySample(
            schema_version="scope04.telemetry.v1",
            source="MOCK",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            stale=True,
            fix_state=FixState.UNAVAILABLE,
        )

    def read(self) -> dict[str, object]:
        return self.sample.as_dict()

    def set_sample(self, sample: TelemetrySample) -> None:
        if sample.source != "MOCK":
            raise ValueError("SCOPE-04 mock source must identify source=MOCK")
        self.sample = sample


def build_3d_view(telemetry: dict[str, object]) -> dict[str, object]:
    orientation_fields = ("heading_deg", "pitch_deg", "roll_deg")
    available = all(telemetry.get(field) is not None for field in orientation_fields)
    return {
        "enabled": available,
        "orientation": {field: telemetry.get(field) if available else None for field in orientation_fields},
        "label": "AVAILABLE" if available else "UNAVAILABLE",
        "animation": False,
        "reason": None if available else "orientation fields are unavailable",
    }
