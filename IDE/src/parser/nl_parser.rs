//! OREO Natural Language Semantic Parser
//!
//! Parses natural language into the Graph Intermediate Representation (GIR).
//! Implements the "Natural Language First" philosophy - write programs in English,
//! get executable graph structures.

use super::*;
use std::collections::{HashMap, HashSet};
use std::fmt;
use serde::{Deserialize, Serialize};
use pest::Parser;
use pest_derive::Parser;

/// NL Parser using Pest for grammar definition
#[derive(Parser)]
#[grammar = "nl_grammar.pest"]
pub struct NLParser;

/// Parsed NL construct
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParsedConstruct {
    pub kind: ConstructKind,
    pub span: (usize, usize),
    pub children: Vec<ParsedConstruct>,
    pub attributes: HashMap<String, String>,
    pub confidence: f32,
}

/// Kind of NL construct
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConstructKind {
    // Declarations
    FunctionDef,
    VariableDef,
    TypeDef,
    EffectDef,
    ContractDef,
    
    // Expressions
    Literal,
    Variable,
    Call,
    BinaryOp,
    UnaryOp,
    IfExpr,
    LoopExpr,
    MatchExpr,
    Block,
    Return,
    
    // Types
    PrimitiveType,
    TupleType,
    RecordType,
    SumType,
    ArrayType,
    MapType,
    OptionType,
    ResultType,
    FunctionType,
    GenericType,
    
    // Effects
    EffectAnnotation,
    HandleExpr,
    
    // Control flow
    IfCondition,
    ThenBranch,
    ElseBranch,
    LoopCondition,
    LoopBody,
    
    // Patterns
    Pattern,
    PatternBinding,
    PatternVariant,
    
    // Documentation
    Comment,
    DocString,
}

/// Semantic parse result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticParseResult {
    pub gir: Option<Box<dyn GirNode>>,
    pub errors: Vec<ParseError>,
    pub warnings: Vec<ParseWarning>,
    pub unresolved_refs: Vec<UnresolvedRef>,
}

/// Parse error
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParseError {
    pub message: String,
    pub span: (usize, usize),
    pub error_code: ParseErrorCode,
    pub suggestions: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ParseErrorCode {
    UnexpectedToken,
    ExpectedKeyword,
    ExpectedExpression,
    ExpectedType,
    ExpectedPattern,
    UndefinedVariable,
    UndefinedType,
    TypeMismatch,
    ArityMismatch,
    AmbiguousParse,
    IncompleteConstruct,
    InvalidSyntax,
    EffectNotAllowed,
    CapabilityMissing,
}

/// Parse warning
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParseWarning {
    pub message: String,
    pub span: (usize, usize),
    pub warning_code: ParseWarningCode,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ParseWarningCode {
    AmbiguousInterpretation,
    UnusedVariable,
    RedundantParentheses,
    DeprecatedSyntax,
    LowConfidence,
    PotentialBug,
}

/// Unresolved reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnresolvedRef {
    pub name: String,
    pub kind: RefKind,
    pub span: (usize, usize),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RefKind {
    Variable,
    Function,
    Type,
    Effect,
    Module,
    Trait,
}

/// NL to GIR compiler
pub struct NLCompiler {
    pub type_checker: TypeChecker,
    pub symbol_table: SymbolTable,
    pub effect_context: EffectSafetyContext,
    pub parse_cache: HashMap<String, SemanticParseResult>,
    pub config: NLCompilerConfig,
}

/// Compiler configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NLCompilerConfig {
    pub strict_mode: bool,
    pub allow_ambiguous: bool,
    pub infer_effects: bool,
    pub require_type_annotations: bool,
    pub max_ambiguity_threshold: f32,
    pub enable_ai_assist: bool,
}

impl Default for NLCompilerConfig {
    fn default() -> Self {
        NLCompilerConfig {
            strict_mode: false,
            allow_ambiguous: true,
            infer_effects: true,
            require_type_annotations: false,
            max_ambiguity_threshold: 0.7,
            enable_ai_assist: true,
        }
    }
}

/// Symbol table for NL compilation
#[derive(Debug, Clone, Default)]
pub struct SymbolTable {
    pub variables: HashMap<String, SymbolInfo>,
    pub functions: HashMap<String, FunctionSymbol>,
    pub types: HashMap<String, TypeSymbol>,
    pub effects: HashMap<String, EffectSymbol>,
    pub modules: HashMap<String, ModuleSymbol>,
    pub scopes: Vec<Scope>,
    pub current_scope: usize,
}

impl SymbolTable {
    pub fn new() -> Self {
        let mut table = SymbolTable::default();
        table.scopes.push(Scope::new());
        table.current_scope = 0;
        table
    }

    pub fn push_scope(&mut self) {
        self.scopes.push(Scope::new());
        self.current_scope = self.scopes.len() - 1;
    }

    pub fn pop_scope(&mut self) {
        if self.scopes.len() > 1 {
            self.scopes.pop();
            self.current_scope = self.scopes.len() - 1;
        }
    }

    pub fn define_variable(&mut self, name: String, info: SymbolInfo) {
        if let Some(scope) = self.scopes.get_mut(self.current_scope) {
            scope.variables.insert(name.clone(), info.clone());
        }
        self.variables.insert(name, info);
    }

    pub fn define_function(&mut self, name: String, info: FunctionSymbol) {
        self.functions.insert(name, info);
    }

    pub fn define_type(&mut self, name: String, info: TypeSymbol) {
        self.types.insert(name, info);
    }

    pub fn define_effect(&mut self, name: String, info: EffectSymbol) {
        self.effects.insert(name, info);
    }

    pub fn lookup_variable(&self, name: &str) -> Option<&SymbolInfo> {
        // Check current scope first, then outer scopes
        for scope in self.scopes.iter().rev() {
            if let Some(info) = scope.variables.get(name) {
                return Some(info);
            }
        }
        self.variables.get(name)
    }

    pub fn lookup_function(&self, name: &str) -> Option<&FunctionSymbol> {
        self.functions.get(name)
    }

    pub fn lookup_type(&self, name: &str) -> Option<&TypeSymbol> {
        self.types.get(name)
    }

    pub fn lookup_effect(&self, name: &str) -> Option<&EffectSymbol> {
        self.effects.get(name)
    }
}

/// Scope in symbol table
#[derive(Debug, Clone, Default)]
pub struct Scope {
    pub variables: HashMap<String, SymbolInfo>,
    pub parent: Option<usize>,
}

impl Scope {
    pub fn new() -> Self {
        Scope::default()
    }
}

/// Symbol information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolInfo {
    pub name: String,
    pub symbol_type: OreType,
    pub is_mut: bool,
    pub is_const: bool,
    pub effects: EffectSet,
    pub definition_span: (usize, usize),
    pub is_parameter: bool,
    pub doc: Option<String>,
}

/// Function symbol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionSymbol {
    pub name: String,
    pub signature: FunctionType,
    pub is_async: bool,
    pub is_const: bool,
    pub is_unsafe: bool,
    pub definition_span: (usize, usize),
    pub doc: Option<String>,
    pub contracts: Vec<Contract>,
}

/// Type symbol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeSymbol {
    pub name: String,
    pub kind: TypeKind,
    pub definition: OreType,
    pub type_params: Vec<GenericParam>,
    pub where_clauses: Vec<WhereClause>,
    pub traits: Vec<String>,
    pub definition_span: (usize, usize),
    pub doc: Option<String>,
}

/// Effect symbol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectSymbol {
    pub name: String,
    pub kind: EffectKind,
    pub params: Vec<OreType>,
    pub handler: Option<EffectHandler>,
    pub definition_span: (usize, usize),
    pub doc: Option<String>,
}

/// Module symbol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleSymbol {
    pub name: String,
    pub exports: Vec<String>,
    pub imports: Vec<String>,
    pub definition_span: (usize, usize),
}

/// Contract for functions/types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contract {
    pub kind: ContractKind,
    pub condition: String, // NL condition
    pub condition_gir: Option<Box<dyn GirNode>>,
    pub message: Option<String>,
    pub span: (usize, usize),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ContractKind {
    Precondition,
    Postcondition,
    Invariant,
    Pure,
    Total,
    Deterministic,
}

/// NL to GIR compilation
impl NLCompiler {
    pub fn new(config: NLCompilerConfig) -> Self {
        NLCompiler {
            type_checker: TypeChecker::new(),
            symbol_table: SymbolTable::new(),
            effect_context: EffectSafetyContext::new(),
            parse_cache: HashMap::new(),
            config,
        }
    }

    pub fn compile(&mut self, nl_code: &str) -> SemanticParseResult {
        // Check cache
        if let Some(cached) = self.parse_cache.get(nl_code) {
            return cached.clone();
        }

        // Parse with Pest
        let parse_result = self.parse(nl_code);
        
        // Convert to GIR
        let gir_result = self.to_gir(&parse_result);
        
        // Type check
        let type_result = self.type_check(&gir_result);
        
        let result = SemanticParseResult {
            gir: type_result.gir,
            errors: parse_result.errors.into_iter()
                .chain(type_result.errors.into_iter())
                .collect(),
            warnings: parse_result.warnings.into_iter()
                .chain(type_result.warnings.into_iter())
                .collect(),
            unresolved_refs: parse_result.unresolved_refs,
        };

        // Cache result
        self.parse_cache.insert(nl_code.to_string(), result.clone());
        result
    }

    fn parse(&self, nl_code: &str) -> ParseResult {
        match NLParser::parse(Rule::program, nl_code) {
            Ok(mut pairs) => {
                let mut constructs = Vec::new();
                let mut errors = Vec::new();
                let mut warnings = Vec::new();
                let mut unresolved = Vec::new();

                for pair in pairs.next().unwrap().into_inner() {
                    match self.parse_construct(pair) {
                        Ok(construct) => constructs.push(construct),
                        Err(e) => errors.push(e),
                    }
                }

                ParseResult {
                    constructs,
                    errors,
                    warnings,
                    unresolved_refs: unresolved,
                }
            }
            Err(e) => {
                ParseResult {
                    constructs: Vec::new(),
                    errors: vec![ParseError {
                        message: format!("Parse error: {}", e),
                        span: (0, nl_code.len()),
                        error_code: ParseErrorCode::InvalidSyntax,
                        suggestions: vec!["Check syntax".to_string()],
                    }),
                    warnings: Vec::new(),
                    unresolved_refs: Vec::new(),
                }
            }
        }
    }

    fn parse_construct(&self, pair: pest::iterators::Pair<Rule>) -> Result<ParsedConstruct, ParseError> {
        let span = pair.as_span();
        let span_range = (span.start(), span.end());

        match pair.as_rule() {
            Rule::function_def => self.parse_function_def(pair, span_range),
            Rule::variable_def => self.parse_variable_def(pair, span_range),
            Rule::type_def => self.parse_type_def(pair, span_range),
            Rule::effect_def => self.parse_effect_def(pair, span_range),
            Rule::expression => self.parse_expression(pair, span_range),
            Rule::if_expr => self.parse_if_expr(pair, span_range),
            Rule::loop_expr => self.parse_loop_expr(pair, span_range),
            Rule::match_expr => self.parse_match_expr(pair, span_range),
            Rule::block => self.parse_block(pair, span_range),
            Rule::return_expr => self.parse_return_expr(pair, span_range),
            Rule::literal => self.parse_literal(pair, span_range),
            Rule::variable => self.parse_variable(pair, span_range),
            Rule::call => self.parse_call(pair, span_range),
            Rule::binary_op => self.parse_binary_op(pair, span_range),
            Rule::unary_op => self.parse_unary_op(pair, span_range),
            Rule::type_annotation => self.parse_type_annotation(pair, span_range),
            Rule::effect_annotation => self.parse_effect_annotation(pair, span_range),
            Rule::contract => self.parse_contract(pair, span_range),
            Rule::pattern => self.parse_pattern(pair, span_range),
            Rule::comment => self.parse_comment(pair, span_range),
            Rule::doc_string => self.parse_doc_string(pair, span_range),
            _ => {
                let mut children = Vec::new();
                for inner in pair.into_inner() {
                    if let Ok(child) = self.parse_construct(inner) {
                        children.push(child);
                    }
                }
                Ok(ParsedConstruct {
                    kind: ConstructKind::Block,
                    span: span_range,
                    children,
                    attributes: HashMap::new(),
                    confidence: 0.5,
                })
            }
        }
    }

    fn parse_function_def(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut children = Vec::new();
        let mut name = String::new();
        let mut params = Vec::new();
        let mut return_type = None;
        let mut effects = Vec::new();
        let mut is_async = false;
        let mut is_const = false;
        let mut contracts = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::parameter_list => {
                    for param in inner.into_inner() {
                        if let Ok(param_construct) = self.parse_parameter(param) {
                            children.push(param_construct);
                        }
                    }
                }
                Rule::return_type => {
                    if let Ok(ty_construct) = self.parse_type_annotation(inner, span) {
                        return_type = Some(ty_construct);
                    }
                }
                Rule::effect_list => {
                    for effect in inner.into_inner() {
                        if let Ok(effect_construct) = self.parse_effect_annotation(effect, span) {
                            effects.push(effect_construct);
                        }
                    }
                }
                Rule::async_kw => is_async = true,
                Rule::const_kw => is_const = true,
                Rule::contract => {
                    if let Ok(contract) = self.parse_contract(inner, span) {
                        contracts.push(contract);
                    }
                }
                Rule::block => {
                    if let Ok(block) = self.parse_block(inner, span) {
                        children.push(block);
                    }
                }
                _ => {}
            }
        }

        attributes.insert("name".to_string(), name);
        attributes.insert("is_async".to_string(), is_async.to_string());
        attributes.insert("is_const".to_string(), is_const.to_string());

        Ok(ParsedConstruct {
            kind: ConstructKind::FunctionDef,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_parameter(&self, pair: pest::iterators::Pair<Rule>) -> Result<ParsedConstruct, ParseError> {
        let span = (pair.as_span().start(), pair.as_span().end());
        let mut attributes = HashMap::new();
        let mut name = String::new();
        let mut param_type = None;
        let mut is_mut = false;
        let mut default = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::type_annotation => {
                    if let Ok(ty) = self.parse_type_annotation(inner, span) {
                        param_type = Some(ty);
                    }
                }
                Rule::mut_kw => attributes.insert("mut".to_string(), "true".to_string()),
                Rule::default_value => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        default = Some(expr);
                    }
                }
                _ => {}
            }
        }

        attributes.insert("name".to_string(), name);
        if let Some(ty) = param_type {
            attributes.insert("type".to_string(), format!("{:?}", ty));
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::VariableDef,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_variable_def(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut name = String::new();
        let mut var_type = None;
        let mut is_mut = false;
        let mut is_const = false;
        let mut initializer = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::type_annotation => {
                    if let Ok(ty) = self.parse_type_annotation(inner, span) {
                        var_type = Some(ty);
                    }
                }
                Rule::mut_kw => {
                    is_mut = true;
                    attributes.insert("mut".to_string(), "true".to_string());
                }
                Rule::const_kw => {
                    is_const = true;
                    attributes.insert("const".to_string(), "true".to_string());
                }
                Rule::expression => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        initializer = Some(expr);
                    }
                }
                _ => {}
            }
        }

        attributes.insert("name".to_string(), name);
        if let Some(ty) = var_type {
            attributes.insert("type".to_string(), format!("{:?}", ty));
        }
        attributes.insert("is_mut".to_string(), is_mut.to_string());
        attributes.insert("is_const".to_string(), is_const.to_string());

        let mut children = Vec::new();
        if let Some(init) = initializer {
            children.push(init);
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::VariableDef,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_type_def(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut name = String::new();
        let mut type_params = Vec::new();
        let mut body = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::type_parameter_list => {
                    for param in inner.into_inner() {
                        if let Ok(param) = self.parse_type_parameter(param) {
                            type_params.push(param);
                        }
                    }
                }
                Rule::type_def_body => {
                    if let Ok(ty) = self.parse_type_annotation(inner, span) {
                        body = Some(ty);
                    }
                }
                _ => {}
            }
        }

        attributes.insert("name".to_string(), name);
        attributes.insert("type_params".to_string(), format!("{:?}", type_params));

        let mut children = Vec::new();
        if let Some(b) = body {
            children.push(b);
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::TypeDef,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_type_parameter(&self, pair: pest::iterators::Pair<Rule>) -> Result<ParsedConstruct, ParseError> {
        let span = (pair.as_span().start(), pair.as_span().end());
        let mut name = String::new();
        let mut constraints = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::trait_bound => constraints.push(inner.as_str().to_string()),
                _ => {}
            }
        }

        let mut attributes = HashMap::new();
        attributes.insert("name".to_string(), name);
        if !constraints.is_empty() {
            attributes.insert("constraints".to_string(), constraints.join(", "));
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::GenericType,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_effect_def(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut name = String::new();
        let mut params = Vec::new();
        let mut handler = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => name = inner.as_str().to_string(),
                Rule::parameter_list => {
                    for param in inner.into_inner() {
                        if let Ok(ty) = self.parse_type_annotation(param, span) {
                            params.push(ty);
                        }
                    }
                }
                Rule::handler_block => {
                    // Parse handler
                }
                _ => {}
            }
        }

        attributes.insert("name".to_string(), name);
        attributes.insert("params".to_string(), format!("{:?}", params));

        Ok(ParsedConstruct {
            kind: ConstructKind::EffectDef,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_expression(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut attributes = HashMap::new();

        // Find the actual expression inside
        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::literal => {
                    if let Ok(lit) = self.parse_literal(inner, span) {
                        return Ok(lit);
                    }
                }
                Rule::variable => {
                    if let Ok(var) = self.parse_variable(inner, span) {
                        return Ok(var);
                    }
                }
                Rule::call => {
                    if let Ok(call) = self.parse_call(inner, span) {
                        return Ok(call);
                    }
                }
                Rule::binary_op => {
                    if let Ok(op) = self.parse_binary_op(inner, span) {
                        return Ok(op);
                    }
                }
                Rule::unary_op => {
                    if let Ok(op) = self.parse_unary_op(inner, span) {
                        return Ok(op);
                    }
                }
                Rule::if_expr => {
                    if let Ok(if_expr) = self.parse_if_expr(inner, span) {
                        return Ok(if_expr);
                    }
                }
                Rule::loop_expr => {
                    if let Ok(loop_expr) = self.parse_loop_expr(inner, span) {
                        return Ok(loop_expr);
                    }
                }
                Rule::match_expr => {
                    if let Ok(match_expr) = self.parse_match_expr(inner, span) {
                        return Ok(match_expr);
                    }
                }
                Rule::block => {
                    if let Ok(block) = self.parse_block(inner, span) {
                        return Ok(block);
                    }
                }
                Rule::return_expr => {
                    if let Ok(ret) = self.parse_return_expr(inner, span) {
                        return Ok(ret);
                    }
                }
                Rule::handle_expr => {
                    if let Ok(handle) = self.parse_handle_expr(inner, span) {
                        return Ok(handle);
                    }
                }
                _ => {
                    if let Ok(child) = self.parse_construct(inner) {
                        children.push(child);
                    }
                }
            }
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::Block,
            span,
            children,
            attributes,
            confidence: 0.5,
        })
    }

    fn parse_literal(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let text = pair.as_str();

        // Determine literal type
        let lit_type = if text.starts_with('"') || text.starts_with('\'') {
            "string"
        } else if text.chars().all(|c| c.is_ascii_digit()) {
            "int"
        } else if text.contains('.') && text.chars().all(|c| c.is_ascii_digit() || c == '.') {
            "float"
        } else if text == "true" || text == "false" {
            "bool"
        } else {
            "unknown"
        };

        attributes.insert("value".to_string(), text.to_string());
        attributes.insert("literal_type".to_string(), lit_type.to_string());

        Ok(ParsedConstruct {
            kind: ConstructKind::Literal,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.95,
        })
    }

    fn parse_variable(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let name = pair.as_str().to_string();
        attributes.insert("name".to_string(), name);

        Ok(ParsedConstruct {
            kind: ConstructKind::Variable,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_call(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut children = Vec::new();
        let mut callee = String::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => callee = inner.as_str().to_string(),
                Rule::argument_list => {
                    for arg in inner.into_inner() {
                        if let Ok(arg_construct) = self.parse_expression(inner, span) {
                            children.push(arg_construct);
                        }
                    }
                }
                _ => {}
            }
        }

        attributes.insert("callee".to_string(), callee);
        attributes.insert("arg_count".to_string(), children.len().to_string());

        Ok(ParsedConstruct {
            kind: ConstructKind::Call,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_binary_op(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut children = Vec::new();
        let mut operator = String::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        children.push(expr);
                    }
                }
                Rule::operator => operator = inner.as_str().to_string(),
                _ => {}
            }
        }

        attributes.insert("operator".to_string(), operator);

        Ok(ParsedConstruct {
            kind: ConstructKind::BinaryOp,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_unary_op(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut children = Vec::new();
        let mut operator = String::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        children.push(expr);
                    }
                }
                Rule::operator => operator = inner.as_str().to_string(),
                _ => {}
            }
        }

        attributes.insert("operator".to_string(), operator);

        Ok(ParsedConstruct {
            kind: ConstructKind::UnaryOp,
            span,
            children,
            attributes,
            confidence: 0.9,
        })
    }

    fn parse_if_expr(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut condition = None;
        let mut then_branch = None;
        let mut else_branch = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if condition.is_none() {
                        if let Ok(cond) = self.parse_expression(inner, span) {
                            condition = Some(cond);
                        }
                    } else if then_branch.is_none() {
                        if let Ok(branch) = self.parse_block(inner, span) {
                            then_branch = Some(branch);
                        }
                    } else if else_branch.is_none() {
                        if let Ok(branch) = self.parse_block(inner, span) {
                            else_branch = Some(branch);
                        }
                    }
                }
                Rule::block => {
                    if then_branch.is_none() {
                        if let Ok(block) = self.parse_block(inner, span) {
                            then_branch = Some(block);
                        }
                    } else if else_branch.is_none() {
                        if let Ok(block) = self.parse_block(inner, span) {
                            else_branch = Some(block);
                        }
                    }
                }
                Rule::else_kw => {}
                _ => {}
            }
        }

        let mut children = Vec::new();
        if let Some(cond) = condition { children.push(cond); }
        if let Some(then_b) = then_branch { children.push(then_b); }
        if let Some(else_b) = else_branch { children.push(else_b); }

        Ok(ParsedConstruct {
            kind: ConstructKind::IfExpr,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_loop_expr(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut condition = None;
        let mut body = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if let Ok(cond) = self.parse_expression(inner, span) {
                        condition = Some(cond);
                    }
                }
                Rule::block => {
                    if let Ok(b) = self.parse_block(inner, span) {
                        body = Some(b);
                    }
                }
                _ => {}
            }
        }

        if let Some(cond) = condition { children.push(cond); }
        if let Some(b) = body { children.push(b); }

        Ok(ParsedConstruct {
            kind: ConstructKind::LoopExpr,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_match_expr(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut scrutinee = None;
        let mut arms = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if scrutinee.is_none() {
                        if let Ok(expr) = self.parse_expression(inner, span) {
                            scrutinee = Some(expr);
                        }
                    }
                }
                Rule::match_arm => {
                    if let Ok(arm) = self.parse_match_arm(inner, span) {
                        arms.push(arm);
                    }
                }
                _ => {}
            }
        }

        if let Some(scrut) = scrutinee { children.push(scrut); }
        children.extend(arms);

        Ok(ParsedConstruct {
            kind: ConstructKind::MatchExpr,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_match_arm(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut pattern = None;
        let mut guard = None;
        let mut body = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::pattern => {
                    if let Ok(p) = self.parse_pattern(inner, span) {
                        pattern = Some(p);
                    }
                }
                Rule::if_expr => {
                    if let Ok(g) = self.parse_expression(inner, span) {
                        guard = Some(g);
                    }
                }
                Rule::block => {
                    if let Ok(b) = self.parse_block(inner, span) {
                        body = Some(b);
                    }
                }
                _ => {}
            }
        }

        if let Some(p) = pattern { children.push(p); }
        if let Some(g) = guard { children.push(g); }
        if let Some(b) = body { children.push(b); }

        Ok(ParsedConstruct {
            kind: ConstructKind::Pattern,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_block(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        children.push(expr);
                    }
                }
                Rule::variable_def => {
                    if let Ok(var) = self.parse_variable_def(inner, span) {
                        children.push(var);
                    }
                }
                Rule::return_expr => {
                    if let Ok(ret) = self.parse_return_expr(inner, span) {
                        children.push(ret);
                    }
                }
                _ => {
                    if let Ok(child) = self.parse_construct(inner) {
                        children.push(child);
                    }
                }
            }
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::Block,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_return_expr(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut value = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if let Ok(expr) = self.parse_expression(inner, span) {
                        value = Some(expr);
                    }
                }
                _ => {}
            }
        }

        if let Some(v) = value { children.push(v); }

        Ok(ParsedConstruct {
            kind: ConstructKind::Return,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.9,
        })
    }

    fn parse_handle_expr(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut expr = None;
        let mut handlers = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::expression => {
                    if expr.is_none() {
                        if let Ok(e) = self.parse_expression(inner, span) {
                            expr = Some(e);
                        }
                    }
                }
                Rule::handler_clause => {
                    if let Ok(h) = self.parse_handler_clause(inner, span) {
                        handlers.push(h);
                    }
                }
                _ => {}
            }
        }

        if let Some(e) = expr { children.push(e); }
        children.extend(handlers);

        Ok(ParsedConstruct {
            kind: ConstructKind::MatchExpr, // Reuse for handle
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.8,
        })
    }

    fn parse_handler_clause(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut children = Vec::new();
        let mut effect = String::new();
        let mut pattern = None;
        let mut body = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => effect = inner.as_str().to_string(),
                Rule::pattern => {
                    if let Ok(p) = self.parse_pattern(inner, span) {
                        pattern = Some(p);
                    }
                }
                Rule::block => {
                    if let Ok(b) = self.parse_block(inner, span) {
                        body = Some(b);
                    }
                }
                _ => {}
            }
        }

        if let Some(p) = pattern { children.push(p); }
        if let Some(b) = body { children.push(b); }

        Ok(ParsedConstruct {
            kind: ConstructKind::MatchExpr,
            span,
            children,
            attributes: HashMap::new(),
            confidence: 0.8,
        })
    }

    fn parse_pattern(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut pattern_type = String::new();
        let mut children = Vec::new();

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::identifier => {
                    pattern_type = "binding".to_string();
                    attributes.insert("name".to_string(), inner.as_str().to_string());
                }
                Rule::literal => {
                    pattern_type = "literal".to_string();
                    if let Ok(lit) = self.parse_literal(inner, span) {
                        children.push(lit);
                    }
                }
                Rule::constructor_pattern => {
                    pattern_type = "constructor".to_string();
                    // Parse constructor pattern
                }
                _ => {}
            }
        }

        attributes.insert("pattern_type".to_string(), pattern_type);

        Ok(ParsedConstruct {
            kind: ConstructKind::Pattern,
            span,
            children,
            attributes,
            confidence: 0.8,
        })
    }

    fn parse_type_annotation(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let type_text = pair.as_str().to_string();
        attributes.insert("type_text".to_string(), type_text);

        Ok(ParsedConstruct {
            kind: ConstructKind::PrimitiveType,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.8,
        })
    }

    fn parse_effect_annotation(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let effect_text = pair.as_str().to_string();
        attributes.insert("effect_text".to_string(), effect_text);

        Ok(ParsedConstruct {
            kind: ConstructKind::EffectAnnotation,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.8,
        })
    }

    fn parse_contract(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        let mut attributes = HashMap::new();
        let mut kind = ContractKind::Precondition;
        let mut condition = String::new();
        let mut message = None;

        for inner in pair.into_inner() {
            match inner.as_rule() {
                Rule::contract_kind => kind = match inner.as_str() {
                    "pre" => ContractKind::Precondition,
                    "post" => ContractKind::Postcondition,
                    "invariant" => ContractKind::Invariant,
                    "pure" => ContractKind::Pure,
                    _ => ContractKind::Precondition,
                },
                Rule::expression => condition = inner.as_str().to_string(),
                Rule::string_literal => message = Some(inner.as_str().to_string()),
                _ => {}
            }
        }

        attributes.insert("kind".to_string(), format!("{:?}", kind));
        attributes.insert("condition".to_string(), condition);
        if let Some(msg) = message {
            attributes.insert("message".to_string(), msg);
        }

        Ok(ParsedConstruct {
            kind: ConstructKind::ContractDef,
            span,
            children: Vec::new(),
            attributes,
            confidence: 0.8,
        })
    }

    fn parse_comment(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        Ok(ParsedConstruct {
            kind: ConstructKind::Comment,
            span,
            children: Vec::new(),
            attributes: {
                let mut attrs = HashMap::new();
                attrs.insert("text".to_string(), pair.as_str().to_string());
                attrs
            },
            confidence: 1.0,
        })
    }

    fn parse_doc_string(&self, pair: pest::iterators::Pair<Rule>, span: (usize, usize)) -> Result<ParsedConstruct, ParseError> {
        Ok(ParsedConstruct {
            kind: ConstructKind::DocString,
            span,
            children: Vec::new(),
            attributes: {
                let mut attrs = HashMap::new();
                attrs.insert("text".to_string(), pair.as_str().to_string());
                attrs
            },
            confidence: 1.0,
        })
    }

    fn to_gir(&self, parse_result: &ParseResult) -> Result<Box<dyn GirNode>, String> {
        // Convert parsed constructs to GIR
        // This is a simplified version - real implementation would be more complex
        Ok(Box::new(MetaNode::new(
            NodeId(0),
            MetaKind::Documentation,
            serde_json::json!({"constructs": parse_result.constructs.len()})
        )))
    }

    fn type_check(&self, gir: &Result<Box<dyn GirNode>, String>) -> SemanticParseResult {
        match gir {
            Ok(node) => {
                let result = self.type_checker.check_graph(&GirGraph::new(GraphId(0), "main".to_string()));
                SemanticParseResult {
                    gir: Some(node),
                    errors: result.errors.into_iter().map(|e| ParseError {
                        message: e.message,
                        location: e.location.clone(),
                        error_code: e.error_code,
                        suggestions: e.suggested_fixes,
                    }).collect(),
                    warnings: result.warnings.into_iter().map(|w| ParseWarning {
                        message: w.message,
                        location: w.location.clone(),
                        warning_code: w.warning_code,
                    }).collect(),
                    unresolved_refs: Vec::new(),
                }
            }
            Err(e) => {
                SemanticParseResult {
                    gir: None,
                    errors: vec![ParseError {
                        message: e,
                        span: (0, 0),
                        error_code: ParseErrorCode::InvalidSyntax,
                        suggestions: vec![],
                    }],
                    warnings: Vec::new(),
                    unresolved_refs: Vec::new(),
                }
            }
        }
    }
}

/// Parse result from Pest
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParseResult {
    pub constructs: Vec<ParsedConstruct>,
    pub errors: Vec<ParseError>,
    pub warnings: Vec<ParseWarning>,
    pub unresolved_refs: Vec<UnresolvedRef>,
}

/// Interactive NL REPL
pub struct NLRepl {
    compiler: NLCompiler,
    history: Vec<String>,
}

impl NLRepl {
    pub fn new(config: NLCompilerConfig) -> Self {
        NLRepl {
            compiler: NLCompiler::new(config),
            history: Vec::new(),
        }
    }

    pub fn run(&mut self, input: &str) -> SemanticParseResult {
        self.history.push(input.to_string());
        self.compiler.compile(input)
    }

    pub fn get_history(&self) -> &[String] {
        &self.history
    }

    pub fn clear_cache(&mut self) {
        self.compiler.parse_cache.clear();
    }
}

/// Batch compilation for files
pub fn compile_file(compiler: &mut NLCompiler, path: &std::path::Path) -> Result<SemanticParseResult, String> {
    let content = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
    Ok(compiler.compile(&content))
}

/// Compile multiple files
pub fn compile_project(compiler: &mut NLCompiler, paths: &[std::path::PathBuf]) -> Vec<SemanticParseResult> {
    paths.iter()
        .map(|p| compile_file(compiler, p))
        .collect::<Result<Vec<_>, _>>()
        .unwrap_or_default()
}

/// IDE integration: semantic tokens for highlighting
pub fn get_semantic_tokens(parse_result: &ParseResult) -> Vec<SemanticToken> {
    let mut tokens = Vec::new();
    
    for construct in &parse_result.constructs {
        tokens.push(SemanticToken {
            start: construct.span.0 as u32,
            end: construct.span.1 as u32,
            token_type: construct.kind as u32,
            modifiers: 0,
        });
        
        for child in &construct.children {
            tokens.extend(get_semantic_tokens(&ParseResult {
                constructs: vec![child.clone()],
                errors: Vec::new(),
                warnings: Vec::new(),
                unresolved_refs: Vec::new(),
            }));
        }
    }
    
    tokens
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticToken {
    pub start: u32,
    pub end: u32,
    pub token_type: u32,
    pub modifiers: u32,
}

/// Completion suggestions
pub fn get_completions(
    compiler: &NLCompiler,
    code: &str,
    position: usize,
) -> Vec<CompletionItem> {
    let mut items = Vec::new();
    
    // Get word at position
    let word = extract_word_at(code, position);
    
    // Add keywords
    for kw in KEYWORDS {
        if kw.starts_with(&word) {
            items.push(CompletionItem {
                label: kw.to_string(),
                kind: CompletionKind::Keyword,
                detail: Some("Keyword".to_string()),
                documentation: None,
            });
        }
    }
    
    // Add variables from symbol table
    for (name, info) in &compiler.symbol_table.variables {
        if name.starts_with(&word) {
            items.push(CompletionItem {
                label: name.clone(),
                kind: CompletionKind::Variable,
                detail: Some(format!("{}", info.symbol_type)),
                documentation: info.doc.clone(),
            });
        }
    }
    
    // Add functions
    for (name, info) in &compiler.symbol_table.functions {
        if name.starts_with(&word) {
            items.push(CompletionItem {
                label: name.clone(),
                kind: CompletionKind::Function,
                detail: Some(format!("{}", info.signature)),
                documentation: info.doc.clone(),
            });
        }
    }
    
    // Add types
    for (name, info) in &compiler.symbol_table.types {
        if name.starts_with(&word) {
            items.push(CompletionItem {
                label: name.clone(),
                kind: CompletionKind::Type,
                detail: Some(format!("{}", info.definition)),
                documentation: info.doc.clone(),
            });
        }
    }
    
    items
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletionItem {
    pub label: String,
    pub kind: CompletionKind,
    pub detail: Option<String>,
    pub documentation: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CompletionKind {
    Keyword,
    Variable,
    Function,
    Type,
    Effect,
    Module,
    Trait,
    Constant,
    Snippet,
}

fn extract_word_at(code: &str, position: usize) -> String {
    let chars: Vec<char> = code.chars().collect();
    if position >= chars.len() {
        return String::new();
    }
    
    let mut start = position;
    while start > 0 && chars[start - 1].is_alphanumeric() || chars[start - 1] == '_' {
        start -= 1;
    }
    
    let mut end = position;
    while end < chars.len() && (chars[end].is_alphanumeric() || chars[end] == '_') {
        end += 1;
    }
    
    chars[start..end].iter().collect()
}

const KEYWORDS: &[&str] = &[
    "function", "fn", "let", "const", "mut", "if", "else", "loop", "while", "for",
    "match", "return", "break", "continue", "async", "await", "handle", "try",
    "type", "effect", "contract", "struct", "enum", "trait", "impl", "use", "mod",
    "pub", "priv", "async", "await", "spawn", "join", "yield",
    "true", "false", "null", "none", "some",
    "int", "float", "bool", "string", "char", "bytes",
    "Option", "Result", "Vec", "Map", "HashMap",
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_symbol_table() {
        let mut table = SymbolTable::new();
        
        table.define_variable("x".to_string(), SymbolInfo {
            name: "x".to_string(),
            symbol_type: OreType::Primitive(PrimitiveType::Int32),
            is_mut: false,
            is_const: true,
            effects: EffectSet::new(),
            definition_span: (0, 1),
            is_parameter: false,
            doc: None,
        });
        
        assert!(table.lookup_variable("x").is_some());
        assert!(table.lookup_variable("y").is_none());
    }

    #[test]
    fn test_symbol_table_scopes() {
        let mut table = SymbolTable::new();
        
        table.define_variable("x".to_string(), SymbolInfo {
            name: "x".to_string(),
            symbol_type: OreType::Primitive(PrimitiveType::Int32),
            is_mut: false,
            is_const: true,
            effects: EffectSet::new(),
            definition_span: (0, 1),
            is_parameter: false,
            doc: None,
        });
        
        table.push_scope();
        table.define_variable("y".to_string(), SymbolInfo {
            name: "y".to_string(),
            symbol_type: OreType::Primitive(PrimitiveType::Int32),
            is_mut: false,
            is_const: true,
            effects: EffectSet::new(),
            definition_span: (0, 1),
            is_parameter: false,
            doc: None,
        });
        
        assert!(table.lookup_variable("x").is_some());
        assert!(table.lookup_variable("y").is_some());
        
        table.pop_scope();
        
        assert!(table.lookup_variable("x").is_some());
        assert!(table.lookup_variable("y").is_none());
    }

    #[test]
    fn test_compiler_config() {
        let config = NLCompilerConfig::default();
        assert!(!config.strict_mode);
        assert!(config.allow_ambiguous);
        assert!(config.infer_effects);
    }

    #[test]
    fn test_parse_error_display() {
        let error = ParseError {
            message: "Expected expression".to_string(),
            span: (10, 20),
            error_code: ParseErrorCode::ExpectedExpression,
            suggestions: vec!["Add expression here".to_string()],
        };
        
        assert!(error.message.contains("Expected expression"));
    }

    #[test]
    fn test_semantic_tokens() {
        let construct = ParsedConstruct {
            kind: ConstructKind::FunctionDef,
            span: (0, 10),
            children: Vec::new(),
            attributes: HashMap::new(),
            confidence: 0.9,
        };
        
        let result = ParseResult {
            constructs: vec![construct],
            errors: Vec::new(),
            warnings: Vec::new(),
            unresolved_refs: Vec::new(),
        };
        
        let tokens = get_semantic_tokens(&result);
        assert_eq!(tokens.len(), 1);
        assert_eq!(tokens[0].token_type, ConstructKind::FunctionDef as u32);
    }
}