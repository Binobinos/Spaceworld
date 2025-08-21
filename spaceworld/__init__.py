"""
Spaceworld CLI is a new generation Cli framework.

for convenient development of your teams written in Python 3.12+
with support for asynchronous commands
"""

from typing import Annotated, Any, Optional, Union

from .annotation_manager import AnnotationManager
from .commands.base_command import BaseCommand
from .exceptions import (
    AnnotationsError,
    CommandCreateError,
    CommandError,
    ModuleCreateError,
    ModuleError,
    SpaceWorldError,
    SubModuleCreateError,
)
from .module.base_module import BaseModule
from .spaceworld_cli import SpaceWorld, run
from .writers.my_writer import MyWriter
from .writers.writer import Writer

__all__ = (
    "AnnotationManager",
    "AnnotationsError",
    "SpaceWorld",
    "BaseModule",
    "BaseCommand",
    "run",
    "MyWriter",
    "Writer",
    "Annotated",
    "Union",
    "Optional",
    "Any",
    "ModuleError",
    "ModuleCreateError",
    "CommandError",
    "SpaceWorldError",
    "CommandCreateError",
    "SubModuleCreateError",
)

__author__ = "binobinos"
