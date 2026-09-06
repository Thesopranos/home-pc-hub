"""Work / concentrate ambient - cool bright (Hue Concentrate recipe)."""

from homepchub.core.presets.base import apply_static_preset, register


def _apply(host: str) -> None:
    apply_static_preset(host, "work")


register("work", label_key="preset.work", apply=_apply, editable=True)
