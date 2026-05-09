"""Neural network layers for sMTJ-PBNN.

Exports:
    PBNNLinear  -- fully-connected layer with stochastic binary weights
    PBNNConv2d  -- 2D convolutional counterpart
    SignSTE     -- straight-through estimator for sign(.)
    BinaryBatchNorm -- BN variant compatible with stochastic binary preact
    binary_cross_entropy_loss, mutual_information_regularizer
"""

from .ste import SignSTE, sign_ste
from .clt import bernoulli_pm1_clt_forward, BernoulliPm1CltLinear
from .pbnn_linear import PBNNLinear, ForwardMode
from .pbnn_conv import PBNNConv2d
from .deterministic_bnn import DeterministicBinaryLinear
from .batchnorm import BinaryBatchNorm1d, BinaryBatchNorm2d
from .losses import binary_cross_entropy_loss, mutual_information_regularizer

__all__ = [
    "SignSTE",
    "sign_ste",
    "bernoulli_pm1_clt_forward",
    "BernoulliPm1CltLinear",
    "PBNNLinear",
    "PBNNConv2d",
    "DeterministicBinaryLinear",
    "ForwardMode",
    "BinaryBatchNorm1d",
    "BinaryBatchNorm2d",
    "binary_cross_entropy_loss",
    "mutual_information_regularizer",
]
