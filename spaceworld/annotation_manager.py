"""The AnnotationManager implementation is a class for annotations in SpaceWorld."""

import inspect
import types
import typing
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    get_args,
    get_origin,
)
from uuid import UUID

from ._types import (
    AnnotateArgType,
    Arg,
    Args,
    AttributeType,
    CacheType,
    Kwargs,
    NewArgs,
    NewKwargs,
    Parameter,
    Parameters,
    Transformer,
    TupleArgs,
    UserAny,
)
from .exceptions import AnnotationsError


class AnnotationManager:
    """
    A class for creating a command container and annotation processing in SpaceWorld.

    Supports annotations:
        - Union annotations
        - Annotated annotations
        - Enum annotations
        - Literal annotations
        - Callable annotations, including:
            - lambda functions with the signature Callable[[Any], Any]
    """

    __slots__ = ("annotations", "args_cache", "transformers")

    def __init__(self) -> None:
        """
        Initialize a new module instance.

        Returns:
            None
        """
        self.annotations: dict[str, AttributeType] = {}
        self.args_cache: dict[TupleArgs, CacheType] = {}
        self.transformers: dict[
            AttributeType | Transformer | Any | None, Transformer
        ] = {
            int: int,
            float: float,
            Decimal: Decimal,
            datetime: self._convert_datetime,
            UUID: UUID,
            str: str,
            bool: self._convert_to_bool,
            Path: Path,
            inspect.Parameter.empty: lambda x: x,
            Any: lambda x: x,
            None: lambda x: x,
        }

    def add_custom_transformer(
        self, type_: AttributeType, transformer: Transformer
    ) -> Transformer:
        """
        Add a custom handler for annotations.

        Args:
            type_ (): The type in the annotation
            transformer (): Handler

        Return:
            Handler's return.
        """
        if type_ in self.transformers:
            raise AnnotationsError(f"Transformer for {type_} already exists")
        self.transformers[type_] = transformer
        return self.transformers[type_]

    def annotate(
        self, annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Convert the annotation argument to the final value.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        origin = get_origin(annotation)
        match origin:
            case types.UnionType | typing.Union:
                return self._annotate_union(annotation, arg)
            case typing.Annotated:
                return self._annotate_annotated(annotation, arg)
            case typing.Literal:
                return self._annotate_literal(annotation, arg)
            case None:
                return self._annotate_base_type(annotation, arg)
            case _:
                raise AnnotationsError(
                    f"Unsupported type in the annotation: {annotation}"
                )

    def _annotate_union(
        self, annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate the Union type.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        errors = []
        for param_type in get_args(annotation):
            try:
                arg = self.annotate(param_type, arg)
                return arg
            except AnnotationsError as error:
                errors.append(error)
        errors_mes = [
            f"{num} Error: {error}" for num, error in enumerate(errors, start=1)
        ]
        message = f"\n\t{'\n\t'.join(errors_mes)}"
        message = (
            f"None of the types in the Union are suitable. List of errors: {message}"
        )
        raise AnnotationsError(message) from errors[-1]

    def _annotate_annotated(
        self, annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate the Annotated type.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        for param_type in get_args(annotation):
            try:
                arg = self.annotate(param_type, arg)
            except Exception as error:
                message = f"Error in the Annotated validation for `{arg}`: {error}, {type(error)}"
                raise AnnotationsError(message) from error
        return arg

    @staticmethod
    def _annotate_literal(
        annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate the Literal type.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        args = get_args(annotation)
        if arg not in args:
            message = f"The value of `{arg}` does not match Literal[{'/'.join(args)}]"
            raise AnnotationsError(message)
        return arg

    def _annotate_base_type(
        self, annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate the basic types.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        transformers = self.transformers
        if annotation in transformers:
            func = transformers[annotation]
            try:
                return func(arg)
            except Exception as error:
                msg = f"Couldn't convert to `{func.__name__}`: {error}"
                raise AnnotationsError(msg) from error
        return self._annotate_normal_type(annotation, arg)

    def _annotate_normal_type(
        self, annotation: AttributeType, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate basic types and callable objects.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        if isinstance(annotation, str):
            return arg
        if callable(annotation):
            return self._annotate_callable(annotation, arg)
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return self._annotate_enum(annotation, arg)
        raise AnnotationsError(f"Unsupported type in the annotation:{annotation}")

    @staticmethod
    def _annotate_enum(annotation: UserAny, arg: AnnotateArgType) -> AnnotateArgType:
        """
        Annotate Enum and string annotations.

        Args:
            annotation (): Annotation
            arg(): Argument

        Returns:
            The final argument
        """
        valid_values = [e.value for e in annotation]
        if arg not in valid_values:
            message = f"The value of `{arg}` does not match the Enum[{'/'.join(valid_values)}]"
            raise AnnotationsError(message)
        return annotation(arg)

    @staticmethod
    def _convert_to_bool(value: AnnotateArgType) -> bool:
        """
        Convert the value to bool.

        Args:
            value (): Argument

        Returns:
            bool object
        """
        return str(value).lower() in {"true", "yes", "y"}

    @staticmethod
    def _convert_datetime(value: AnnotateArgType) -> datetime:
        """
        Convert the argument to a datatime object.

        Args:
            value (): Argument

        Returns:
            datatime object
        """
        try:
            return datetime.fromisoformat(value)
        except ValueError as e:
            raise AnnotationsError(f"Invalid ISO date: {value}") from e

    def _annotate_callable(
        self, func: Transformer, arg: AnnotateArgType
    ) -> AnnotateArgType:
        """
        Annotate callable objects.

        Args:
            func(): A callable object
            arg(): Argument

        Returns:
            The final value after the transformations
        """
        try:
            if func.__name__ == "<lambda>":
                return self._annotate_lambda(func, arg)
            return func(arg) or arg
        except Exception as error:
            raise AnnotationsError(f"Arg: {arg}, Error: {error}") from error

    @staticmethod
    def _annotate_lambda(func: Transformer, arg: AnnotateArgType) -> AnnotateArgType:
        """
        Annotate lambda.

        Args:
            arg(): argument
            func(): lambda function

        Returns:
            the final value
        """
        value = func(arg)
        if isinstance(value, BaseException):
            raise AnnotationsError(value)
        if value is False:
            message = f"Failed validation for `{arg}` in the lambda function"
            raise AnnotationsError(message)
        if isinstance(value, bool) and not isinstance(arg, bool):
            return arg
        return value

    def pre_preparing_arg(self, args: TupleArgs) -> tuple[Args, Kwargs]:
        """
        Prepare arguments.

        into a tuple of named and positional arguments
        Args:
            args(): A bare list of arguments

        Returns:
            tuple of named and positional arguments
        """
        positional_args: Args = []
        keyword_args: Kwargs = {}
        for arg in args:
            if not arg.startswith("-"):
                positional_args.append(arg)
                continue
            if not arg.startswith("--"):
                self._preparing_short_flag(arg, positional_args, keyword_args)
                continue
            arg = arg[2:]
            if "=" in arg:
                self._preparing_value_flag(arg, keyword_args)
                continue
            self._preparing_bool_flag(arg, keyword_args)
        return positional_args, keyword_args

    @staticmethod
    def _preparing_bool_flag(arg: Arg, keyword_args: Kwargs) -> None:
        """
        Handle bool flags.

        Args:
            arg (): flag name
            keyword_args (): Dictionary of arguments

        Returns:
            None
        """
        is_no: bool = arg.startswith("no-")
        name: str = arg[3:] if is_no else arg
        if not name:
            raise ValueError("Invalid flag name: Empty name")
        keyword_args[name.replace("-", "_")] = not is_no

    @staticmethod
    def startswith_value(value: str, sym: str) -> bool:
        """
        Determine whether a string begins and ends with a substring.

        Args:
            value (str): value
            sym (str): substring

        Returns:
            Bool
        """
        return value.startswith(sym) and value.endswith(sym)

    def _preparing_value_flag(self, arg: Arg, keyword_args: Kwargs) -> None:
        """
        Prepare flags with the value.

        Args:
            arg(): Argument
            keyword_args (): Dictionary of arguments

        Returns:
            None
        """
        name, _, value = arg.partition("=")
        if not name:
            raise ValueError("Invalid flag name: Empty name")
        vl = value.lower()
        condition = self.startswith_value(vl, '"') or self.startswith_value(vl, "'")
        value = value[1:-1] if condition else value
        vlue = (vl == "true") if vl in ["false", "true"] else value
        keyword_args[name.replace("-", "_")] = vlue

    @staticmethod
    def _preparing_short_flag(
        arg: Arg, positional_args: Args, keyword_args: Kwargs
    ) -> None:
        """
        Prepare a one-letter flag(-h, -abc, and the like).

        Args:
            arg(): single-letter argument
            keyword_args ():  Dictionary of arguments

        Returns:
            None
        """
        try:
            float(arg)
            positional_args.append(arg)
            return
        except ValueError:
            for name in arg[1:]:
                keyword_args[name.lower()] = name.islower()

    def preparing_args(
        self,
        parameters: Parameters,
        positional_args: Args | NewArgs,
        keyword_args: Kwargs | NewKwargs,
    ) -> CacheType:
        """
        Process raw command arguments into properly typed and structured parameters.

        This internal method handles:
        - Argument parsing and validation
        - Type conversion using annotations
        - Positional vs keyword argument separation
        - Default value handling
        - Special flag processing (--no-*, -x, etc.)

        Args:
            positional_args ():
            keyword_args ():
            parameters: List of command parameter specifications from inspection

        Returns:
            tuple: Contains three elements:
                1. List of processed positional arguments
                2. Dictionary of processed keyword arguments
                3. Dictionary of raw flags (for special handling)

        Raises:
            ValueError: When argument value cannot be converted to expected type
            TypeError: When required arguments are missing

        Behavior:
            1. Separates positional args from flags (--prefix)
            2. Processes special flag formats:
               - --flag=value
               - --no-flag (sets False)
               - -xyz (sets x=True, y=True, z=True)
            3. Matches arguments to parameters using:
               - Parameter kind (POSITIONAL, KEYWORD, etc.)
               - Type annotations
               - Default values
            4. Performs type conversion when annotations are present
            5. Validates required parameters are provided


        Notes:
            - Uses inspect.Parameter information for validation
            - Supports variable arguments (*args, **kwargs)
            - Handles type conversion through registered annotations
            - Preserves original flag values for special handling
        """
        positional_args_index: int = 0
        new_args_positional: NewArgs = []
        new_args_keyword: NewKwargs = {}
        for param in parameters:
            param_name = param.name
            match param.kind:
                case param.VAR_POSITIONAL:
                    self.preparing_var_positional(
                        positional_args, new_args_positional, param
                    )
                    positional_args_index = len(positional_args)

                case param.KEYWORD_ONLY if param_name in keyword_args:
                    value = keyword_args.pop(param_name)
                    new_args_keyword[param_name] = self.preparing_annotate(param, value)

                case param.VAR_KEYWORD:
                    self.preparing_var_keyword(keyword_args, new_args_keyword, param)
                case _ if param_name in keyword_args:
                    value = keyword_args.pop(param_name)
                    new_args_keyword[param_name] = self.preparing_annotate(param, value)
                case _ if positional_args_index < len(positional_args):
                    value = positional_args.pop(0)
                    new_args_positional.append(self.preparing_annotate(param, value))

                case _ if param.default != param.empty:
                    self.preparing_default(new_args_positional, new_args_keyword, param)
                case _:
                    raise TypeError(f"Missing required argument: '{param_name}'")
        return new_args_positional, new_args_keyword, keyword_args

    def preparing_annotate(self, prm: Parameter, value: UserAny) -> AnnotateArgType:
        """
        Perform annotation if the annotation is not empty.

        Args:
            prm (): annotation
            value (): Argument

        Returns:
            None
        """
        try:
            return (
                self.annotate(prm.annotation, value)
                if prm.annotation != prm.empty
                else value
            )
        except Exception as e:
            raise ValueError(f"Invalid argument for '{prm.name}': \n{e}") from e

    def preparing_var_positional(
        self, new_args: Args, new_args_positional: NewArgs, prm: Parameter
    ) -> None:
        """
        Prepare *args arguments.

        Args:
            prm(): Parameter class
            new_args(): List of args arguments
            new_args_positional (): List of kwargs arguments

        Returns:
            None
        """
        new_args_positional += (
            [self.annotate(prm.annotation, arg) for arg in new_args]
            if prm.annotation != prm.empty
            else new_args
        )

    def preparing_var_keyword(
        self, lst: Kwargs, new_args_keyword: NewKwargs, prm: Parameter
    ) -> None:
        """
        Prepare **kwargs arguments.

        Args:
            lst (): Kwargs
            new_args_keyword (): List of kwargs arguments
            prm (): Parameter class

        Returns:
            None
        """
        annotate = self.preparing_annotate
        for name, value in lst.items():
            new_args_keyword[name] = annotate(prm, value)

    def preparing_default(
        self, new_args_positional: NewArgs, new_args_keyword: NewKwargs, prm: Parameter
    ) -> None:
        """
        Prepare default values.

        Args:
            new_args_keyword (): List of arguments to kwargs
            new_args_positional (): List of args arguments
            prm(): Parameter class

        Returns:
            None
        """
        value = prm.default
        if prm.kind in {
            prm.KEYWORD_ONLY,
            prm.VAR_KEYWORD,
            prm.POSITIONAL_OR_KEYWORD,
        }:
            new_args_keyword[prm.name] = self.preparing_annotate(prm, value)
            return
        new_args_positional.append(self.preparing_annotate(prm, value))
