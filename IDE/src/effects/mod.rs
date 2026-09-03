//! OREO Effect System
//!
//! Comprehensive effect system with:
//! - Built-in effects: IO, State, Exception, Async, Resource
//! - Row-polymorphic effect sets
//! - Effect inference and subsumption
//! - Effect handlers (for algebraic effects)
//! - Effect safety and encapsulation

use super::*;
use std::collections::{HashMap, HashSet};
use std::fmt;
use serde::{Deserialize, Serialize};

/// Effect kind - built-in effects
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EffectKind {
    /// Input/Output operations
    IO,
    /// Mutable state at a location
    State,
    /// Exception throwing/catching
    Exception,
    /// Asynchronous computation
    Async,
    /// Resource acquisition/release
    Resource,
    /// Non-determinism
    Nondet,
    /// Continuation capture
    Continuation,
    /// Custom user-defined effect
    Custom,
}

/// Effect with parameters
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Effect {
    pub kind: EffectKind,
    pub params: Vec<OreType>,
    pub name: String, // For custom effects
}

impl Effect {
    pub fn io() -> Self {
        Effect { kind: EffectKind::IO, params: vec![], name: "IO".to_string() }
    }

    pub fn state(loc: OreType) -> Self {
        Effect { kind: EffectKind::State, params: vec![loc], name: "State".to_string() }
    }

    pub fn exception(err: OreType) -> Self {
        Effect { kind: EffectKind::Exception, params: vec![err], name: "Exception".to_string() }
    }

    pub fn async_() -> Self {
        Effect { kind: EffectKind::Async, params: vec![], name: "Async".to_string() }
    }

    pub fn resource(res: OreType) -> Self {
        Effect { kind: EffectKind::Resource, params: vec![res], name: "Resource".to_string() }
    }

    pub fn nondet() -> Self {
        Effect { kind: EffectKind::Nondet, params: vec![], name: "Nondet".to_string() }
    }

    pub fn continuation(answer: OreType) -> Self {
        Effect { kind: EffectKind::Continuation, params: vec![answer], name: "Continuation".to_string() }
    }

    pub fn custom(name: String, params: Vec<OreType>) -> Self {
        Effect { kind: EffectKind::Custom, params, name }
    }
}

impl fmt::Display for Effect {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.kind {
            EffectKind::IO => write!(f, "IO"),
            EffectKind::State => write!(f, "State<{}>", self.params[0]),
            EffectKind::Exception => write!(f, "Exception<{}>", self.params[0]),
            EffectKind::Async => write!(f, "Async"),
            EffectKind::Resource => write!(f, "Resource<{}>", self.params[0]),
            EffectKind::Nondet => write!(f, "Nondet"),
            EffectKind::Continuation => write!(f, "Continuation<{}>", self.params[0]),
            EffectKind::Custom => write!(f, "{}", self.name),
        }
    }
}

/// Row-polymorphic effect set
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectRow {
    pub effects: HashSet<Effect>,
    pub tail: Option<EffectRowVariable>, // For row polymorphism
}

/// Effect row variable (for polymorphism)
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectRowVariable {
    pub name: String,
    pub constraints: Vec<EffectConstraint>,
}

/// Constraint on effect row variable
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EffectConstraint {
    /// Row must contain this effect
    Contains(Effect),
    /// Row must not contain this effect
    Excludes(Effect),
    /// Row must be subset of another
    SubsetOf(EffectRow),
}

/// Effect set - concrete set of effects (closed row)
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectSet {
    pub effects: HashSet<Effect>,
}

impl EffectSet {
    pub fn new() -> Self {
        EffectSet { effects: HashSet::new() }
    }

    pub fn from_effects(effects: Vec<Effect>) -> Self {
        EffectSet { effects: effects.into_iter().collect() }
    }

    pub fn single(effect: Effect) -> Self {
        let mut set = EffectSet::new();
        set.insert(effect);
        set
    }

    pub fn insert(&mut self, effect: Effect) {
        self.effects.insert(effect);
    }

    pub fn remove(&mut self, effect: &Effect) {
        self.effects.remove(effect);
    }

    pub fn contains(&self, effect: &Effect) -> bool {
        self.effects.contains(effect)
    }

    pub fn union(&self, other: &EffectSet) -> EffectSet {
        let mut result = self.clone();
        result.effects.extend(other.effects.iter().cloned());
        result
    }

    pub fn intersection(&self, other: &EffectSet) -> EffectSet {
        EffectSet {
            effects: self.effects.intersection(&other.effects).cloned().collect(),
        }
    }

    pub fn difference(&self, other: &EffectSet) -> EffectSet {
        EffectSet {
            effects: self.effects.difference(&other.effects).cloned().collect(),
        }
    }

    pub fn is_subset_of(&self, other: &EffectSet) -> bool {
        self.effects.is_subset(&other.effects)
    }

    pub fn is_superset_of(&self, other: &EffectSet) -> bool {
        other.effects.is_subset(&self.effects)
    }

    pub fn is_disjoint(&self, other: &EffectSet) -> bool {
        self.effects.is_disjoint(&other.effects)
    }

    pub fn is_empty(&self) -> bool {
        self.effects.is_empty()
    }

    pub fn len(&self) -> usize {
        self.effects.len()
    }

    pub fn iter(&self) -> impl Iterator<Item = &Effect> {
        self.effects.iter()
    }
}

/// Effect polymorphism support
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PolymorphicEffect {
    /// The concrete effects we know about
    pub known: EffectSet,
    /// The row variable for polymorphic tail
    pub tail: Option<EffectRowVariable>,
}

impl PolymorphicEffect {
    pub fn new(known: EffectSet, tail: Option<EffectRowVariable>) -> Self {
        PolymorphicEffect { known, tail }
    }

    pub fn concrete(effects: EffectSet) -> Self {
        PolymorphicEffect { known: effects, tail: None }
    }

    pub fn polymorphic(tail: EffectRowVariable) -> Self {
        PolymorphicEffect { known: EffectSet::new(), tail: Some(tail) }
    }

    /// Check if this polymorphic effect subsumes another
    pub fn subsumes(&self, other: &PolymorphicEffect) -> bool {
        // Concrete effects must be subset
        if !other.known.is_subset_of(&self.known) {
            return false;
        }

        // Tail handling
        match (&self.tail, &other.tail) {
            (None, None) => true, // Both concrete
            (Some(_), None) => true, // We're polymorphic, they're concrete
            (None, Some(_)) => false, // They're polymorphic, we're not
            (Some(self_tail), Some(other_tail)) => {
                // Both polymorphic - check constraints
                self.constraints_subsume(other_tail)
            }
        }
    }

    fn constraints_subsume(&self, other_tail: &EffectRowVariable) -> bool {
        if let Some(self_tail) = &self.tail {
            // Check if our constraints are stricter
            for constraint in &self_tail.constraints {
                if !other_tail.constraints.iter().any(|c| c == constraint) {
                    return false;
                }
            }
        }
        true
    }

    /// Instantiate polymorphic effect with concrete tail
    pub fn instantiate(&self, tail_effects: EffectSet) -> EffectSet {
        let mut result = self.known.clone();
        // Tail would be replaced with concrete effects
        // For now just return known effects
        result
    }
}

/// Effect handler - for algebraic effects
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectHandler {
    pub name: String,
    pub handled_effects: Vec<EffectKind>,
    pub clauses: Vec<HandlerClause>,
    pub finally_clause: Option<HandlerClause>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandlerClause {
    pub effect_kind: EffectKind,
    pub parameter_pattern: Vec<String>, // Parameter names
    pub body: HandlerBody,
    pub resume_type: Option<OreType>, // Type of resume continuation
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HandlerBody {
    /// Simple expression body
    Expression(Box<dyn GirNode>),
    /// Block with statements
    Block(Vec<HandlerStatement>),
    /// Return value directly
    Return(Box<dyn GirNode>),
    /// Resume with value
    Resume(Box<dyn GirNode>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HandlerStatement {
    Let { name: String, type_ann: Option<OreType>, value: Box<dyn GirNode> },
    Expression(Box<dyn GirNode>),
    Return(Box<dyn GirNode>),
    Resume(Box<dyn GirNode>),
}

/// Effect safety - capabilities for effect encapsulation
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EffectCapability {
    pub effect: Effect,
    pub permission: CapabilityPermission,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CapabilityPermission {
    /// Can perform the effect
    Perform,
    /// Can handle the effect
    Handle,
    /// Can abstract over the effect (polymorphism)
    Abstract,
    /// Full permission
    All,
}

/// Effect safety context - tracks what effects are allowed where
#[derive(Debug, Clone, Default)]
pub struct EffectSafetyContext {
    pub allowed_effects: HashMap<EffectKind, CapabilityPermission>,
    pub effect_bounds: HashMap<String, PolymorphicEffect>, // For polymorphic bounds
    pub handler_stack: Vec<EffectHandler>,
}

impl EffectSafetyContext {
    pub fn new() -> Self {
        EffectSafetyContext {
            allowed_effects: HashMap::new(),
            effect_bounds: HashMap::new(),
            handler_stack: Vec::new(),
        }
    }

    pub fn allow_effect(&mut self, kind: EffectKind, permission: CapabilityPermission) {
        self.allowed_effects.insert(kind, permission);
    }

    pub fn can_perform(&self, effect: &Effect) -> bool {
        self.allowed_effects.get(&effect.kind)
            .map(|p| matches!(p, CapabilityPermission::Perform | CapabilityPermission::All))
            .unwrap_or(false)
    }

    pub fn can_handle(&self, kind: &EffectKind) -> bool {
        self.allowed_effects.get(kind)
            .map(|p| matches!(p, CapabilityPermission::Handle | CapabilityPermission::All))
            .unwrap_or(false)
    }

    pub fn push_handler(&mut self, handler: EffectHandler) {
        for kind in &handler.handled_effects {
            self.allowed_effects.insert(*kind, CapabilityPermission::Handle);
        }
        self.handler_stack.push(handler);
    }

    pub fn pop_handler(&mut self) -> Option<EffectHandler> {
        self.handler_stack.pop()
    }

    /// Check if an effect set is safe in this context
    pub fn is_effect_set_safe(&self, effects: &EffectSet) -> bool {
        for effect in &effects.effects {
            if !self.can_perform(effect) {
                // Check if there's a handler on the stack that handles it
                if !self.handler_stack.iter().any(|h| h.handled_effects.contains(&effect.kind)) {
                    return false;
                }
            }
        }
        true
    }
}

/// Effect inference for expressions
#[derive(Debug, Clone)]
pub struct EffectInference {
    pub constraints: Vec<EffectConstraint>,
    pub effect_vars: HashMap<String, EffectSet>,
    pub next_var_id: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EffectConstraint {
    /// Effect set must contain this effect
    MustContain(Effect),
    /// Effect set must not contain this effect
    MustNotContain(Effect),
    /// Effect set must be subset of another
    SubsetOf(EffectSet),
    /// Two effect sets must be equal
    Equals(EffectSet, EffectSet),
    /// Effect set must subsume another
    Subsumes(EffectSet, EffectSet),
}

impl EffectInference {
    pub fn new() -> Self {
        EffectInference {
            constraints: Vec::new(),
            effect_vars: HashMap::new(),
            next_var_id: 0,
        }
    }

    pub fn fresh_var(&mut self) -> String {
        let name = format!("E{}", self.next_var_id);
        self.next_var_id += 1;
        name
    }

    pub fn add_constraint(&mut self, constraint: EffectConstraint) {
        self.constraints.push(constraint);
    }

    pub fn solve(&mut self) -> Result<HashMap<String, EffectSet>, String> {
        // Simple constraint solving - in practice would be more sophisticated
        let mut solution = HashMap::new();
        
        for constraint in &self.constraints {
            match constraint {
                EffectConstraint::MustContain(effect) => {
                    // Add to all relevant variables
                }
                EffectConstraint::MustNotContain(effect) => {
                    // Ensure effect is not in solution
                }
                EffectConstraint::SubsetOf(set) => {
                    // Variable must be subset
                }
                EffectConstraint::Equals(a, b) => {
                    if a != b {
                        return Err(format!("Effect sets not equal: {:?} != {:?}", a, b));
                    }
                }
                EffectConstraint::Subsumes(a, b) => {
                    if !a.is_superset_of(b) {
                        return Err(format!("Effect set {:?} does not subsume {:?}", a, b));
                    }
                }
            }
        }

        Ok(solution)
    }
}

/// Built-in effect definitions for the standard library
pub mod builtin_effects {
    use super::*;

    pub fn io_effect() -> Effect {
        Effect::io()
    }

    pub fn state_effect(loc: OreType) -> Effect {
        Effect::state(loc)
    }

    pub fn exception_effect(err: OreType) -> Effect {
        Effect::exception(err)
    }

    pub fn async_effect() -> Effect {
        Effect::async_()
    }

    pub fn resource_effect(res: OreType) -> Effect {
        Effect::resource(res)
    }

    pub fn nondet_effect() -> Effect {
        Effect::nondet()
    }

    pub fn continuation_effect(answer: OreType) -> Effect {
        Effect::continuation(answer)
    }

    /// Standard effect sets
    pub fn pure_effects() -> EffectSet {
        EffectSet::new()
    }

    pub fn io_effects() -> EffectSet {
        EffectSet::from_effects(vec![Effect::io()])
    }

    pub fn state_effects(loc: OreType) -> EffectSet {
        EffectSet::from_effects(vec![Effect::state(loc)])
    }

    pub fn exception_effects(err: OreType) -> EffectSet {
        EffectSet::from_effects(vec![Effect::exception(err)])
    }

    pub fn async_effects() -> EffectSet {
        EffectSet::from_effects(vec![Effect::async_()])
    }

    pub fn total_effects() -> EffectSet {
        EffectSet::from_effects(vec![
            Effect::io(),
            Effect::async_(),
            Effect::nondet(),
        ])
    }
}

/// Effect safety attributes for functions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectSafety {
    pub allowed_effects: EffectSet,
    pub required_capabilities: Vec<EffectCapability>,
    pub is_pure: bool,
    pub is_total: bool, // Guaranteed to terminate
    pub is_deterministic: bool,
}

impl EffectSafety {
    pub fn pure() -> Self {
        EffectSafety {
            allowed_effects: EffectSet::new(),
            required_capabilities: Vec::new(),
            is_pure: true,
            is_total: true,
            is_deterministic: true,
        }
    }

    pub fn total() -> Self {
        EffectSafety {
            allowed_effects: EffectSet::new(),
            required_capabilities: Vec::new(),
            is_pure: false,
            is_total: true,
            is_deterministic: true,
        }
    }

    pub fn with_effects(effects: EffectSet) -> Self {
        EffectSafety {
            allowed_effects: effects,
            required_capabilities: Vec::new(),
            is_pure: false,
            is_total: false,
            is_deterministic: true,
        }
    }

    pub fn with_io() -> Self {
        EffectSafety::with_effects(EffectSet::from_effects(vec![Effect::io()]))
    }

    pub fn with_state(loc: OreType) -> Self {
        EffectSafety::with_effects(EffectSet::from_effects(vec![Effect::state(loc)]))
    }

    pub fn with_async() -> Self {
        EffectSafety::with_effects(EffectSet::from_effects(vec![Effect::async_()]))
    }

    pub fn check_compatibility(&self, other: &EffectSafety) -> bool {
        // Self's effects must be subset of other's allowed effects
        self.allowed_effects.is_subset_of(&other.allowed_effects)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_effect_creation() {
        let io = Effect::io();
        assert_eq!(io.kind, EffectKind::IO);
        assert_eq!(io.name, "IO");

        let state = Effect::state(OreType::Primitive(PrimitiveType::Int32));
        assert_eq!(state.kind, EffectKind::State);
        assert_eq!(state.params.len(), 1);
    }

    #[test]
    fn test_effect_set_operations() {
        let mut set1 = EffectSet::new();
        let mut set2 = EffectSet::new();
        
        let io = Effect::io();
        let state = Effect::state(OreType::Primitive(PrimitiveType::Int32));
        
        set1.insert(io.clone());
        set2.insert(state.clone());
        
        assert!(set1.contains(&io));
        assert!(!set1.contains(&state));
        
        let union = set1.union(&set2);
        assert!(union.contains(&io));
        assert!(union.contains(&state));
        assert_eq!(union.len(), 2);
    }

    #[test]
    fn test_effect_subsumption() {
        let mut pure = EffectSet::new();
        let mut io_only = EffectSet::new();
        let mut io_state = EffectSet::new();
        
        let io = Effect::io();
        let state = Effect::state(OreType::Primitive(PrimitiveType::Int32));
        
        io_only.insert(io.clone());
        io_state.insert(io.clone());
        io_state.insert(state.clone());
        
        assert!(io_only.is_superset_of(&pure));
        assert!(io_state.is_superset_of(&io_only));
        assert!(io_state.is_superset_of(&pure));
        assert!(!pure.is_superset_of(&io_only));
    }

    #[test]
    fn test_effect_kind_display() {
        assert_eq!(Effect::io().to_string(), "IO");
        assert_eq!(Effect::async_().to_string(), "Async");
        
        let state = Effect::state(OreType::Primitive(PrimitiveType::Int32));
        assert_eq!(state.to_string(), "State<i32>");
    }

    #[test]
    fn test_polymorphic_effect() {
        let concrete = PolymorphicEffect::concrete(EffectSet::from_effects(vec![Effect::io()]));
        assert!(concrete.tail.is_none());
        assert!(concrete.known.contains(&Effect::io()));

        let tail = EffectRowVariable {
            name: "E".to_string(),
            constraints: vec![],
        };
        let polymorphic = PolymorphicEffect::polymorphic(tail.clone());
        assert!(polymorphic.tail.is_some());
        assert!(polymorphic.known.is_empty());
    }

    #[test]
    fn test_effect_safety() {
        let pure = EffectSafety::pure();
        assert!(pure.is_pure);
        assert!(pure.allowed_effects.is_empty());

        let with_io = EffectSafety::with_io();
        assert!(!with_io.is_pure);
        assert!(with_io.allowed_effects.contains(&Effect::io()));

        let with_state = EffectSafety::with_state(OreType::Primitive(PrimitiveType::Int32));
        assert!(with_state.allowed_effects.iter().any(|e| matches!(e.kind, EffectKind::State)));
    }

    #[test]
    fn test_effect_safety_compatibility() {
        let pure = EffectSafety::pure();
        let with_io = EffectSafety::with_io();
        let with_io_state = EffectSafety::with_effects(
            EffectSet::from_effects(vec![Effect::io(), Effect::state(OreType::Primitive(PrimitiveType::Int32))])
        );

        // Pure is compatible with everything
        assert!(pure.check_compatibility(&with_io));
        assert!(pure.check_compatibility(&with_io_state));

        // IO is compatible with IO+State
        assert!(with_io.check_compatibility(&with_io_state));

        // But IO+State is NOT compatible with just IO
        assert!(!with_io_state.check_compatibility(&with_io));
    }
}