"""Reading ambient — warm high brightness (Hue Read recipe)."""

from homepchub.core.presets.base import apply_static_preset, register


def _apply(host: str) -> None:
    apply_static_preset(host, "reading")


register("reading", label_key="preset.reading", apply=_apply, editable=True)
