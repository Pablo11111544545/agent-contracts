"""ContractValidator - Static validation for node contracts.

Validates contracts at registration time to catch configuration
errors before runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent_contracts.utils.logging import get_logger

if TYPE_CHECKING:
    from agent_contracts.registry import NodeRegistry

logger = get_logger("agent_contracts.validator")


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class ValidationResult:
    """Result of contract validation.
    
    Attributes:
        errors: Fatal issues that prevent execution (unknown slices, etc.)
        warnings: Potential issues that deserve attention
        info: Informational messages (shared writers, etc.)
    """
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not self.has_errors
    
    def __str__(self) -> str:
        """Human-readable format."""
        lines = []
        
        if self.errors:
            lines.append("ERRORS:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        if self.info:
            lines.append("INFO:")
            for info_msg in self.info:
                lines.append(f"  - {info_msg}")
        
        if not lines:
            lines.append("✅ All validations passed")
        
        return "\n".join(lines)


# =============================================================================
# Contract Validator
# =============================================================================

class ContractValidator:
    """Validator for node contracts.
    
    Performs static analysis on registered contracts to detect:
    - Unknown slice names in reads/writes
    - Missing service dependencies
    - Orphan/unreachable nodes
    - Shared writers (informational)
    
    Example:
        from agent_contracts import ContractValidator, get_node_registry
        
        registry = get_node_registry()
        # ... register nodes ...
        
        validator = ContractValidator(registry)
        result = validator.validate()
        
        if result.has_errors:
            print(result)
            sys.exit(1)
    """
    
    def __init__(
        self,
        registry: "NodeRegistry",
        known_services: set[str] | None = None,
        strict: bool = False,
    ):
        """Initialize validator.
        
        Args:
            registry: Node registry to validate
            known_services: Set of known service names for validation.
                           If None, service validation is skipped.
            strict: Treat warnings as errors for CI enforcement.
        """
        self._registry = registry
        self._known_services = known_services
        self._strict = strict
    
    def validate(self) -> ValidationResult:
        """Run all validations.
        
        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult()
        
        # Run validations
        self._validate_slices(result)
        self._validate_services(result)
        self._validate_reachability(result)
        self._report_shared_writers(result)
        self._apply_strict_mode(result)
        
        # Log summary
        if result.has_errors:
            logger.error(f"Contract validation failed: {len(result.errors)} errors")
        elif result.has_warnings:
            logger.warning(f"Contract validation passed with {len(result.warnings)} warnings")
        else:
            logger.info("Contract validation passed")
        
        return result
    
    def _validate_slices(self, result: ValidationResult) -> None:
        """Validate that all slice names are known."""
        valid_slices = self._registry._valid_slices
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            # Check reads
            for slice_name in contract.reads:
                if slice_name not in valid_slices:
                    result.errors.append(
                        f"Unknown slice '{slice_name}' in node '{name}' reads"
                    )
            
            # Check writes
            for slice_name in contract.writes:
                if slice_name not in valid_slices:
                    result.errors.append(
                        f"Unknown slice '{slice_name}' in node '{name}' writes"
                    )
                if slice_name == "request":
                    result.warnings.append(
                        f"Writing to 'request' slice is discouraged (node '{name}')"
                    )
    
    def _validate_services(self, result: ValidationResult) -> None:
        """Validate that required services are known."""
        if self._known_services is None:
            return  # Skip if no known services provided
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for service_name in contract.services:
                if service_name not in self._known_services:
                    result.warnings.append(
                        f"Unknown service '{service_name}' required by node '{name}'"
                    )
    
    def _validate_reachability(self, result: ValidationResult) -> None:
        """Check for orphan/unreachable nodes."""
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            # Check for orphan (no supervisor)
            if not contract.supervisor:
                result.warnings.append(
                    f"Node '{name}' has no supervisor (orphan)"
                )
                continue
            
            # Check for unreachable (no trigger conditions)
            if not contract.trigger_conditions:
                result.warnings.append(
                    f"Node '{name}' has no trigger conditions (may be unreachable)"
                )
    
    def _report_shared_writers(self, result: ValidationResult) -> None:
        """Report slices with multiple writers (informational)."""
        shared_writers = self.get_shared_writers()
        
        for slice_name, writers in shared_writers.items():
            if len(writers) > 1:
                writers_str = ", ".join(sorted(writers))
                result.info.append(
                    f"Shared writers for '{slice_name}': {writers_str}"
                )

    def _apply_strict_mode(self, result: ValidationResult) -> None:
        """Convert warnings to errors in strict mode."""
        if not self._strict or not result.warnings:
            return
        result.errors.extend([f"STRICT: {warning}" for warning in result.warnings])
        result.warnings = []
    
    def get_shared_writers(self) -> dict[str, list[str]]:
        """Get all slices and their writers.
        
        Returns:
            {slice_name: [node_names that write to it]}
        """
        writers: dict[str, list[str]] = {}
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for slice_name in contract.writes:
                if slice_name not in writers:
                    writers[slice_name] = []
                writers[slice_name].append(name)
        
        return writers
    
    def get_slice_readers(self) -> dict[str, list[str]]:
        """Get all slices and their readers.
        
        Returns:
            {slice_name: [node_names that read from it]}
        """
        readers: dict[str, list[str]] = {}
        
        for name in self._registry.get_all_nodes():
            contract = self._registry.get_contract(name)
            if not contract:
                continue
            
            for slice_name in contract.reads:
                if slice_name not in readers:
                    readers[slice_name] = []
                readers[slice_name].append(name)
        
        return readers
    
    def get_unused_slices(self) -> dict[str, str]:
        """Find slices that are written but never read, or vice versa.
        
        Returns:
            {slice_name: "write_only" | "read_only"}
        """
        writers = self.get_shared_writers()
        readers = self.get_slice_readers()
        
        all_slices = set(writers.keys()) | set(readers.keys())
        unused: dict[str, str] = {}
        
        for slice_name in all_slices:
            has_writers = slice_name in writers and len(writers[slice_name]) > 0
            has_readers = slice_name in readers and len(readers[slice_name]) > 0
            
            if has_writers and not has_readers:
                unused[slice_name] = "write_only"
            elif has_readers and not has_writers:
                # Read-only is only a concern for non-input slices
                if slice_name != "request":
                    unused[slice_name] = "read_only"
        
        return unused
