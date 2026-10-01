"""Typed, offline-only network models and adapters for SCOPE-03."""

from .adapters import (
    InMemoryProfileStore,
    MockConnectivityProbe,
    MockNetworkManagerAdapter,
    MockRecoveryController,
)
from .models import (
    InterfaceIdentity,
    NetworkStatus,
    ReachabilitySignal,
    SignalState,
)
from .state import NetworkEvent, PiNetworkStateMachine

__all__ = [
    "InMemoryProfileStore",
    "InterfaceIdentity",
    "MockConnectivityProbe",
    "MockNetworkManagerAdapter",
    "MockRecoveryController",
    "NetworkEvent",
    "NetworkStatus",
    "PiNetworkStateMachine",
    "ReachabilitySignal",
    "SignalState",
]
