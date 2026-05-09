"""Time-domain unfolding utilities for the sMTJ-PBNN simulator.

Submodules:

* :mod:`schedules`        -- pure Python; importable without torch.
* :mod:`unfold`           -- requires torch.
* :mod:`bernoulli_smtj`   -- requires torch.

The torch-dependent submodules are NOT eagerly imported at subpackage
load time, so ``import smtj_pbnn_sim.sampling.schedules`` works in a
torch-free environment. Use ``from smtj_pbnn_sim.sampling.bernoulli_smtj
import bernoulli_from_voltage`` to access the torch-dependent parts when
torch is installed.
"""
