"""Framework exceptions."""

from __future__ import annotations


class ContractViolationError(RuntimeError):
    """Raised when a node violates its declared NodeContract I/O."""

