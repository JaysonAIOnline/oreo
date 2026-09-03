//! OREO Type System
//!
//! Complete type system implementation with:
//! - Primitive types (Int, UInt, Float, Bool, Char, String, Bytes)
//! - Composite types (Tuple, Record, Sum/ADT, Array, Map, Option, Result)
//! - Function types with effects
//! - Generic types with trait constraints
//! - Type inference support

use super::*;
use std::collections::{HashMap, HashSet};
use std::fmt;
use serde::{Deserialize, Serialize};

/// Complete type representation in OREO
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum OreType {
    /// Primitive types
    Primitive(PrimitiveType),
    /// Tuple type (product)
    Tuple(Vec<OreType>),
    /// Record type (named product)
    Record(Vec<(String, OreType)>),
    /// Sum type / Algebraic Data Type (tagged union)
    Sum(Vec<(String, OreType)>),
    /// Array type (homogeneous sequence)
    Array(Box<OreType>, Option<u64>), // element type, optional fixed size
    /// Map type (associative array)
    Map(Box<OreType>, Box<OreType>), // key type, value type
    /// Option type (Maybe)
    Option(Box<OreType>),
    /// Result type (Ok/Err)
    Result(Box<OreType>, Box<OreType>), // Ok type, Err type
    /// Function type
    Function(FunctionType),
    /// Generic type parameter
    Generic(GenericParam),
    /// Type alias/reference
    Alias(TypeAlias),
    /// Effect type
    Effect(EffectType),
    /// Never type (bottom type)
    Never,
    /// Unknown/inferred type (used during inference)
    Unknown,
}

/// Primitive types with bit widths
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PrimitiveType {
    // Signed integers
    Int8, Int16, Int32, Int64, Int128,
    // Unsigned integers
    UInt8, UInt16, UInt32, UInt64, UInt128,
    // Floats (IEEE 754)
    Float16, Float32, Float64, Float80,
    // Other primitives
    Bool,
    Char,
    String,
    Bytes,
    // Pointer/reference types
    Ptr(Box<PrimitiveType>),      // Raw pointer
    Ref(Box<PrimitiveType>),      // Immutable reference
    MutRef(Box<PrimitiveType>),   // Mutable reference
}

impl PrimitiveType {
    /// Get the size in bits
    pub fn bit_width(&self) -> Option<u32> {
        match self {
            PrimitiveType::Int8 | PrimitiveType::UInt8 => Some(8),
            PrimitiveType::Int16 | PrimitiveType::UInt16 => Some(16),
            PrimitiveType::Int32 | PrimitiveType::UInt32 => Some(32),
            PrimitiveType::Int64 | PrimitiveType::UInt64 => Some(64),
            PrimitiveType::Int128 | PrimitiveType::UInt128 => Some(128),
            PrimitiveType::Float16 => Some(16),
            PrimitiveType::Float32 => Some(32),
            PrimitiveType::Float64 => Some(64),
            PrimitiveType::Float80 => Some(80),
            PrimitiveType::Ptr(_) | PrimitiveType::Ref(_) | PrimitiveType::MutRef(_) => Some(64), // 64-bit pointers
            _ => None, // Bool, Char, String, Bytes are variable-sized
        }
    }

    /// Check if this is a numeric type
    pub fn is_numeric(&self) -> bool {
        matches!(self, 
            PrimitiveType::Int8 | PrimitiveType::Int16 | PrimitiveType::Int32 | 
            PrimitiveType::Int64 | PrimitiveType::Int128 |
            PrimitiveType::UInt8 | PrimitiveType::UInt16 | PrimitiveType::UInt32 |
            PrimitiveType::UInt64 | PrimitiveType::UInt128 |
            PrimitiveType::Float16 | PrimitiveType::Float32 | PrimitiveType::Float64 | PrimitiveType::Float80
        )
    }

    /// Check if this is an integer type
    pub fn is_integer(&self) -> bool {
        matches!(self,
            PrimitiveType::Int8 | PrimitiveType::Int16 | PrimitiveType::Int32 |
            PrimitiveType::Int64 | PrimitiveType::Int128 |
            PrimitiveType::UInt8 | PrimitiveType::UInt16 | PrimitiveType::UInt32 |
            PrimitiveType::UInt64 | PrimitiveType::UInt128
        )
    }

    /// Check if this is a signed integer
    pub fn is_signed(&self) -> bool {
        matches!(self,
            PrimitiveType::Int8 | PrimitiveType::Int16 | PrimitiveType::Int32 |
            PrimitiveType::Int64 | PrimitiveType::Int128
        )
    }

    /// Check if this is a floating point type
    pub fn is_float(&self) -> bool {
        matches!(self,
            PrimitiveType::Float16 | PrimitiveType::Float32 | 
            PrimitiveType::Float64 | PrimitiveType::Float80
        )
    }

    /// Get the default integer type
    pub fn default_int() -> Self {
        PrimitiveType::Int64
    }

    /// Get the default float type
    pub fn default_float() -> Self {
        PrimitiveType::Float64
    }
}

/// Function type with parameters, return type, and effects
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FunctionType {
    pub params: Vec<FunctionParam>,
    pub return_type: Box<OreType>,
    pub effects: EffectSet,
    pub is_async: bool,
    pub is_const: bool,
    pub is_unsafe: bool,
    pub calling_convention: CallingConvention,
}

/// Function parameter
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FunctionParam {
    pub name: String,
    pub param_type: OreType,
    pub is_mut: bool,
    pub default_value: Option<ConstantValue>,
    pub is_variadic: bool,
}

/// Calling convention
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CallingConvention {
    Default,
    C,
    SystemV,
    Fastcall,
    Wasm,
}

/// Generic type parameter
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct GenericParam {
    pub name: String,
    pub constraints: Vec<TraitBound>,
    pub default: Option<OreType>,
    pub variance: Variance,
}

/// Variance of a generic parameter
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Variance {
    Covariant,
    Contravariant,
    Invariant,
    Bivariant,
}

/// Trait bound for generics
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TraitBound {
    pub trait_name: String,
    pub type_params: Vec<OreType>,
    pub is_auto: bool, // auto trait like Send, Sync
}

/// Type alias
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TypeAlias {
    pub name: String,
    pub type_params: Vec<GenericParam>,
    pub target: Box<OreType>,
    pub where_clauses: Vec<WhereClause>,
}

/// Where clause for type constraints
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct WhereClause {
    pub left: OreType,
    pub right: OreType,
    pub kind: WhereClauseKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WhereClauseKind {
    /// Left implements Right (trait bound)
    Implements,
    /// Left equals Right (type equality)
    Equals,
    /// Left is subtype of Right
    Subtype,
}

/// Effect type (for effect polymorphism)
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectType {
    pub name: String,
    pub params: Vec<OreType>,
}

/// Effect set - row-polymorphic set of effects
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectSet {
    pub effects: HashSet<EffectType>,
    pub is_open: bool, // true = row polymorphic (can have more effects)
}

impl EffectSet {
    pub fn new() -> Self {
        EffectSet {
            effects: HashSet::new(),
            is_open: false,
        }
    }

    pub fn open() -> Self {
        EffectSet {
            effects: HashSet::new(),
            is_open: true,
        }
    }

    pub fn add(&mut self, effect: EffectType) {
        self.effects.insert(effect);
    }

    pub fn remove(&mut self, effect: &EffectType) {
        self.effects.remove(effect);
    }

    pub fn contains(&self, effect: &EffectType) -> bool {
        self.effects.contains(effect)
    }

    pub fn union(&self, other: &EffectSet) -> EffectSet {
        let mut result = self.clone();
        result.effects.extend(other.effects.iter().cloned());
        result.is_open = self.is_open || other.is_open;
        result
    }

    pub fn intersects(&self, other: &EffectSet) -> bool {
        !self.effects.is_disjoint(&other.effects)
    }

    pub fn is_subset_of(&self, other: &EffectSet) -> bool {
        self.effects.is_subset(&other.effects)
    }

    pub fn is_pure(&self) -> bool {
        self.effects.is_empty() && !self.is_open
    }

    /// Check if this effect set subsumes another (for effect subtyping)
    pub fn subsumes(&self, other: &EffectSet) -> bool {
        if other.is_open && !self.is_open {
            return false; // Can't subsume open with closed
        }
        other.effects.is_subset(&self.effects)
    }
}

/// Constant values for defaults and compile-time computation
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConstantValue {
    Int(i128),
    UInt(u128),
    Float(String), // Store as string to preserve precision
    Bool(bool),
    Char(char),
    String(String),
    Bytes(Vec<u8>),
    None,
    Tuple(Vec<ConstantValue>),
    Array(Vec<ConstantValue>),
}

/// Type environment for inference
#[derive(Debug, Clone, Default)]
pub struct TypeEnv {
    /// Variable name -> type
    pub variables: HashMap<String, OreType>,
    /// Type variable -> type (for unification)
    pub type_vars: HashMap<String, OreType>,
    /// Trait implementations
    pub traits: HashMap<String, TraitImpl>,
    /// Effect variables
    pub effect_vars: HashMap<String, EffectSet>,
}

/// Trait implementation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraitImpl {
    pub trait_name: String,
    pub for_type: OreType,
    pub methods: HashMap<String, FunctionType>,
    pub where_clauses: Vec<WhereClause>,
}

/// Type inference context
#[derive(Debug, Clone)]
pub struct InferenceContext {
    pub env: TypeEnv,
    pub next_type_var_id: u32,
    pub next_effect_var_id: u32,
    pub constraints: Vec<TypeConstraint>,
    pub effect_constraints: Vec<EffectConstraint>,
}

/// Type constraint for unification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeConstraint {
    pub left: OreType,
    pub right: OreType,
    pub kind: ConstraintKind,
    pub location: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConstraintKind {
    Equals,
    Subtype,
    Supertype,
    Implements, // left implements right (trait)
}

/// Effect constraint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectConstraint {
    pub left: EffectSet,
    pub right: EffectSet,
    pub kind: EffectConstraintKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EffectConstraintKind {
    Subset,    // left ⊆ right
    Superset,  // left ⊇ right
    Equals,
}

impl InferenceContext {
    pub fn new() -> Self {
        InferenceContext {
            env: TypeEnv::default(),
            next_type_var_id: 0,
            next_effect_var_id: 0,
            constraints: Vec::new(),
            effect_constraints: Vec::new(),
        }
    }

    /// Create a fresh type variable
    pub fn fresh_type_var(&mut self, name: Option<String>) -> OreType {
        let id = self.next_type_var_id;
        self.next_type_var_id += 1;
        let name = name.unwrap_or_else(|| format!("T{}", id));
        OreType::Generic(GenericParam {
            name,
            constraints: Vec::new(),
            default: None,
            variance: Variance::Invariant,
        })
    }

    /// Create a fresh effect variable
    pub fn fresh_effect_var(&mut self, name: Option<String>) -> EffectSet {
        let id = self.next_effect_var_id;
        self.next_effect_var_id += 1;
        let name = name.unwrap_or_else(|| format!("E{}", id));
        let mut effects = HashSet::new();
        effects.insert(EffectType { name, params: Vec::new() });
        EffectSet {
            effects,
            is_open: true,
        }
    }

    /// Add a type constraint
    pub fn add_constraint(&mut self, left: OreType, right: OreType, kind: ConstraintKind, location: Option<String>) {
        self.constraints.push(TypeConstraint { left, right, kind, location });
    }

    /// Add an effect constraint
    pub fn add_effect_constraint(&mut self, left: EffectSet, right: EffectSet, kind: EffectConstraintKind) {
        self.effect_constraints.push(EffectConstraint { left, right, kind });
    }
}

/// Type display for pretty printing
impl fmt::Display for OreType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OreType::Primitive(p) => write!(f, "{}", p),
            OreType::Tuple(types) => {
                write!(f, "(")?;
                for (i, t) in types.iter().enumerate() {
                    if i > 0 { write!(f, ", ")?; }
                    write!(f, "{}", t)?;
                }
                if types.len() == 1 { write!(f, ",")?; }
                write!(f, ")")
            }
            OreType::Record(fields) => {
                write!(f, "{{")?;
                for (i, (name, t)) in fields.iter().enumerate() {
                    if i > 0 { write!(f, ", ")?; }
                    write!(f, "{}: {}", name, t)?;
                }
                write!(f, "}}")
            }
            OreType::Sum(variants) => {
                for (i, (name, t)) in variants.iter().enumerate() {
                    if i > 0 { write!(f, " | ")?; }
                    write!(f, "{}", name)?;
                    if !matches!(t, OreType::Tuple(v) if v.is_empty()) {
                        write!(f, "({})", t)?;
                    }
                }
                Ok(())
            }
            OreType::Array(elem, size) => {
                write!(f, "[")?;
                if let Some(sz) = size {
                    write!(f, "{}; ", sz)?;
                }
                write!(f, "{}", elem)?;
                write!(f, "]")
            }
            OreType::Map(k, v) => write!(f, "Map<{}, {}>", k, v),
            OreType::Option(t) => write!(f, "Option<{}>", t),
            OreType::Result(ok, err) => write!(f, "Result<{}, {}>", ok, err),
            OreType::Function(ft) => {
                write!(f, "fn(")?;
                for (i, p) in ft.params.iter().enumerate() {
                    if i > 0 { write!(f, ", ")?; }
                    write!(f, "{}: {}", p.name, p.param_type)?;
                    if p.is_mut { write!(f, " mut")?; }
                }
                write!(f, ") -> {}", ft.return_type)?;
                if !ft.effects.is_pure() {
                    write!(f, " [{}]", ft.effects)?;
                }
                Ok(())
            }
            OreType::Generic(gp) => write!(f, "{}", gp.name),
            OreType::Alias(alias) => write!(f, "{}", alias.name),
            OreType::Effect(eff) => write!(f, "effect {}", eff.name),
            OreType::Never => write!(f, "!"),
            OreType::Unknown => write!(f, "?"),
        }
    }
}

impl fmt::Display for PrimitiveType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PrimitiveType::Int8 => write!(f, "i8"),
            PrimitiveType::Int16 => write!(f, "i16"),
            PrimitiveType::Int32 => write!(f, "i32"),
            PrimitiveType::Int64 => write!(f, "i64"),
            PrimitiveType::Int128 => write!(f, "i128"),
            PrimitiveType::UInt8 => write!(f, "u8"),
            PrimitiveType::UInt16 => write!(f, "u16"),
            PrimitiveType::UInt32 => write!(f, "u32"),
            PrimitiveType::UInt64 => write!(f, "u64"),
            PrimitiveType::UInt128 => write!(f, "u128"),
            PrimitiveType::Float16 => write!(f, "f16"),
            PrimitiveType::Float32 => write!(f, "f32"),
            PrimitiveType::Float64 => write!(f, "f64"),
            PrimitiveType::Float80 => write!(f, "f80"),
            PrimitiveType::Bool => write!(f, "bool"),
            PrimitiveType::Char => write!(f, "char"),
            PrimitiveType::String => write!(f, "string"),
            PrimitiveType::Bytes => write!(f, "bytes"),
            PrimitiveType::Ptr(inner) => write!(f, "*{}", inner),
            PrimitiveType::Ref(inner) => write!(f, "&{}", inner),
            PrimitiveType::MutRef(inner) => write!(f, "&mut {}", inner),
        }
    }
}

impl fmt::Display for EffectSet {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.effects.is_empty() {
            if self.is_open {
                write!(f, "effects...")?;
            } else {
                write!(f, "pure")?;
            }
        } else {
            let mut first = true;
            for eff in &self.effects {
                if !first { write!(f, ", ")?; }
                write!(f, "{}", eff.name)?;
                first = false;
            }
            if self.is_open {
                write!(f, ", ...")?;
            }
        }
        Ok(())
    }
}

impl fmt::Display for FunctionType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "fn(")?;
        for (i, p) in self.params.iter().enumerate() {
            if i > 0 { write!(f, ", ")?; }
            if p.is_mut { write!(f, "mut ")?; }
            write!(f, "{}: {}", p.name, p.param_type)?;
        }
        write!(f, ") -> {}", self.return_type)?;
        if !self.effects.is_pure() {
            write!(f, " [{}]", self.effects)?;
        }
        Ok(())
    }
}

/// Type substitution for inference
#[derive(Debug, Clone, Default)]
pub struct TypeSubstitution {
    pub type_vars: HashMap<String, OreType>,
    pub effect_vars: HashMap<String, EffectSet>,
}

impl TypeSubstitution {
    pub fn apply_type(&self, ty: &OreType) -> OreType {
        match ty {
            OreType::Generic(gp) => {
                self.type_vars.get(&gp.name).cloned().unwrap_or(ty.clone())
            }
            OreType::Function(ft) => {
                let mut new_ft = ft.clone();
                new_ft.params = ft.params.iter().map(|p| FunctionParam {
                    name: p.name.clone(),
                    param_type: self.apply_type(&p.param_type),
                    ..p.clone()
                }).collect();
                new_ft.return_type = Box::new(self.apply_type(&ft.return_type));
                new_ft.effects = self.apply_effects(&ft.effects);
                OreType::Function(new_ft)
            }
            OreType::Tuple(types) => {
                OreType::Tuple(types.iter().map(|t| self.apply_type(t)).collect())
            }
            OreType::Record(fields) => {
                OreType::Record(fields.iter().map(|(n, t)| (n.clone(), self.apply_type(t))).collect())
            }
            OreType::Sum(variants) => {
                OreType::Sum(variants.iter().map(|(n, t)| (n.clone(), self.apply_type(t))).collect())
            }
            OreType::Array(elem, size) => {
                OreType::Array(Box::new(self.apply_type(elem)), *size)
            }
            OreType::Map(k, v) => {
                OreType::Map(Box::new(self.apply_type(k)), Box::new(self.apply_type(v)))
            }
            OreType::Option(t) => {
                OreType::Option(Box::new(self.apply_type(t)))
            }
            OreType::Result(ok, err) => {
                OreType::Result(Box::new(self.apply_type(ok)), Box::new(self.apply_type(err)))
            }
            OreType::Effect(eff) => {
                let mut new_eff = eff.clone();
                new_eff.params = eff.params.iter().map(|p| self.apply_type(p)).collect();
                OreType::Effect(new_eff)
            }
            _ => ty.clone(),
        }
    }

    pub fn apply_effects(&self, effects: &EffectSet) -> EffectSet {
        let mut new_effects = HashSet::new();
        for eff in &effects.effects {
            let mut new_eff = eff.clone();
            new_eff.params = eff.params.iter().map(|p| self.apply_type(p)).collect();
            new_effects.insert(new_eff);
        }
        EffectSet {
            effects: new_effects,
            is_open: effects.is_open,
        }
    }

    pub fn compose(&mut self, other: TypeSubstitution) {
        // Apply other to our existing substitutions first
        for (k, v) in self.type_vars.iter_mut() {
            *v = other.apply_type(v);
        }
        // Then add other's substitutions
        self.type_vars.extend(other.type_vars);
        self.effect_vars.extend(other.effect_vars);
    }
}

/// Builtin types and traits
pub mod builtins {
    use super::*;

    pub fn bool_type() -> OreType {
        OreType::Primitive(PrimitiveType::Bool)
    }

    pub fn int_type() -> OreType {
        OreType::Primitive(PrimitiveType::Int64)
    }

    pub fn float_type() -> OreType {
        OreType::Primitive(PrimitiveType::Float64)
    }

    pub fn string_type() -> OreType {
        OreType::Primitive(PrimitiveType::String)
    }

    pub fn bytes_type() -> OreType {
        OreType::Primitive(PrimitiveType::Bytes)
    }

    pub fn char_type() -> OreType {
        OreType::Primitive(PrimitiveType::Char)
    }

    pub fn unit_type() -> OreType {
        OreType::Tuple(Vec::new())
    }

    pub fn never_type() -> OreType {
        OreType::Never
    }

    pub fn option_type(inner: OreType) -> OreType {
        OreType::Option(Box::new(inner))
    }

    pub fn result_type(ok: OreType, err: OreType) -> OreType {
        OreType::Result(Box::new(ok), Box::new(err))
    }

    pub fn array_type(elem: OreType, size: Option<u64>) -> OreType {
        OreType::Array(Box::new(elem), size)
    }

    pub fn map_type(key: OreType, value: OreType) -> OreType {
        OreType::Map(Box::new(key), Box::new(value))
    }

    pub fn io_effect() -> EffectType {
        EffectType { name: "IO".to_string(), params: Vec::new() }
    }

    pub fn state_effect(loc: OreType) -> EffectType {
        EffectType { name: "State".to_string(), params: vec![loc] }
    }

    pub fn exception_effect(err: OreType) -> EffectType {
        EffectType { name: "Exception".to_string(), params: vec![err] }
    }

    pub fn async_effect() -> EffectType {
        EffectType { name: "Async".to_string(), params: Vec::new() }
    }

    pub fn resource_effect(res: OreType) -> EffectType {
        EffectType { name: "Resource".to_string(), params: vec![res] }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_primitive_type_display() {
        assert_eq!(PrimitiveType::Int32.to_string(), "i32");
        assert_eq!(PrimitiveType::Float64.to_string(), "f64");
        assert_eq!(PrimitiveType::Bool.to_string(), "bool");
        assert_eq!(PrimitiveType::String.to_string(), "string");
    }

    #[test]
    fn test_type_display() {
        let ty = OreType::Primitive(PrimitiveType::Int64);
        assert_eq!(ty.to_string(), "i64");

        let ty = OreType::Option(Box::new(OreType::Primitive(PrimitiveType::Int32)));
        assert_eq!(ty.to_string(), "Option<i32>");

        let ty = OreType::Result(
            Box::new(OreType::Primitive(PrimitiveType::String)),
            Box::new(OreType::Primitive(PrimitiveType::String))
        );
        assert_eq!(ty.to_string(), "Result<string, string>");

        let ty = OreType::Function(FunctionType {
            params: vec![
                FunctionParam { name: "x".to_string(), param_type: OreType::Primitive(PrimitiveType::Int32), is_mut: false, default_value: None, is_variadic: false },
                FunctionParam { name: "y".to_string(), param_type: OreType::Primitive(PrimitiveType::Int32), is_mut: false, default_value: None, is_variadic: false },
            ],
            return_type: Box::new(OreType::Primitive(PrimitiveType::Int32)),
            effects: EffectSet::new(),
            is_async: false,
            is_const: false,
            is_unsafe: false,
            calling_convention: CallingConvention::Default,
        });
        assert_eq!(ty.to_string(), "fn(x: i32, y: i32) -> i32");
    }

    #[test]
    fn test_effect_set_operations() {
        let mut set1 = EffectSet::new();
        let mut set2 = EffectSet::new();
        
        let io = EffectType { name: "IO".to_string(), params: Vec::new() };
        let state = EffectType { name: "State".to_string(), params: Vec::new() };
        
        set1.add(io.clone());
        set2.add(state.clone());
        
        assert!(set1.contains(&io));
        assert!(!set1.contains(&state));
        
        let union = set1.union(&set2);
        assert!(union.contains(&io));
        assert!(union.contains(&state));
        assert!(set1.is_subset_of(&union));
    }

    #[test]
    fn test_effect_subsumption() {
        let mut pure = EffectSet::new();
        let mut io_only = EffectSet::new();
        let mut io_state = EffectSet::new();
        
        io_only.add(EffectType { name: "IO".to_string(), params: Vec::new() });
        io_state.add(EffectType { name: "IO".to_string(), params: Vec::new() });
        io_state.add(EffectType { name: "State".to_string(), params: Vec::new() });
        
        assert!(io_only.subsumes(&pure));
        assert!(io_state.subsumes(&io_only));
        assert!(io_state.subsumes(&pure));
        assert!(!pure.subsumes(&io_only));
    }

    #[test]
    fn test_type_substitution() {
        let mut subst = TypeSubstitution::default();
        let t_var = OreType::Generic(GenericParam {
            name: "T".to_string(),
            constraints: Vec::new(),
            default: None,
            variance: Variance::Invariant,
        });
        
        subst.type_vars.insert("T".to_string(), OreType::Primitive(PrimitiveType::Int32));
        
        let applied = subst.apply_type(&t_var);
        assert_eq!(applied, OreType::Primitive(PrimitiveType::Int32));
    }

    #[test]
    fn test_primitive_properties() {
        assert!(PrimitiveType::Int32.is_numeric());
        assert!(PrimitiveType::Int32.is_integer());
        assert!(PrimitiveType::Int32.is_signed());
        assert!(!PrimitiveType::Int32.is_float());
        
        assert!(PrimitiveType::UInt64.is_numeric());
        assert!(PrimitiveType::UInt64.is_integer());
        assert!(!PrimitiveType::UInt64.is_signed());
        
        assert!(PrimitiveType::Float64.is_numeric());
        assert!(!PrimitiveType::Float64.is_integer());
        assert!(PrimitiveType::Float64.is_float());
        
        assert!(!PrimitiveType::Bool.is_numeric());
        
        assert_eq!(PrimitiveType::Int32.bit_width(), Some(32));
        assert_eq!(PrimitiveType::Float64.bit_width(), Some(64));
        assert_eq!(PrimitiveType::Bool.bit_width(), None);
    }

    #[test]
    fn test_function_type_effects() {
        let io = EffectType { name: "IO".to_string(), params: Vec::new() };
        let mut effects = EffectSet::new();
        effects.add(io);
        
        let ft = FunctionType {
            params: vec![],
            return_type: Box::new(OreType::Primitive(PrimitiveType::Int32)),
            effects,
            is_async: false,
            is_const: false,
            is_unsafe: false,
            calling_convention: CallingConvention::Default,
        };
        
        assert!(!ft.effects.is_pure());
        assert!(ft.effects.contains(&EffectType { name: "IO".to_string(), params: Vec::new() }));
    }
}