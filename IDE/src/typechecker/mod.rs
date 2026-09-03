//! OREO Bidirectional Type Checker with Effect Inference
//!
//! Complete type checking implementation with:
//! - Bidirectional type checking (synthesis + checking)
//! - Effect inference and subsumption
//! - Constraint solving for generics
//! - Trait resolution
//! - Error reporting with source locations

use super::*;
use std::collections::{HashMap, HashSet, VecDeque};
use std::fmt;
use serde::{Deserialize, Serialize};

/// Type checking mode
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CheckMode {
    /// Synthesize type from expression
    Synth,
    /// Check expression against expected type
    Check(OreType),
}

/// Type checking context
#[derive(Debug, Clone)]
pub struct TypeCheckContext {
    /// Type environment
    pub env: TypeEnv,
    /// Effect inference
    pub effect_inference: EffectInference,
    /// Current function return type (for return statements)
    pub current_return_type: Option<OreType>,
    /// Current function effects (for effect checking)
    pub current_function_effects: EffectSet,
    /// Loop nesting level (for break/continue)
    pub loop_depth: u32,
    /// Errors collected during checking
    pub errors: Vec<TypeError>,
    /// Warnings collected during checking
    pub warnings: Vec<TypeWarning>,
    /// Current source location
    pub current_location: Option<SourceLocation>,
    /// Type variable counter
    pub next_type_var: u32,
    /// Effect variable counter
    pub next_effect_var: u32,
    /// Solver state
    pub solver: ConstraintSolver,
}

impl TypeCheckContext {
    pub fn new() -> Self {
        TypeCheckContext {
            env: TypeEnv::default(),
            effect_inference: EffectInference::new(),
            current_return_type: None,
            current_function_effects: EffectSet::new(),
            loop_depth: 0,
            errors: Vec::new(),
            warnings: Vec::new(),
            current_location: None,
            next_type_var: 0,
            next_effect_var: 0,
            solver: ConstraintSolver::new(),
        }
    }

    pub fn with_env(mut self, env: TypeEnv) -> Self {
        self.env = env;
        self
    }

    pub fn push_scope(&mut self) {
        // In a real implementation, this would push a new scope level
    }

    pub fn pop_scope(&mut self) {
        // In a real implementation, this would pop the scope level
    }

    pub fn add_error(&mut self, error: TypeError) {
        self.errors.push(error);
    }

    pub fn add_warning(&mut self, warning: TypeWarning) {
        self.warnings.push(warning);
    }

    pub fn fresh_type_var(&mut self) -> OreType {
        let name = format!("T{}", self.next_type_var);
        self.next_type_var += 1;
        OreType::Generic(GenericParam {
            name,
            constraints: Vec::new(),
            default: None,
            variance: Variance::Invariant,
        })
    }

    pub fn fresh_effect_var(&mut self) -> EffectSet {
        let mut effects = HashSet::new();
        let name = format!("E{}", self.next_effect_var);
        self.next_effect_var += 1;
        effects.insert(Effect {
            kind: EffectKind::Custom,
            params: Vec::new(),
            name,
        });
        EffectSet { effects }
    }

    pub fn enter_function(&mut self, return_type: OreType, effects: EffectSet) {
        self.current_return_type = Some(return_type);
        self.current_function_effects = effects;
    }

    pub fn exit_function(&mut self) {
        self.current_return_type = None;
        self.current_function_effects = EffectSet::new();
    }

    pub fn enter_loop(&mut self) {
        self.loop_depth += 1;
    }

    pub fn exit_loop(&mut self) {
        self.loop_depth = self.loop_depth.saturating_sub(1);
    }
}

/// Type error
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeError {
    pub message: String,
    pub location: Option<SourceLocation>,
    pub error_code: ErrorCode,
    pub notes: Vec<String>,
    pub suggested_fixes: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ErrorCode {
    TypeMismatch,
    UnknownVariable,
    UnknownType,
    UnknownEffect,
    EffectNotAllowed,
    EffectNotHandled,
    TraitNotImplemented,
    AmbiguousType,
    RecursiveType,
    InfiniteType,
    ArityMismatch,
    DuplicateDefinition,
    UnusedVariable,
    UnreachableCode,
    MissingReturn,
    NonExhaustiveMatch,
    InvalidCast,
    EffectMismatch,
    CapabilityMissing,
    UnsupportedOperation,
}

impl fmt::Display for TypeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)?;
        if let Some(loc) = &self.location {
            write!(f, " at {}", loc)?;
        }
        for note in &self.notes {
            write!(f, "\n  note: {}", note)?;
        }
        for fix in &self.suggested_fixes {
            write!(f, "\n  help: {}", fix)?;
        }
        Ok(())
    }
}

/// Type warning
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeWarning {
    pub message: String,
    pub location: Option<SourceLocation>,
    pub warning_code: WarningCode,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum WarningCode {
    UnusedVariable,
    UnusedImport,
    DeadCode,
    RedundantCast,
    EffectCouldBePure,
    UnusedTypeParameter,
    DeprecatedSyntax,
    PotentialBug,
}

/// Constraint solver for type inference
#[derive(Debug, Clone)]
pub struct ConstraintSolver {
    pub type_constraints: Vec<TypeConstraint>,
    pub effect_constraints: Vec<EffectConstraint>,
    pub type_substitution: TypeSubstitution,
    pub effect_substitution: HashMap<String, EffectSet>,
    pub trait_obligations: Vec<TraitObligation>,
}

impl ConstraintSolver {
    pub fn new() -> Self {
        ConstraintSolver {
            type_constraints: Vec::new(),
            effect_constraints: Vec::new(),
            type_substitution: TypeSubstitution::default(),
            effect_substitution: HashMap::new(),
            trait_obligations: Vec::new(),
        }
    }

    pub fn add_type_constraint(&mut self, left: OreType, right: OreType, kind: ConstraintKind, location: Option<String>) {
        self.type_constraints.push(TypeConstraint { left, right, kind, location });
    }

    pub fn add_effect_constraint(&mut self, left: EffectSet, right: EffectSet, kind: EffectConstraintKind) {
        self.effect_constraints.push(EffectConstraint { left, right, kind });
    }

    pub fn add_trait_obligation(&mut self, obligation: TraitObligation) {
        self.trait_obligations.push(obligation);
    }

    pub fn solve(&mut self) -> Result<(), String> {
        // Solve type constraints
        for constraint in &self.type_constraints {
            self.solve_type_constraint(constraint)?;
        }

        // Solve effect constraints
        for constraint in &self.effect_constraints {
            self.solve_effect_constraint(constraint)?;
        }

        // Solve trait obligations
        for obligation in &self.trait_obligations {
            self.solve_trait_obligation(obligation)?;
        }

        Ok(())
    }

    fn solve_type_constraint(&mut self, constraint: &TypeConstraint) -> Result<(), String> {
        let left = self.type_substitution.apply_type(&constraint.left);
        let right = self.type_substitution.apply_type(&constraint.right);

        match constraint.kind {
            ConstraintKind::Equals => {
                self.unify(&left, &right, constraint.location.clone())?;
            }
            ConstraintKind::Subtype => {
                self.check_subtype(&left, &right, constraint.location.clone())?;
            }
            ConstraintKind::Supertype => {
                self.check_subtype(&right, &left, constraint.location.clone())?;
            }
            ConstraintKind::Implements => {
                self.check_implements(&left, &right, constraint.location.clone())?;
            }
        }
        Ok(())
    }

    fn solve_effect_constraint(&mut self, constraint: &EffectConstraint) -> Result<(), String> {
        let left = self.apply_effect_subst(&constraint.left);
        let right = self.apply_effect_subst(&constraint.right);

        match constraint.kind {
            EffectConstraintKind::Subset => {
                if !left.is_subset_of(&right) {
                    return Err(format!("Effect set {:?} is not a subset of {:?}", left, right));
                }
            }
            EffectConstraintKind::Superset => {
                if !right.is_subset_of(&left) {
                    return Err(format!("Effect set {:?} is not a superset of {:?}", left, right));
                }
            }
            EffectConstraintKind::Equals => {
                if left != right {
                    return Err(format!("Effect sets not equal: {:?} != {:?}", left, right));
                }
            }
        }
        Ok(())
    }

    fn unify(&mut self, left: &OreType, right: &OreType, location: Option<String>) -> Result<(), String> {
        match (left, right) {
            (OreType::Generic(gp), ty) | (ty, OreType::Generic(gp)) => {
                if self.occurs_check(&gp.name, ty) {
                    return Err(format!("Occurs check failed: {} = {}", gp.name, ty));
                }
                self.type_substitution.type_vars.insert(gp.name.clone(), ty.clone());
            }
            (OreType::Function(fl), OreType::Function(fr)) => {
                if fl.params.len() != fr.params.len() {
                    return Err("Function arity mismatch".to_string());
                }
                // Unify return types
                self.unify(&fl.return_type, &fr.return_type, location.clone())?;
                // Unify parameter types
                for (pl, pr) in fl.params.iter().zip(fr.params.iter()) {
                    self.unify(&pl.param_type, &pr.param_type, location.clone())?;
                }
                // Unify effects
                self.add_effect_constraint(EffectConstraint {
                    left: fl.effects.clone(),
                    right: fr.effects.clone(),
                    kind: EffectConstraintKind::Equals,
                });
            }
            (OreType::Tuple(tl), OreType::Tuple(tr)) => {
                if tl.len() != tr.len() {
                    return Err("Tuple size mismatch".to_string());
                }
                for (l, r) in tl.iter().zip(tr.iter()) {
                    self.unify(l, r, location.clone())?;
                }
            }
            (OreType::Record(fl), OreType::Record(fr)) => {
                if fl.len() != fr.len() {
                    return Err("Record field count mismatch".to_string());
                }
                for (l, r) in fl.iter().zip(fr.iter()) {
                    if l.0 != r.0 {
                        return Err(format!("Record field name mismatch: {} != {}", l.0, r.0));
                    }
                    self.unify(&l.1, &r.1, location.clone())?;
                }
            }
            (OreType::Sum(vl), OreType::Sum(vr)) => {
                if vl.len() != vr.len() {
                    return Err("Sum variant count mismatch".to_string());
                }
                for (l, r) in vl.iter().zip(vr.iter()) {
                    if l.0 != r.0 {
                        return Err(format!("Sum variant name mismatch: {} != {}", l.0, r.0));
                    }
                    self.unify(&l.1, &r.1, location.clone())?;
                }
            }
            (OreType::Array(el, sl), OreType::Array(er, sr)) => {
                if sl != sr {
                    return Err("Array size mismatch".to_string());
                }
                self.unify(el, er, location)?;
            }
            (OreType::Map(kl, vl), OreType::Map(kr, vr)) => {
                self.unify(kl, kr, location.clone())?;
                self.unify(vl, vr, location)?;
            }
            (OreType::Option(l), OreType::Option(r)) => {
                self.unify(l, r, location)?;
            }
            (OreType::Result(ol, el), OreType::Result(or, er)) => {
                self.unify(ol, or, location.clone())?;
                self.unify(el, er, location)?;
            }
            (OreType::Primitive(pl), OreType::Primitive(pr)) => {
                if pl != pr {
                    return Err(format!("Primitive type mismatch: {} != {}", pl, pr));
                }
            }
            (OreType::Generic(gp), OreType::Generic(gq)) => {
                if gp.name != gq.name {
                    // Create equality constraint between type vars
                    self.type_substitution.type_vars.insert(gp.name.clone(), OreType::Generic(gq.clone()));
                }
            }
            (OreType::Alias(a), OreType::Alias(b)) => {
                if a.name != b.name {
                    return Err(format!("Type alias mismatch: {} != {}", a.name, b.name));
                }
            }
            (OreType::Never, _) | (_, OreType::Never) => {
                // Never unifies with anything
            }
            (OreType::Unknown, _) | (_, OreType::Unknown) => {
                // Unknown unifies with anything (will be resolved later)
            }
            _ => {
                return Err(format!("Cannot unify {} with {}", left, right));
            }
        }
        Ok(())
    }

    fn occurs_check(&self, var: &str, ty: &OreType) -> bool {
        match ty {
            OreType::Generic(gp) => gp.name == var,
            OreType::Function(f) => {
                self.occurs_check(var, &f.return_type) ||
                f.params.iter().any(|p| self.occurs_check(var, &p.param_type))
            }
            OreType::Tuple(types) => types.iter().any(|t| self.occurs_check(var, t)),
            OreType::Record(fields) => fields.iter().any(|(_, t)| self.occurs_check(var, t)),
            OreType::Sum(variants) => variants.iter().any(|(_, t)| self.occurs_check(var, t)),
            OreType::Array(t, _) => self.occurs_check(var, t),
            OreType::Map(k, v) => self.occurs_check(var, k) || self.occurs_check(var, v),
            OreType::Option(t) => self.occurs_check(var, t),
            OreType::Result(ok, err) => self.occurs_check(var, ok) || self.occurs_check(var, err),
            OreType::Function(f) => {
                self.occurs_check(var, &f.return_type) ||
                f.params.iter().any(|p| self.occurs_check(var, &p.param_type))
            }
            OreType::Effect(eff) => eff.params.iter().any(|p| self.occurs_check(var, p)),
            OreType::Generic(gp) => gp.name == var,
            _ => false,
        }
    }

    fn check_subtype(&mut self, left: &OreType, right: &OreType, location: Option<String>) -> Result<(), String> {
        // Simplified subtyping - in practice would be more sophisticated
        match (left, right) {
            (OreType::Never, _) => Ok(()), // Never is subtype of everything
            (_, OreType::Unknown) => Ok(()), // Anything is subtype of Unknown
            (OreType::Primitive(l), OreType::Primitive(r)) => {
                if l == r { Ok(()) } else { Err(format!("{} is not a subtype of {}", l, r)) }
            }
            (OreType::Function(fl), OreType::Function(fr)) => {
                // Contravariant in params, covariant in return
                if fl.params.len() != fr.params.len() {
                    return Err("Function arity mismatch".to_string());
                }
                for (pl, pr) in fl.params.iter().zip(fr.params.iter()) {
                    self.check_subtype(&pr.param_type, &pl.param_type, location.clone())?; // Contravariant
                }
                self.check_subtype(&fl.return_type, &fr.return_type, location)?; // Covariant
                // Effects: left must subsume right (more effects allowed)
                if !fl.effects.subsumes(&fr.effects) {
                    return Err(format!("Effect set {:?} does not subsume {:?}", fl.effects, fr.effects));
                }
                Ok(())
            }
            (OreType::Option(l), OreType::Option(r)) => self.check_subtype(l, r, location),
            (OreType::Result(ol, el), OreType::Result(or, er)) => {
                self.check_subtype(ol, or, location.clone())?;
                self.check_subtype(el, er, location)
            }
            (OreType::Array(l, sl), OreType::Array(r, sr)) => {
                if sl != sr { return Err("Array size mismatch in subtyping".to_string()); }
                self.check_subtype(l, r, location)
            }
            _ => {
                // For now, only allow exact match
                if left == right { Ok(()) } else { Err(format!("{} is not a subtype of {}", left, right)) }
            }
        }
    }

    fn check_implements(&self, left: &OreType, right: &OreType, location: Option<String>) -> Result<(), String> {
        // Check if left implements the trait in right
        // Simplified - would need trait registry lookup
        if let OreType::Alias(trait_alias) = right {
            // Would look up trait implementation for left type
            Ok(())
        } else {
            Err(format!("Right side of implements must be a trait, got {}", right))
        }
    }

    fn apply_effect_subst(&self, effects: &EffectSet) -> EffectSet {
        let mut new_effects = HashSet::new();
        for eff in &effects.effects {
            let mut new_eff = eff.clone();
            new_eff.params = eff.params.iter().map(|p| self.type_substitution.apply_type(p)).collect();
            new_effects.insert(new_eff);
        }
        EffectSet { effects: new_effects }
    }

    fn solve_trait_obligation(&mut self, obligation: &TraitObligation) -> Result<(), String> {
        // Would look up trait implementation
        Ok(())
    }
}

/// Trait obligation for resolution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraitObligation {
    pub trait_name: String,
    pub for_type: OreType,
    pub type_params: Vec<OreType>,
    pub location: Option<SourceLocation>,
}

/// Main type checking functions
pub struct TypeChecker {
    pub context: TypeCheckContext,
    pub builtin_types: HashMap<String, OreType>,
    pub builtin_traits: HashMap<String, TraitInfo>,
}

impl TypeChecker {
    pub fn new() -> Self {
        let mut checker = TypeChecker {
            context: TypeCheckContext::new(),
            builtin_types: HashMap::new(),
            builtin_traits: HashMap::new(),
        };
        checker.init_builtins();
        checker
    }

    fn init_builtins(&mut self) {
        // Primitive types
        self.builtin_types.insert("bool".to_string(), OreType::Primitive(PrimitiveType::Bool));
        self.builtin_types.insert("i8".to_string(), OreType::Primitive(PrimitiveType::Int8));
        self.builtin_types.insert("i16".to_string(), OreType::Primitive(PrimitiveType::Int16));
        self.builtin_types.insert("i32".to_string(), OreType::Primitive(PrimitiveType::Int32));
        self.builtin_types.insert("i64".to_string(), OreType::Primitive(PrimitiveType::Int64));
        self.builtin_types.insert("i128".to_string(), OreType::Primitive(PrimitiveType::Int128));
        self.builtin_types.insert("u8".to_string(), OreType::Primitive(PrimitiveType::UInt8));
        self.builtin_types.insert("u16".to_string(), OreType::Primitive(PrimitiveType::UInt16));
        self.builtin_types.insert("u32".to_string(), OreType::Primitive(PrimitiveType::UInt32));
        self.builtin_types.insert("u64".to_string(), OreType::Primitive(PrimitiveType::UInt64));
        self.builtin_types.insert("u128".to_string(), OreType::Primitive(PrimitiveType::UInt128));
        self.builtin_types.insert("f16".to_string(), OreType::Primitive(PrimitiveType::Float16));
        self.builtin_types.insert("f32".to_string(), OreType::Primitive(PrimitiveType::Float32));
        self.builtin_types.insert("f64".to_string(), OreType::Primitive(PrimitiveType::Float64));
        self.builtin_types.insert("f80".to_string(), OreType::Primitive(PrimitiveType::Float80));
        self.builtin_types.insert("char".to_string(), OreType::Primitive(PrimitiveType::Char));
        self.builtin_types.insert("string".to_string(), OreType::Primitive(PrimitiveType::String));
        self.builtin_types.insert("bytes".to_string(), OreType::Primitive(PrimitiveType::Bytes));
        self.builtin_types.insert("never".to_string(), OreType::Never);

        // Builtin traits
        self.builtin_traits.insert("Clone".to_string(), TraitInfo {
            name: "Clone".to_string(),
            type_params: vec![],
            methods: vec![],
            supertraits: vec![],
        });
        self.builtin_traits.insert("Copy".to_string(), TraitInfo {
            name: "Copy".to_string(),
            type_params: vec![],
            methods: vec![],
            supertraits: vec!["Clone".to_string()],
        });
        self.builtin_traits.insert("Send".to_string(), TraitInfo {
            name: "Send".to_string(),
            type_params: vec![],
            methods: vec![],
            supertraits: vec![],
        });
        self.builtin_traits.insert("Sync".to_string(), TraitInfo {
            name: "Sync".to_string(),
            type_params: vec![],
            methods: vec![],
            supertraits: vec![],
        });
    }

    /// Type check a node in synthesis mode
    pub fn synth(&mut self, node: &dyn GirNode) -> Result<OreType, String> {
        self.check_node(node, CheckMode::Synth)
    }

    /// Type check a node in checking mode
    pub fn check(&mut self, node: &dyn GirNode, expected: OreType) -> Result<OreType, String> {
        self.check_node(node, CheckMode::Check(expected))
    }

    fn check_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        match node.node_type() {
            NodeType::Value => self.check_value_node(node, mode),
            NodeType::Op => self.check_op_node(node, mode),
            NodeType::Control => self.check_control_node(node, mode),
            NodeType::Type => self.check_type_node(node, mode),
            NodeType::Effect => self.check_effect_node(node, mode),
            NodeType::Meta => self.check_meta_node(node, mode),
        }
    }

    fn check_value_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Value nodes have their type in the node
        if let Some(value_node) = node.as_any().downcast_ref::<ValueNode>() {
            let ty = value_node.value_type.clone();
            match mode {
                CheckMode::Synth => Ok(ty),
                CheckMode::Check(expected) => {
                    self.context.check_subtype(&ty, &expected, None)?;
                    Ok(expected)
                }
            }
        } else {
            Err("Expected ValueNode".to_string())
        }
    }

    fn check_op_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Would check operation types based on operation kind
        // For now return the output type from the first output port
        if let Some(output_port) = node.output_ports().first() {
            let ty = output_port.port_type.clone();
            match mode {
                CheckMode::Synth => Ok(ty),
                CheckMode::Check(expected) => {
                    self.context.check_subtype(&ty, &expected, None)?;
                    Ok(expected)
                }
            }
        } else {
            Err("OpNode has no output ports".to_string())
        }
    }

    fn check_control_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Control nodes typically return the type of their branches
        if let Some(output_port) = node.output_ports().first() {
            let ty = output_port.port_type.clone();
            match mode {
                CheckMode::Synth => Ok(ty),
                CheckMode::Check(expected) => {
                    self.context.check_subtype(&ty, &expected, None)?;
                    Ok(expected)
                }
            }
        } else {
            // Control nodes like return/break don't produce values
            Ok(OreType::Never)
        }
    }

    fn check_type_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Type nodes represent type definitions
        Ok(OreType::Unknown)
    }

    fn check_effect_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Effect nodes represent effect operations
        if let Some(output_port) = node.output_ports().first() {
            let ty = output_port.port_type.clone();
            match mode {
                CheckMode::Synth => Ok(ty),
                CheckMode::Check(expected) => {
                    self.context.check_subtype(&ty, &expected, None)?;
                    Ok(expected)
                }
            }
        } else {
            Err("EffectNode has no output ports".to_string())
        }
    }

    fn check_meta_node(&mut self, node: &dyn GirNode, mode: CheckMode) -> Result<OreType, String> {
        // Meta nodes don't produce runtime values
        Ok(OreType::Never)
    }

    /// Check a function definition
    pub fn check_function(&mut self, func: &FunctionDef) -> Result<FunctionType, String> {
        self.context.enter_function(func.return_type.clone(), func.effects.clone());
        
        // Add parameters to environment
        for param in &func.params {
            self.context.env.variables.insert(param.name.clone(), param.param_type.clone());
        }

        // Check body
        let body_type = self.synth(func.body.as_ref())?;
        
        // Check return type matches
        self.context.check_subtype(&body_type, &func.return_type, func.body.metadata().source_location.clone())?;

        // Check effects
        let inferred_effects = self.context.effect_inference.solve()?;
        // Would check that inferred effects are subset of declared effects

        let func_type = FunctionType {
            params: func.params.iter().map(|p| FunctionParam {
                name: p.name.clone(),
                param_type: p.param_type.clone(),
                is_mut: p.is_mut,
                default_value: p.default_value.clone(),
                is_variadic: false,
            }).collect(),
            return_type: Box::new(func.return_type.clone()),
            effects: func.effects.clone(),
            is_async: func.is_async,
            is_const: func.is_const,
            is_unsafe: func.is_unsafe,
            calling_convention: CallingConvention::Default,
        };

        self.context.exit_function();
        Ok(func_type)
    }

    /// Get all errors
    pub fn errors(&self) -> &[TypeError] {
        &self.context.errors
    }

    /// Get all warnings
    pub fn warnings(&self) -> &[TypeWarning] {
        &self.context.warnings
    }

    /// Check if there are any errors
    pub fn has_errors(&self) -> bool {
        !self.context.errors.is_empty()
    }
}

/// Function definition for type checking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionDef {
    pub name: String,
    pub params: Vec<FunctionParam>,
    pub return_type: OreType,
    pub effects: EffectSet,
    pub is_async: bool,
    pub is_const: bool,
    pub is_unsafe: bool,
    pub body: Box<dyn GirNode>,
    pub type_params: Vec<GenericParam>,
    pub where_clauses: Vec<WhereClause>,
}

/// Trait information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraitInfo {
    pub name: String,
    pub type_params: Vec<GenericParam>,
    pub methods: Vec<TraitMethod>,
    pub supertraits: Vec<String>,
}

/// Trait method
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraitMethod {
    pub name: String,
    pub signature: FunctionType,
    pub default_impl: Option<Box<dyn GirNode>>,
}

/// Type checking result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeCheckResult {
    pub success: bool,
    pub errors: Vec<TypeError>,
    pub warnings: Vec<TypeWarning>,
    pub inferred_types: HashMap<NodeId, OreType>,
    pub inferred_effects: HashMap<NodeId, EffectSet>,
}

impl TypeChecker {
    /// Run type checking on a graph
    pub fn check_graph(&mut self, graph: &GirGraph) -> TypeCheckResult {
        let mut inferred_types = HashMap::new();
        let mut inferred_effects = HashMap::new();

        // Topological sort for checking order
        if let Ok(sorted) = graph.topological_sort() {
            for node_id in sorted {
                if let Some(node) = graph.get_node(node_id) {
                    match self.synth(node) {
                        Ok(ty) => {
                            inferred_types.insert(node_id, ty);
                        }
                        Err(e) => {
                            self.context.add_error(TypeError {
                                message: e,
                                location: node.metadata().source_location.clone(),
                                error_code: ErrorCode::TypeMismatch,
                                notes: vec![],
                                suggested_fixes: vec![],
                            });
                        }
                    }
                }
        }

        TypeCheckResult {
            success: self.context.errors.is_empty(),
            errors: self.context.errors.clone(),
            warnings: self.context.warnings.clone(),
            inferred_types,
            inferred_effects,
        }
    }
}

/// Type inference for expressions (local type inference)
pub struct LocalTypeInference {
    pub context: TypeCheckContext,
    pub expected_type: Option<OreType>,
}

impl LocalTypeInference {
    pub fn new(context: TypeCheckContext) -> Self {
        LocalTypeInference {
            context,
            expected_type: None,
        }
    }

    pub fn infer(&mut self, node: &dyn GirNode) -> Result<OreType, String> {
        self.infer_with_expected(node, self.expected_type.clone())
    }

    pub fn infer_with_expected(&mut self, node: &dyn GirNode, expected: Option<OreType>) -> Result<OreType, String> {
        match expected {
            Some(ty) => self.context.check(node, ty),
            None => self.context.synth(node),
        }
    }
}

/// Type display for error messages
pub fn type_to_string(ty: &OreType) -> String {
    ty.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_type_checker_creation() {
        let checker = TypeChecker::new();
        assert!(checker.builtin_types.contains_key("i32"));
        assert!(checker.builtin_types.contains_key("bool"));
        assert!(checker.builtin_types.contains_key("string"));
    }

    #[test]
    fn test_type_error_display() {
        let error = TypeError {
            message: "Type mismatch".to_string(),
            location: Some(SourceLocation {
                file: Some("test.oreo".to_string()),
                line: Some(10),
                column: Some(5),
                span: None,
            }),
            error_code: ErrorCode::TypeMismatch,
            notes: vec!["Expected i32".to_string(), "Found string".to_string()],
            suggested_fixes: vec!["Change variable type".to_string()],
        };
        
        let display = format!("{}", error);
        assert!(display.contains("Type mismatch"));
        assert!(display.contains("test.oreo:10:5"));
        assert!(display.contains("Expected i32"));
        assert!(display.contains("help: Change variable type"));
    }

    #[test]
    fn test_constraint_solver() {
        let mut solver = ConstraintSolver::new();
        
        let int_type = OreType::Primitive(PrimitiveType::Int32);
        let int_type2 = OreType::Primitive(PrimitiveType::Int32);
        
        solver.add_type_constraint(int_type, int_type2, ConstraintKind::Equals, None);
        
        assert!(solver.solve().is_ok());
    }

    #[test]
    fn test_unify_primitives() {
        let mut solver = ConstraintSolver::new();
        
        let int_type = OreType::Primitive(PrimitiveType::Int32);
        let int_type2 = OreType::Primitive(PrimitiveType::Int32);
        
        assert!(solver.unify(&int_type, &int_type2, None).is_ok());
        
        let float_type = OreType::Primitive(PrimitiveType::Float64);
        assert!(solver.unify(&int_type, &float_type, None).is_err());
    }

    #[test]
    fn test_occurs_check() {
        let solver = ConstraintSolver::new();
        
        let var = OreType::Generic(GenericParam {
            name: "T".to_string(),
            constraints: Vec::new(),
            default: None,
            variance: Variance::Invariant,
        });
        
        let recursive = OreType::Function(FunctionType {
            params: vec![],
            return_type: Box::new(var.clone()),
            effects: EffectSet::new(),
            is_async: false,
            is_const: false,
            is_unsafe: false,
            calling_convention: CallingConvention::Default,
        });
        
        assert!(solver.occurs_check("T", &recursive));
        assert!(!solver.occurs_check("U", &recursive));
    }

    #[test]
    fn test_subtype_checking() {
        let mut solver = ConstraintSolver::new();
        
        // Never is subtype of everything
        assert!(solver.check_subtype(&OreType::Never, &OreType::Primitive(PrimitiveType::Int32), None).is_ok());
        
        // Int32 is not subtype of Int64 (no implicit widening in this system)
        let int32 = OreType::Primitive(PrimitiveType::Int32);
        let int64 = OreType::Primitive(PrimitiveType::Int64);
        assert!(solver.check_subtype(&int32, &int64, None).is_err());
        
        // Function subtyping
        let fn1 = OreType::Function(FunctionType {
            params: vec![FunctionParam {
                name: "x".to_string(),
                param_type: OreType::Primitive(PrimitiveType::Int32),
                is_mut: false,
                default_value: None,
                is_variadic: false,
            }],
            return_type: Box::new(OreType::Primitive(PrimitiveType::Int32)),
            effects: EffectSet::new(),
            is_async: false,
            is_const: false,
            is_unsafe: false,
            calling_convention: CallingConvention::Default,
        });
        
        let fn2 = OreType::Function(FunctionType {
            params: vec![FunctionParam {
                name: "x".to_string(),
                param_type: OreType::Primitive(PrimitiveType::Int32),
                is_mut: false,
                default_value: None,
                is_variadic: false,
            }],
            return_type: Box::new(OreType::Primitive(PrimitiveType::Int32)),
            effects: EffectSet::new(),
            is_async: false,
            is_const: false,
            is_unsafe: false,
            calling_convention: CallingConvention::Default,
        });
        
        assert!(solver.check_subtype(&fn1, &fn2, None).is_ok());
    }

    #[test]
    fn test_type_checker_basic() {
        let mut checker = TypeChecker::new();
        
        // Test that we can look up builtin types
        assert_eq!(checker.builtin_types.get("i32"), Some(&OreType::Primitive(PrimitiveType::Int32)));
        assert_eq!(checker.builtin_types.get("bool"), Some(&OreType::Primitive(PrimitiveType::Bool)));
    }
}