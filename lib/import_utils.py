#!/usr/bin/env python3
"""Import utilities with error handling for fplaunchwrapper.

Provides decorators and context managers for handling ImportError
consistently across the codebase.
"""

from __future__ import annotations

import functools
from typing import Callable, TypeVar, Any, Optional

T = TypeVar('T')


class ImportErrorHandler:
    """Handler for ImportError with consistent error messaging.
    
    Usage:
        handler = ImportErrorHandler(console_err)
        handler.require("lib.generate", "WrapperGenerator")
    """
    
    def __init__(self, console_err: Any):
        self.console_err = console_err
    
    def require(self, module: str, name: Optional[str] = None) -> Any:
        """Import a module or object, raising SystemExit on failure.
        
        Args:
            module: Module path to import
            name: Optional object name to import from module
            
        Returns:
            The imported module or object
            
        Raises:
            SystemExit: If import fails
        """
        try:
            import importlib
            imported = importlib.import_module(module)
            if name:
                return getattr(imported, name)
            return imported
        except ImportError as e:
            desc = f"{module}.{name}" if name else module
            self.console_err.print(f"[red]Error:[/red] Failed to import {desc}: {e}")
            raise SystemExit(1)


def safe_import(module: str, name: Optional[str] = None, default: Any = None) -> Any:
    """Safely import a module or object, returning default on failure.
    
    Args:
        module: Module path to import
        name: Optional object name to import from module
        default: Value to return if import fails
        
    Returns:
        The imported module/object, or default on failure
    """
    try:
        import importlib
        imported = importlib.import_module(module)
        if name:
            return getattr(imported, name)
        return imported
    except ImportError:
        return default