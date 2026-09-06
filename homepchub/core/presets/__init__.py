"""Bulb ambient presets. Import this package to load registered modes."""

from homepchub.core.presets.base import (
    REGISTRY,
    apply_preset,
    apply_static,
    apply_static_preset,
    list_editable_ids,
    list_preset_ids,
    preset_label,
    register,
    reload_custom_presets,
    set_device_preset,
    stop_dynamic,
    unregister,
)

# Built-in modes (each file calls register on import)
from homepchub.core.presets import reading as _reading  # noqa: F401
from homepchub.core.presets import work as _work  # noqa: F401
from homepchub.core.presets import screen_sync as _screen_sync  # noqa: F401
from homepchub.core.presets import outside as _outside  # noqa: F401
from homepchub.core.presets import circadian as _circadian  # noqa: F401
from homepchub.core.presets import movie as _movie  # noqa: F401
from homepchub.core.presets import relax as _relax  # noqa: F401

reload_custom_presets()

__all__ = [
    "REGISTRY",
    "apply_preset",
    "apply_static",
    "apply_static_preset",
    "list_editable_ids",
    "list_preset_ids",
    "preset_label",
    "register",
    "reload_custom_presets",
    "set_device_preset",
    "stop_dynamic",
    "unregister",
]
