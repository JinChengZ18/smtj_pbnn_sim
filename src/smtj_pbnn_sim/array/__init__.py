"""Array / circuit-level models for sMTJ-PBNN.

Submodules:

* :mod:`ir_drop`     -- pure Python; importable without torch.
* :mod:`crossbar`    -- requires torch.
* :mod:`periphery`   -- requires torch (for the DAC quantize op).
* :mod:`tile`        -- requires torch.

Import torch-dependent submodules directly when torch is installed.
"""
