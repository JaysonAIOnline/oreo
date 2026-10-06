"""
GIR (Graph Intermediate Representation) - Type System
Type definitions, inference, and checking for the OREO language.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Union, Callable
from abc import ABC, abstractmethod
from uuid import uuid4


class PrimitiveKind(Enum):
    """Primitive type kinds."""
    UNIT = "unit"       # ()
    BOOL = "bool"       # true | false
    INT = "int"         # signed integer
    UINT = "uint"       # unsigned integer
    FLOAT = "float"     # IEEE 754 float
    CHAR = "char"       # Unicode code point
    STRING = "string"   # UTF-8 string
    BYTES = "bytes"     # raw byte sequence
    NEVER = "never"     # bottom type (no values)
    ANY = "any"         # top type (all values)


class CompositeKind(Enum):
    """Composite type kinds."""
    TUPLE = "tuple"           # (T1, T2, ...)
    RECORD = "record"         # { field: Type, ... }
    SUM = "sum"               # Variant | Variant2 | ...
    ARRAY = "array"           # [T; n] or [T]
    MAP = "map"               # Map<K, V>
    OPTION = "option"         # Option<T> = Some(T) | None
    RESULT = "result"         # Result<T, E> = Ok(T) | Err(E)
    FUNCTION = "function"     # Fn(Params) -> Ret [Effects]


class EffectKind(Enum):
    """Built-in effect kinds."""
    IO = "io"                 # Input/output operations
    STATE = "state"           # Mutable state access
    EXCEPTION = "exception"   # Exception throwing/catching
    ASYNC = "async"           # Asynchronous operations
    RESOURCE = "resource"     # Resource acquisition/release
    PANIC = "panic"           # Panic/unrecoverable error
    NONDET = "nondet"         # Non-determinism


@dataclass
class TypeVar:
    """Type variable for generics."""
    name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    constraints: List['Type'] = field(default_factory=list)  # Trait bounds
    variance: str = "invariant"  # covariant, contravariant, invariant
    
    def __str__(self):
        constraints = f": {', '.join(str(c) for c in self.constraints)}" if self.constraints else ""
        return f"{self.name}{constraints}"
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, TypeVar):
            return False
        return self.id == other.id


@dataclass
class Type(ABC):
    """Base type class."""
    id: str = field(default_factory=lambda: str(uuid4()), kw_only=True)
    metadata: Dict[str, Any] = field(default_factory=dict, kw_only=True)
    
    @abstractmethod
    def __str__(self) -> str:
        pass
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Type):
            return False
        return self.id == other.id
    
    def substitute(self, subst: Dict[TypeVar, 'Type']) -> 'Type':
        """Apply type substitution."""
        return self
    
    def free_vars(self) -> Set[TypeVar]:
        """Return free type variables in this type."""
        return set()
    
    def occurs_in(self, var: TypeVar) -> bool:
        """Check if type variable occurs in this type."""
        return var in self.free_vars()


@dataclass
class PrimitiveType(Type):
    kind: PrimitiveKind
    bit_width: Optional[int] = None  # for Int/UInt/Float
    
    def __str__(self):
        if self.kind in (PrimitiveKind.INT, PrimitiveKind.UINT, PrimitiveKind.FLOAT):
            if self.bit_width:
                return f"{self.kind.value}{self.bit_width}"
        return self.kind.value
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        return self


@dataclass
class TypeVarType(Type):
    var: TypeVar
    
    def __str__(self):
        return str(self.var)
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        return subst.get(self.var, self)
    
    def free_vars(self) -> Set[TypeVar]:
        return {self.var}
    
    def occurs_in(self, var: TypeVar) -> bool:
        return self.var == var


@dataclass
class CompositeType(Type):
    kind: CompositeKind
    type_args: List[Type] = field(default_factory=list)
    fields: List['RecordField'] = field(default_factory=list)  # for RECORD
    variants: List['Variant'] = field(default_factory=list)    # for SUM
    is_mutable: bool = False
    
    def __str__(self):
        if self.kind == CompositeKind.TUPLE:
            args = ", ".join(str(a) for a in self.type_args)
            return f"({args})"
        elif self.kind == CompositeKind.RECORD:
            fields = ", ".join(f"{f.name}: {f.type}" for f in self.fields)
            return f"{{{fields}}}"
        elif self.kind == CompositeKind.SUM:
            variants = " | ".join(str(v) for v in self.variants)
            return variants
        elif self.kind == CompositeKind.ARRAY:
            if len(self.type_args) == 1:
                return f"[{self.type_args[0]}]"
            elif len(self.type_args) == 2:
                return f"[{self.type_args[0]}; {self.type_args[1]}]"
            return "[]"
        elif self.kind == CompositeKind.MAP:
            if len(self.type_args) == 2:
                return f"Map<{self.type_args[0]}, {self.type_args[1]}>"
            return "Map"
        elif self.kind == CompositeKind.OPTION:
            if self.type_args:
                return f"Option<{self.type_args[0]}>"
            return "Option"
        elif self.kind == CompositeKind.RESULT:
            if len(self.type_args) == 2:
                return f"Result<{self.type_args[0]}, {self.type_args[1]}>"
            return "Result"
        elif self.kind == CompositeKind.FUNCTION:
            if len(self.type_args) >= 2:
                params = self.type_args[:-1]
                ret = self.type_args[-1]
                params_str = ", ".join(str(p) for p in params)
                return f"Fn({params_str}) -> {ret}"
            return "Fn"
        return self.kind.value
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        return CompositeType(
            kind=self.kind,
            type_args=[a.substitute(subst) for a in self.type_args],
            fields=[RecordField(f.name, f.type.substitute(subst), f.is_mutable) for f in self.fields],
            variants=[Variant(v.name, [t.substitute(subst) for t in v.type_args]) for v in self.variants],
            is_mutable=self.is_mutable
        )
    
    def free_vars(self) -> Set[TypeVar]:
        vars = set()
        for arg in self.type_args:
            vars.update(arg.free_vars())
        for field in self.fields:
            vars.update(field.type.free_vars())
        for variant in self.variants:
            for t in variant.type_args:
                vars.update(t.free_vars())
        return vars


@dataclass
class RecordField:
    name: str
    type: Type
    is_mutable: bool = False
    default: Optional[Any] = None
    
    def __str__(self):
        mut = "mut " if self.is_mutable else ""
        default_str = f" = {self.default}" if self.default is not None else ""
        return f"{mut}{self.name}: {self.type}{default_str}"


@dataclass
class Variant:
    name: str
    type_args: List[Type] = field(default_factory=list)
    
    def __str__(self):
        if self.type_args:
            args = ", ".join(str(t) for t in self.type_args)
            return f"{self.name}({args})"
        return self.name


@dataclass
class FunctionType(Type):
    """Function type with explicit effect row."""
    params: List[Type] = field(default_factory=list)
    return_type: Type = field(default_factory=lambda: PrimitiveType(PrimitiveKind.UNIT))
    effects: List['Effect'] = field(default_factory=list)
    is_async: bool = False
    is_pure: bool = False  # no effects
    
    def __str__(self):
        params_str = ", ".join(str(p) for p in self.params)
        effects_str = ""
        if self.effects:
            effects_str = f" [{', '.join(str(e) for e in self.effects)}]"
        async_str = "async " if self.is_async else ""
        pure_str = "pure " if self.is_pure else ""
        return f"{async_str}{pure_str}Fn({params_str}) -> {self.return_type}{effects_str}"
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        return FunctionType(
            params=[p.substitute(subst) for p in self.params],
            return_type=self.return_type.substitute(subst),
            effects=[e.substitute(subst) for e in self.effects],
            is_async=self.is_async,
            is_pure=self.is_pure
        )
    
    def free_vars(self) -> Set[TypeVar]:
        vars = set()
        for p in self.params:
            vars.update(p.free_vars())
        vars.update(self.return_type.free_vars())
        for e in self.effects:
            vars.update(e.free_vars())
        return vars


@dataclass
class Effect(Type):
    """Effect type (row polymorphism)."""
    name: str
    type_args: List[Type] = field(default_factory=list)
    is_row_var: bool = False  # for effect row polymorphism
    row_var: Optional[TypeVar] = None  # the row variable if polymorphic
    
    def __str__(self):
        if self.is_row_var and self.row_var:
            return f"ρ{self.row_var.name}"
        if self.type_args:
            args = ", ".join(str(t) for t in self.type_args)
            return f"{self.name}<{args}>"
        return self.name
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        if self.is_row_var and self.row_var:
            if self.row_var in subst:
                return subst[self.row_var]
        return Effect(
            name=self.name,
            type_args=[t.substitute(subst) for t in self.type_args],
            is_row_var=self.is_row_var,
            row_var=self.row_var
        )
    
    def free_vars(self) -> Set[TypeVar]:
        vars = set()
        for t in self.type_args:
            vars.update(t.free_vars())
        if self.row_var:
            vars.add(self.row_var)
        return vars


@dataclass
class ForAllType(Type):
    """Universal quantification (generics)."""
    type_vars: List[TypeVar] = field(default_factory=list)
    body: Type = field(default_factory=lambda: PrimitiveType(PrimitiveKind.ANY))
    where_clauses: List['WhereClause'] = field(default_factory=list)
    
    def __str__(self):
        vars_str = ", ".join(str(v) for v in self.type_vars)
        where_str = ""
        if self.where_clauses:
            where_str = f" where {', '.join(str(w) for w in self.where_clauses)}"
        return f"forall<{vars_str}>. {self.body}{where_str}"
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        # Remove bound variables from substitution
        new_subst = {k: v for k, v in subst.items() if k not in self.type_vars}
        return ForAllType(
            type_vars=self.type_vars,
            body=self.body.substitute(new_subst),
            where_clauses=self.where_clauses
        )
    
    def free_vars(self) -> Set[TypeVar]:
        vars = self.body.free_vars()
        # Remove bound variables
        return vars - set(self.type_vars)


@dataclass
class WhereClause:
    """Trait/constraint bound."""
    type_var: TypeVar
    constraints: List[Type] = field(default_factory=list)  # Trait types
    
    def __str__(self):
        constraints_str = " + ".join(str(c) for c in self.constraints)
        return f"{self.type_var}: {constraints_str}"


@dataclass
class AliasType(Type):
    """Type alias."""
    name: str
    type_args: List[Type] = field(default_factory=list)
    target: Optional[Type] = None  # resolved target type
    
    def __str__(self):
        if self.type_args:
            args = ", ".join(str(t) for t in self.type_args)
            return f"{self.name}<{args}>"
        return self.name
    
    def substitute(self, subst: Dict[TypeVar, Type]) -> Type:
        if self.target:
            return self.target.substitute(subst)
        return AliasType(
            name=self.name,
            type_args=[t.substitute(subst) for t in self.type_args],
            target=self.target
        )
    
    def free_vars(self) -> Set[TypeVar]:
        vars = set()
        for t in self.type_args:
            vars.update(t.free_vars())
        if self.target:
            vars.update(self.target.free_vars())
        return vars


# --- Built-in Types ---

UNIT = PrimitiveType(PrimitiveKind.UNIT)
BOOL = PrimitiveType(PrimitiveKind.BOOL)
INT = PrimitiveType(PrimitiveKind.INT)
UINT = PrimitiveType(PrimitiveKind.UINT)
FLOAT = PrimitiveType(PrimitiveKind.FLOAT)
CHAR = PrimitiveType(PrimitiveKind.CHAR)
STRING = PrimitiveType(PrimitiveKind.STRING)
BYTES = PrimitiveType(PrimitiveKind.BYTES)
NEVER = PrimitiveType(PrimitiveKind.NEVER)
ANY = PrimitiveType(PrimitiveKind.ANY)

# Common sized types
INT8 = PrimitiveType(PrimitiveKind.INT, 8)
INT16 = PrimitiveType(PrimitiveKind.INT, 16)
INT32 = PrimitiveType(PrimitiveKind.INT, 32)
INT64 = PrimitiveType(PrimitiveKind.INT, 64)
INT128 = PrimitiveType(PrimitiveKind.INT, 128)

UINT8 = PrimitiveType(PrimitiveKind.UINT, 8)
UINT16 = PrimitiveType(PrimitiveKind.UINT, 16)
UINT32 = PrimitiveType(PrimitiveKind.UINT, 32)
UINT64 = PrimitiveType(PrimitiveKind.UINT, 64)
UINT128 = PrimitiveType(PrimitiveKind.UINT, 128)

FLOAT16 = PrimitiveType(PrimitiveKind.FLOAT, 16)
FLOAT32 = PrimitiveType(PrimitiveKind.FLOAT, 32)
FLOAT64 = PrimitiveType(PrimitiveKind.FLOAT, 64)
FLOAT80 = PrimitiveType(PrimitiveKind.FLOAT, 80)


def make_tuple(*types: Type) -> CompositeType:
    return CompositeType(CompositeKind.TUPLE, list(types))


def make_record(*fields: RecordField) -> CompositeType:
    return CompositeType(CompositeKind.RECORD, fields=list(fields))


def make_sum(*variants: Variant) -> CompositeType:
    return CompositeType(CompositeKind.SUM, variants=list(variants))


def make_array(element_type: Type, size: Optional[int] = None) -> CompositeType:
    if size is not None:
        return CompositeType(CompositeKind.ARRAY, [element_type, PrimitiveType(PrimitiveKind.INT)])
    return CompositeType(CompositeKind.ARRAY, [element_type])


def make_map(key_type: Type, value_type: Type) -> CompositeType:
    return CompositeType(CompositeKind.MAP, [key_type, value_type])


def make_option(inner_type: Type) -> CompositeType:
    return CompositeType(CompositeKind.OPTION, [inner_type])


def make_result(ok_type: Type, err_type: Type) -> CompositeType:
    return CompositeType(CompositeKind.RESULT, [ok_type, err_type])


def make_function(params: List[Type], return_type: Type, effects: List[Effect] = None) -> FunctionType:
    return FunctionType(
        params=params,
        return_type=return_type,
        effects=effects or [],
        is_pure=(effects is None or len(effects) == 0)
    )


# --- Effect Instances ---

EFFECT_IO = Effect("IO")
EFFECT_STATE = Effect("State")
EFFECT_EXCEPTION = Effect("Exception")
EFFECT_ASYNC = Effect("Async")
EFFECT_RESOURCE = Effect("Resource")
EFFECT_PANIC = Effect("Panic")
EFFECT_NONDET = Effect("NonDet")


def make_effect(name: str, *type_args: Type) -> Effect:
    return Effect(name, list(type_args))


def make_effect_row(*effects: Effect) -> List[Effect]:
    return list(effects)


# --- Type Inference Context ---

@dataclass
class TypeScheme:
    """A type scheme (for let-polymorphism)."""
    type_vars: List[TypeVar]
    type: Type
    
    def instantiate(self, fresh_var_gen: Callable[[], TypeVar]) -> Type:
        """Instantiate with fresh type variables."""
        subst = {}
        for var in self.type_vars:
            new_var = fresh_var_gen()
            new_var.name = var.name
            new_var.constraints = var.constraints.copy()
            new_var.variance = var.variance
            subst[var] = TypeVarType(new_var)
        return self.type.substitute(subst)
    
    def generalize(self, free_vars: Set[TypeVar]) -> 'TypeScheme':
        """Generalize over free variables not in free_vars."""
        scheme_vars = self.type.free_vars() - free_vars
        return TypeScheme(list(scheme_vars), self.type)


@dataclass
class TypeEnvironment:
    """Typing environment."""
    variables: Dict[str, TypeScheme] = field(default_factory=dict)
    type_aliases: Dict[str, Type] = field(default_factory=dict)
    traits: Dict[str, 'Trait'] = field(default_factory=dict)
    parent: Optional['TypeEnvironment'] = None
    
    def lookup(self, name: str) -> Optional[TypeScheme]:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def define(self, name: str, scheme: TypeScheme):
        self.variables[name] = scheme
    
    def define_type(self, name: str, type_: Type):
        self.type_aliases[name] = type_
    
    def lookup_type(self, name: str) -> Optional[Type]:
        if name in self.type_aliases:
            return self.type_aliases[name]
        if self.parent:
            return self.parent.lookup_type(name)
        return None
    
    def child(self) -> 'TypeEnvironment':
        return TypeEnvironment(parent=self)


@dataclass
class Trait:
    """Type class / trait definition."""
    name: str
    type_params: List[TypeVar] = field(default_factory=list)
    methods: List['TraitMethod'] = field(default_factory=list)
    supertraits: List[Type] = field(default_factory=list)
    
    def __str__(self):
        params = ", ".join(str(p) for p in self.type_params)
        return f"trait {self.name}<{params}>"


@dataclass
class TraitMethod:
    name: str
    type: FunctionType
    default_impl: Optional[Any] = None  # optional default implementation


# --- Unification ---

class UnificationError(Exception):
    def __init__(self, message: str, expected: Type, actual: Type):
        self.message = message
        self.expected = expected
        self.actual = actual
        super().__init__(f"{message}: expected {expected}, got {actual}")


def unify(expected: Type, actual: Type, subst: Dict[TypeVar, Type] = None) -> Dict[TypeVar, Type]:
    """
    Unify two types, returning a substitution.
    Raises UnificationError if types cannot be unified.
    """
    if subst is None:
        subst = {}
    
    # Apply current substitution
    expected = expected.substitute(subst)
    actual = actual.substitute(subst)
    
    # Same type variable?
    if isinstance(expected, TypeVarType) and isinstance(actual, TypeVarType):
        if expected.var == actual.var:
            return subst
    
    # Expected is type variable
    if isinstance(expected, TypeVarType):
        if expected.var.occurs_in(actual):
            raise UnificationError("Occurs check failed", expected, actual)
        subst[expected.var] = actual
        return subst
    
    # Actual is type variable
    if isinstance(actual, TypeVarType):
        if actual.var.occurs_in(expected):
            raise UnificationError("Occurs check failed", expected, actual)
        subst[actual.var] = expected
        return subst
    
    # Both are primitive types
    if isinstance(expected, PrimitiveType) and isinstance(actual, PrimitiveType):
        # ANY is the top type: unifies with everything.
        if expected.kind == PrimitiveKind.ANY or actual.kind == PrimitiveKind.ANY:
            return subst
        if expected.kind != actual.kind:
            raise UnificationError("Primitive kind mismatch", expected, actual)
        if expected.kind in (PrimitiveKind.INT, PrimitiveKind.UINT, PrimitiveKind.FLOAT):
            if expected.bit_width != actual.bit_width:
                raise UnificationError("Bit width mismatch", expected, actual)
        return subst
    
    # Both are composite types
    if isinstance(expected, CompositeType) and isinstance(actual, CompositeType):
        if expected.kind != actual.kind:
            raise UnificationError("Composite kind mismatch", expected, actual)
        if len(expected.type_args) != len(actual.type_args):
            raise UnificationError("Type argument count mismatch", expected, actual)
        for ea, aa in zip(expected.type_args, actual.type_args):
            unify(ea, aa, subst)
        # Check fields for records
        if expected.kind == CompositeKind.RECORD:
            if len(expected.fields) != len(actual.fields):
                raise UnificationError("Record field count mismatch", expected, actual)
            for ef, af in zip(expected.fields, actual.fields):
                if ef.name != af.name:
                    raise UnificationError(f"Record field name mismatch: {ef.name} vs {af.name}", expected, actual)
                unify(ef.type, af.type, subst)
        # Check variants for sums
        if expected.kind == CompositeKind.SUM:
            if len(expected.variants) != len(actual.variants):
                raise UnificationError("Sum variant count mismatch", expected, actual)
            for ev, av in zip(expected.variants, actual.variants):
                if ev.name != av.name:
                    raise UnificationError(f"Sum variant name mismatch: {ev.name} vs {av.name}", expected, actual)
                if len(ev.type_args) != len(av.type_args):
                    raise UnificationError("Variant type arg count mismatch", expected, actual)
                for et, at in zip(ev.type_args, av.type_args):
                    unify(et, at, subst)
        return subst
    
    # Both are function types
    if isinstance(expected, FunctionType) and isinstance(actual, FunctionType):
        if len(expected.params) != len(actual.params):
            raise UnificationError("Function parameter count mismatch", expected, actual)
        for ep, ap in zip(expected.params, actual.params):
            unify(ep, ap, subst)
        unify(expected.return_type, actual.return_type, subst)
        # Effects: actual must be subset of expected (contravariant in effects)
        # For now, require exact match
        if len(expected.effects) != len(actual.effects):
            raise UnificationError("Effect count mismatch", expected, actual)
        for ee, ae in zip(expected.effects, actual.effects):
            unify(ee, ae, subst)
        return subst
    
    # Both are effects
    if isinstance(expected, Effect) and isinstance(actual, Effect):
        if expected.name != actual.name:
            raise UnificationError("Effect name mismatch", expected, actual)
        if len(expected.type_args) != len(actual.type_args):
            raise UnificationError("Effect type arg count mismatch", expected, actual)
        for ea, aa in zip(expected.type_args, actual.type_args):
            unify(ea, aa, subst)
        return subst
    
    # ForAll types
    if isinstance(expected, ForAllType) and isinstance(actual, ForAllType):
        # Skolemize - create fresh variables for each
        # For now, require same structure
        if len(expected.type_vars) != len(actual.type_vars):
            raise UnificationError("ForAll quantifier count mismatch", expected, actual)
        # Substitute fresh vars and unify bodies
        fresh_vars = [TypeVar(f"_skolem{i}") for i in range(len(expected.type_vars))]
        expected_subst = {v: TypeVarType(fv) for v, fv in zip(expected.type_vars, fresh_vars)}
        actual_subst = {v: TypeVarType(fv) for v, fv in zip(actual.type_vars, fresh_vars)}
        return unify(expected.body.substitute(expected_subst), actual.body.substitute(actual_subst), subst)
    
    # Alias types - resolve and unify
    if isinstance(expected, AliasType) and expected.target:
        return unify(expected.target, actual, subst)
    if isinstance(actual, AliasType) and actual.target:
        return unify(expected, actual.target, subst)
    
    raise UnificationError("Cannot unify", expected, actual)


def apply_subst(type_: Type, subst: Dict[TypeVar, Type]) -> Type:
    """Apply substitution to type."""
    return type_.substitute(subst)


# --- Type Checking ---

@dataclass
class TypeError(Exception):
    message: str
    node_id: Optional[str] = None
    expected: Optional[Type] = None
    actual: Optional[Type] = None


def check_type(expected: Type, actual: Type, context: str = "") -> List[TypeError]:
    """Check that actual type matches expected type."""
    errors = []
    try:
        unify(expected, actual)
    except UnificationError as e:
        errors.append(TypeError(
            message=f"{context}: {e.message}",
            expected=e.expected,
            actual=e.actual
        ))
    return errors


# --- Trait Resolution ---

def resolve_trait(trait_name: str, type_args: List[Type], env: TypeEnvironment) -> Optional[Trait]:
    """Resolve a trait implementation for given type arguments."""
    trait = env.traits.get(trait_name)
    if not trait:
        return None
    # TODO: implement trait resolution with impl blocks
    return trait


def check_trait_bounds(type_: Type, bounds: List[Type], env: TypeEnvironment) -> List[TypeError]:
    """Check that a type satisfies all trait bounds."""
    errors = []
    for bound in bounds:
        # TODO: implement trait bound checking
        pass
    return errors