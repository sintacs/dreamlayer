"""dreamlayer.plugins — the supported extension surface (see docs/PLATFORM.md).

The registries the codebase already had, given one doorway: object-lens
providers, Glance Arbiter candidates, Brain/Perception tiers, and HUD card
renderers. A plugin is a `register(ctx)` callable gated by capabilities and
loaded with failures isolated. First-party features are built through the same
doorway (dogfood), so the API is proven by use.
"""
from .base import (
    Plugin, SimplePlugin, make_plugin, PluginContext, PluginSettings,
    PluginRegistry, LoadResult,
)
from .events import PluginEventBus, KINDS as EVENT_KINDS
from .package import (
    PluginManifest, PluginPackage, sha256_of, KNOWN_CAPABILITIES, API_VERSION,
    SUPPORTED_API,
)
from .validate import validate, scan_source, smoke_load, ValidationReport
from .store import (
    RegistryIndex, StoreEntry, PluginStore, load_plugin_object,
)

__all__ = [
    "Plugin", "SimplePlugin", "make_plugin", "PluginContext", "PluginSettings",
    "PluginRegistry", "LoadResult",
    "PluginEventBus", "EVENT_KINDS",
    "PluginManifest", "PluginPackage", "sha256_of", "KNOWN_CAPABILITIES",
    "API_VERSION", "SUPPORTED_API",
    "validate", "scan_source", "smoke_load", "ValidationReport",
    "RegistryIndex", "StoreEntry", "PluginStore", "load_plugin_object",
]
