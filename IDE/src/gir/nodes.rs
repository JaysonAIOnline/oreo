//! GIR Node Definitions
//!
//! All node types in the Graph Intermediate Representation

use super::*;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// Value nodes - literals, variables, parameters, constants
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValueNode {
    pub id: NodeId,
    pub kind: ValueKind,
    pub value_type: TypeId,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port>,
    pub metadata: NodeMetadata,
}

impl ValueNode {
    pub fn new(id: NodeId, kind: ValueKind, value_type: TypeId) -> Self {
        let output_port = Port {
            id: PortId { node_id: id, index: 0, direction: PortDirection::Output },
            name: "value".to_string(),
            port_type: value_type,
            direction: PortDirection::Output,
            is_required: true,
            default_value: None,
        };

        ValueNode {
            id,
            kind,
            value_type,
            input_ports: vec![],
            output_ports: vec![output_port],
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for ValueNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Value }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

/// Kinds of value nodes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ValueKind {
    Literal,
    Variable,
    Parameter,
    Constant,
}

/// Operation nodes - arithmetic, logic, comparison, cast, call
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpNode {
    pub id: NodeId,
    pub op: OpKind,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port>,
    pub metadata: NodeMetadata,
}

impl OpNode {
    pub fn new(id: NodeId, op: OpKind, input_types: Vec<TypeId>, output_type: TypeId) -> Self {
        let mut input_ports = Vec::new();
        for (i, ty) in input_types.iter().enumerate() {
            input_ports.push(Port {
                id: PortId { node_id: id, index: i as u32, direction: PortDirection::Input },
                name: format!("arg{}", i),
                port_type: *ty,
                direction: PortDirection::Input,
                is_required: true,
                default_value: None,
            });
        }

        let output_port = Port {
            id: PortId { node_id: id, index: input_types.len() as u32, direction: PortDirection::Output },
            name: "result".to_string(),
            port_type: output_type,
            direction: PortDirection::Output,
            is_required: true,
            default_value: None,
        };

        OpNode {
            id,
            op,
            input_ports,
            output_ports: vec![output_port],
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for OpNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Op }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

/// Operation kinds
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum OpKind {
    // Arithmetic
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    Neg,
    // Logic
    And,
    Or,
    Not,
    Xor,
    // Comparison
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    // Bitwise
    BitAnd,
    BitOr,
    BitXor,
    BitNot,
    Shl,
    Shr,
    // Cast/Conversion
    Cast,
    // Function call
    Call,
    // Memory
    Load,
    Store,
    // Array/Collection
    Index,
    Length,
    // String
    Concat,
    // Custom/External
    Custom,
}

/// Control flow nodes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlNode {
    pub id: NodeId,
    pub kind: ControlKind,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port>,
    pub metadata: NodeMetadata,
}

impl ControlNode {
    pub fn new(id: NodeId, kind: ControlKind, input_types: Vec<TypeId>, output_types: Vec<TypeId>) -> Self {
        let mut input_ports = Vec::new();
        for (i, ty) in input_types.iter().enumerate() {
            input_ports.push(Port {
                id: PortId { node_id: id, index: i as u32, direction: PortDirection::Input },
                name: format!("input{}", i),
                port_type: *ty,
                direction: PortDirection::Input,
                is_required: true,
                default_value: None,
            });
        }

        let mut output_ports = Vec::new();
        for (i, ty) in output_types.iter().enumerate() {
            output_ports.push(Port {
                id: PortId { node_id: id, index: (input_types.len() + i) as u32, direction: PortDirection::Output },
                name: format!("output{}", i),
                port_type: *ty,
                direction: PortDirection::Output,
                is_required: true,
                default_value: None,
            });
        }

        ControlNode {
            id,
            kind,
            input_ports,
            output_ports,
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for ControlNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Control }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

/// Control flow kinds
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ControlKind {
    If,
    Loop,
    Match,
    Try,
    Sequence,
    Parallel,
    Break,
    Continue,
    Return,
    Yield,
    Await,
    Spawn,
    Join,
}

/// Type nodes - type definitions and annotations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeNode {
    pub id: NodeId,
    pub kind: TypeNodeKind,
    pub defined_type: Option<TypeId>,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port>,
    pub metadata: NodeMetadata,
}

impl TypeNode {
    pub fn new(id: NodeId, kind: TypeNodeKind, defined_type: Option<TypeId>) -> Self {
        TypeNode {
            id,
            kind,
            defined_type,
            input_ports: vec![],
            output_ports: vec![],
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for TypeNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Type }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TypeNodeKind {
    Primitive,
    Composite,
    Function,
    Effect,
    Generic,
    Alias,
}

/// Effect nodes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectNode {
    pub id: NodeId,
    pub effect_id: EffectId,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port],
    pub metadata: NodeMetadata,
}

impl EffectNode {
    pub fn new(id: NodeId, effect_id: EffectId, input_types: Vec<TypeId>, output_type: TypeId) -> Self {
        let mut input_ports = Vec::new();
        for (i, ty) in input_types.iter().enumerate() {
            input_ports.push(Port {
                id: PortId { node_id: id, index: i as u32, direction: PortDirection::Input },
                name: format!("arg{}", i),
                port_type: *ty,
                direction: PortDirection::Input,
                is_required: true,
                default_value: None,
            });
        }

        let output_port = Port {
            id: PortId { node_id: id, index: input_types.len() as u32, direction: PortDirection::Output },
            name: "result".to_string(),
            port_type: output_type,
            direction: PortDirection::Output,
            is_required: true,
            default_value: None,
        };

        EffectNode {
            id,
            effect_id,
            input_ports,
            output_ports: vec![output_port],
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for EffectNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Effect }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

/// Meta nodes - contracts, annotations, documentation, source maps
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetaNode {
    pub id: NodeId,
    pub kind: MetaKind,
    pub content: serde_json::Value,
    pub input_ports: Vec<Port>,
    pub output_ports: Vec<Port>,
    pub metadata: NodeMetadata,
}

impl MetaNode {
    pub fn new(id: NodeId, kind: MetaKind, content: serde_json::Value) -> Self {
        MetaNode {
            id,
            kind,
            content,
            input_ports: vec![],
            output_ports: vec![],
            metadata: NodeMetadata::default(),
        }
    }
}

impl GirNode for MetaNode {
    fn id(&self) -> NodeId { self.id }
    fn node_type(&self) -> NodeType { NodeType::Meta }
    fn input_ports(&self) -> &[Port] { &self.input_ports }
    fn output_ports(&self) -> &[Port] { &self.output_ports }
    fn metadata(&self) -> &NodeMetadata { &self.metadata }
    fn metadata_mut(&mut self) -> &mut NodeMetadata { &mut self.metadata }
    fn clone_box(&self) -> Box<dyn GirNode> { Box::new(self.clone()) }
    fn as_any(&self) -> &dyn std::any::Any { self }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any { self }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MetaKind {
    Contract,
    Annotation,
    Documentation,
    SourceMap,
    DebugInfo,
}

/// Factory functions for creating nodes
pub fn create_value_node(ctx: &mut GirContext, kind: ValueKind, value_type: TypeId) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(ValueNode::new(id, kind, value_type))
}

pub fn create_op_node(ctx: &mut GirContext, op: OpKind, input_types: Vec<TypeId>, output_type: TypeId) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(OpNode::new(id, op, input_types, output_type))
}

pub fn create_control_node(ctx: &mut GirContext, kind: ControlKind, input_types: Vec<TypeId>, output_types: Vec<TypeId>) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(ControlNode::new(id, kind, input_types, output_types))
}

pub fn create_type_node(ctx: &mut GirContext, kind: TypeNodeKind, defined_type: Option<TypeId>) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(TypeNode::new(id, kind, defined_type))
}

pub fn create_effect_node(ctx: &mut GirContext, effect_id: EffectId, input_types: Vec<TypeId>, output_type: TypeId) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(EffectNode::new(id, effect_id, input_types, output_type))
}

pub fn create_meta_node(ctx: &mut GirContext, kind: MetaKind, content: serde_json::Value) -> Box<dyn GirNode> {
    let id = ctx.next_node_id();
    Box::new(MetaNode::new(id, kind, content))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gir::*;

    #[test]
    fn test_value_node_creation() {
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        
        assert_eq!(node.id(), NodeId(1));
        assert_eq!(node.node_type(), NodeType::Value);
        assert_eq!(node.output_ports().len(), 1);
        assert_eq!(node.input_ports().len(), 0);
    }

    #[test]
    fn test_op_node_creation() {
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node = create_op_node(&mut ctx, OpKind::Add, vec![type_id, type_id], type_id);
        
        assert_eq!(node.id(), NodeId(1));
        assert_eq!(node.node_type(), NodeType::Op);
        assert_eq!(node.input_ports().len(), 2);
        assert_eq!(node.output_ports().len(), 1);
    }

    #[test]
    fn test_control_node_creation() {
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node = create_control_node(&mut ctx, ControlKind::If, vec![type_id], vec![type_id, type_id]);
        
        assert_eq!(node.id(), NodeId(1));
        assert_eq!(node.node_type(), NodeType::Control);
        assert_eq!(node.input_ports().len(), 1);
        assert_eq!(node.output_ports().len(), 2);
    }

    #[test]
    fn test_node_cloning() {
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let cloned = node.clone_box();
        
        assert_eq!(cloned.id(), node.id());
        assert_eq!(cloned.node_type(), node.node_type());
    }
}