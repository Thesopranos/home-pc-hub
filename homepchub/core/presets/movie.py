"""Movie ambient - warm very dim bias light."""

from homepchub.core.presets.base import apply_static_preset, register


def _apply(host: str) -> None:
    apply_static_preset(host, "movie")


register("movie", label_key="preset.movie", apply=_apply, editable=True)
