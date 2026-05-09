"""Three-terminal SOT-MTJ resistance model.

The device has two distinct electrical paths:

* Read path  -- across the MTJ pillar; resistance switches between R_P
  (parallel) and R_AP (antiparallel), with TMR = (R_AP - R_P) / R_P.
* Write path -- through the heavy-metal SOT channel of resistance R_SOT,
  carrying the spin-Hall write current; the channel resistance is largely
  independent of the magnetic state.

Default values follow Chapter 2.3 (300 mm wafer SOT-MTJ on beta-W,
80 nm pillar): R_P = 4.9 kohm (Device A), TMR = 1.0, R_SOT = 776 ohm,
read voltage 50 mV.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MTJResistance:
    """Two-state read resistance plus SOT write-channel resistance.

    Attributes:
        R_P: Parallel-state read resistance [ohm].
        TMR: Tunneling magnetoresistance ratio (R_AP - R_P) / R_P.
        R_SOT: SOT write-channel resistance [ohm].
        V_read: Nominal read voltage [V].
    """
    R_P: float = 4.9e3
    TMR: float = 1.0
    R_SOT: float = 776.0
    V_read: float = 0.05

    @property
    def R_AP(self) -> float:
        return self.R_P * (1.0 + self.TMR)

    @property
    def G_P(self) -> float:
        return 1.0 / self.R_P

    @property
    def G_AP(self) -> float:
        return 1.0 / self.R_AP

    @property
    def G_mid(self) -> float:
        return 0.5 * (self.G_P + self.G_AP)

    @property
    def G_diff(self) -> float:
        """Half of (G_P - G_AP); scales the +/-1 binary contribution."""
        return 0.5 * (self.G_P - self.G_AP)


def conductance_from_state(state, mtj: MTJResistance):
    """Map a binary state s in {-1, +1} to per-cell read conductance [S].

    Works on NumPy arrays or Torch tensors; the linear combination
    ``G_mid + state * G_diff`` is backend-agnostic.
    """
    return mtj.G_mid + state * mtj.G_diff


def sot_write_energy(V_wr: float, t_p: float, R_SOT: float) -> float:
    """Single-shot SOT write energy via Ohmic dissipation in the channel.

        E = V_wr^2 / R_SOT * t_p.

    Following Chapter 2.3 (V_wr = 0.9 V, t_p = 0.75 ns, R_SOT = 776 ohm)
    gives E ~ 0.78 pJ.
    """
    return (V_wr * V_wr / R_SOT) * t_p
