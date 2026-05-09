"""Area estimation for sMTJ-PBNN tiles and accelerators."""

from __future__ import annotations

from .tech_params import TechParams


def tile_area(rows: int, cols: int, tech: TechParams) -> float:
    """Area of one tile in um^2.

    Components: cell array (read pillar + SOT track) + per-row DACs +
    per-column counters.
    """
    a_array = rows * cols * (tech.a_smtj_cell + tech.a_sot_track)
    a_dacs = rows * tech.a_dac
    a_counters = cols * tech.a_counter
    return a_array + a_dacs + a_counters


def accelerator_area(tile_rows: int, tile_cols: int, num_tiles: int,
                     tech: TechParams) -> float:
    """Total area for an accelerator with ``num_tiles`` identical tiles.

    Excludes the global controller, top-level interconnect and host
    interfaces; these are constant overheads that should be added by the
    caller from a separate floorplan budget.
    """
    return num_tiles * tile_area(tile_rows, tile_cols, tech)
