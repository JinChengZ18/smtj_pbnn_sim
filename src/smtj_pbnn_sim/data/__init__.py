"""Datasets used by the experiments."""

from .mnist import get_mnist_loaders
from .cifar import get_cifar10_loaders
from .fashion_mnist import get_fashion_mnist_loaders

__all__ = ["get_mnist_loaders", "get_cifar10_loaders",
           "get_fashion_mnist_loaders"]
