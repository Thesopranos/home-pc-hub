"""Relax ambient — warm dim (Hue Relax, floored at 2500K)."""

from homepchub.core.presets.base import apply_static_preset, register


def _apply(host: str) -> None:
    apply_static_preset(host, "relax")


register("relax", label_key="preset.relax", apply=_apply, editable=True)
