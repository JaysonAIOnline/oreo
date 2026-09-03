//! GIR Edge Definitions and Graph Structure
//!
//! Edge types and graph manipulation utilities

use super::*;
use std::collections::{HashMap, HashSet, VecDeque};
use petgraph::visit::{IntoNeighbors, IntoNodeIdentifiers};
use petgraph::Direction;

/// Enhanced edge with validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatedEdge {
    pub edge: GirEdge,
    pub is_valid: bool,
    pub validation_errors: Vec<String>,
}

impl ValidatedEdge {
    pub fn new(edge: GirEdge) -> Self {
        ValidatedEdge {
            edge,
            is_valid: true,
            validation_errors: Vec::new(),
        }
    }

    pub fn invalidate(&mut self, error: String) {
        self.is_valid = false;
        self.validation_errors.push(error);
    }
}

/// Graph with petgraph backend for algorithms
#[derive(Debug, Clone)]
pub struct GirGraph {
    pub id: GraphId,
    pub name: String,
    /// Nodes stored in a HashMap for O(1) lookup
    pub nodes: HashMap<NodeId, Box<dyn GirNode>>,
    /// Edges stored in a HashMap
    pub edges: HashMap<EdgeId, GirEdge>,
    /// Petgraph graph for algorithms (connectivity, cycles, etc.)
    petgraph: petgraph::Graph<NodeId, EdgeId>,
    /// Mapping from our NodeId to petgraph NodeIndex
    node_to_pg: HashMap<NodeId, petgraph::prelude::NodeIndex>,
    /// Mapping from petgraph NodeIndex to our NodeId
    pg_to_node: HashMap<petgraph::prelude::NodeIndex, NodeId>,
    /// Entry points
    pub entry_points: Vec<NodeId>,
    /// Metadata
    pub metadata: NodeMetadata,
}

impl GirGraph {
    pub fn new(id: GraphId, name: String) -> Self {
        GirGraph {
            id,
            name,
            nodes: HashMap::new(),
            edges: HashMap::new(),
            petgraph: petgraph::Graph::new(),
            node_to_pg: HashMap::new(),
            pg_to_node: HashMap::new(),
            entry_points: Vec::new(),
            metadata: NodeMetadata::default(),
        }
    }

    /// Add a node to the graph
    pub fn add_node(&mut self, node: Box<dyn GirNode>) -> NodeId {
        let node_id = node.id();
        self.nodes.insert(node_id, node);
        
        // Add to petgraph
        let pg_idx = self.petgraph.add_node(node_id);
        self.node_to_pg.insert(node_id, pg_idx);
        self.pg_to_node.insert(pg_idx, node_id);
        
        // Initialize adjacency
        self.node_to_pg.insert(node_id, pg_idx);
        
        node_id
    }

    /// Remove a node and all its edges
    pub fn remove_node(&mut self, node_id: NodeId) -> bool {
        if self.nodes.remove(&node_id).is_none() {
            return false;
        }

        // Remove all edges connected to this node
        let edges_to_remove: Vec<EdgeId> = self.edges.iter()
            .filter(|(_, e)| e.source.node_id == node_id || e.target.node_id == node_id)
            .map(|(id, _)| *id)
            .collect();

        for edge_id in edges_to_remove {
            self.remove_edge(edge_id);
        }

        // Remove from petgraph
        if let Some(pg_idx) = self.node_to_pg.remove(&node_id) {
            self.petgraph.remove_node(pg_idx);
            self.pg_to_node.remove(&pg_idx);
        }

        true
    }

    /// Add an edge between two ports
    pub fn add_edge(&mut self, source: PortId, target: PortId, edge_type: EdgeType) -> Result<EdgeId, String> {
        // Validate that source is an output port and target is an input port
        let source_node = self.nodes.get(&source.node_id)
            .ok_or_else(|| format!("Source node {} not found", source.node_id))?;
        let target_node = self.nodes.get(&target.node_id)
            .ok_or_else(|| format!("Target node {} not found", target.node_id))?;

        // Check port directions
        let source_port = source_node.output_ports().iter()
            .find(|p| p.id == source)
            .ok_or_else(|| format!("Source port {} not found or not an output", source))?;
        
        let target_port = target_node.input_ports().iter()
            .find(|p| p.id == target)
            .ok_or_else(|| format!("Target port {} not found or not an input", target))?;

        // Type check
        if source_port.port_type != target_port.port_type {
            return Err(format!(
                "Type mismatch: source port has type {:?}, target port has type {:?}",
                source_port.port_type, target_port.port_type
            ));
        }

        let edge_id = EdgeId(rand::random());
        let edge = GirEdge {
            id: edge_id,
            source,
            target,
            edge_type,
            metadata: NodeMetadata::default(),
        };

        self.edges.insert(edge_id, edge);

        // Add to petgraph
        let source_pg = self.node_to_pg[&source.node_id];
        let target_pg = self.node_to_pg[&target.node_id];
        self.petgraph.add_edge(source_pg, target_pg, edge_id);

        Ok(edge_id)
    }

    /// Remove an edge
    pub fn remove_edge(&mut self, edge_id: EdgeId) -> bool {
        if let Some(edge) = self.edges.remove(&edge_id) {
            // Remove from petgraph
            let source_pg = self.node_to_pg[&edge.source.node_id];
            let target_pg = self.node_to_pg[&edge.target.node_id];
            
            // Find and remove the edge in petgraph
            if let Some(edge_idx) = self.petgraph.find_edge(source_pg, target_pg) {
                self.petgraph.remove_edge(edge_idx);
            }
            true
        } else {
            false
        }
    }

    /// Get a node by ID
    pub fn get_node(&self, node_id: NodeId) -> Option<&dyn GirNode> {
        self.nodes.get(&node_id).map(|n| n.as_ref())
    }

    /// Get a mutable node by ID
    pub fn get_node_mut(&mut self, node_id: NodeId) -> Option<&mut dyn GirNode> {
        self.nodes.get_mut(&node_id).map(|n| n.as_mut())
    }

    /// Get an edge by ID
    pub fn get_edge(&self, edge_id: EdgeId) -> Option<&GirEdge> {
        self.edges.get(&edge_id)
    }

    /// Get all edges connected to a node
    pub fn edges_for_node(&self, node_id: NodeId) -> Vec<&GirEdge> {
        self.edges.values()
            .filter(|e| e.source.node_id == node_id || e.target.node_id == node_id)
            .collect()
    }

    /// Get all outgoing edges from a node
    pub fn outgoing_edges(&self, node_id: NodeId) -> Vec<&GirEdge> {
        self.edges.values()
            .filter(|e| e.source.node_id == node_id)
            .collect()
    }

    /// Get all incoming edges to a node
    pub fn incoming_edges(&self, node_id: NodeId) -> Vec<&GirEdge> {
        self.edges.values()
            .filter(|e| e.target.node_id == node_id)
            .collect()
    }

    /// Check if adding an edge would create a cycle in data flow
    pub fn would_create_cycle(&self, source: NodeId, target: NodeId) -> bool {
        // For data flow edges, we want to prevent cycles
        // Use petgraph to check if there's already a path from target to source
        if let (Some(&source_pg), Some(&target_pg)) = 
            (self.node_to_pg.get(&source), self.node_to_pg.get(&target)) {
            petgraph::algo::has_path_connecting(&self.petgraph, target_pg, source_pg, None)
        } else {
            false
        }
    }

    /// Topological sort of nodes (for data flow)
    pub fn topological_sort(&self) -> Result<Vec<NodeId>, String> {
        use petgraph::algo::toposort;
        use petgraph::visit::IntoNodeIdentifiers;

        let sorted = toposort(&self.petgraph, None)
            .map_err(|_| "Graph contains cycles".to_string())?;

        Ok(sorted.into_iter()
            .filter_map(|idx| self.pg_to_node.get(&idx).copied())
            .collect())
    }

    /// Find all paths between two nodes
    pub fn find_paths(&self, from: NodeId, to: NodeId, max_paths: usize) -> Vec<Vec<NodeId>> {
        use petgraph::algo::all_simple_paths;
        
        let from_pg = self.node_to_pg[&from];
        let to_pg = self.node_to_pg[&to];

        let paths = all_simple_paths::<Vec<_>, _>(&self.petgraph, from_pg, to_pg, 0, None);
        
        paths.into_iter()
            .take(max_paths)
            .map(|path| {
                path.into_iter()
                    .filter_map(|idx| self.pg_to_node.get(&idx).copied())
                    .collect()
            })
            .collect()
    }

    /// Get all nodes reachable from a given node
    pub fn reachable_nodes(&self, from: NodeId) -> HashSet<NodeId> {
        use petgraph::visit::Dfs;
        
        let from_pg = self.node_to_pg[&from];
        let mut dfs = Dfs::new(&self.petgraph, from_pg);
        let mut reachable = HashSet::new();

        while let Some(idx) = dfs.next(&self.petgraph) {
            if let Some(&node_id) = self.pg_to_node.get(&idx) {
                reachable.insert(node_id);
            }
        }

        reachable
    }

    /// Get subgraph induced by a set of nodes
    pub fn induced_subgraph(&self, nodes: &HashSet<NodeId>) -> GirGraph {
        let mut subgraph = GirGraph::new(GraphId(rand::random()), format!("subgraph_of_{}", self.name));
        
        // Add nodes
        for node_id in nodes {
            if let Some(node) = self.nodes.get(node_id) {
                subgraph.add_node(node.clone_box());
            }
        }

        // Add edges where both endpoints are in the set
        for edge in self.edges.values() {
            if nodes.contains(&edge.source.node_id) && nodes.contains(&edge.target.node_id) {
                let _ = subgraph.add_edge(edge.source, edge.target, edge.edge_type);
            }
        }

        subgraph
    }

    /// Validate the entire graph
    pub fn validate(&self) -> Vec<String> {
        let mut errors = Vec::new();

        // Check all edges reference valid nodes
        for edge in self.edges.values() {
            if !self.nodes.contains_key(&edge.source.node_id) {
                errors.push(format!("Edge {:?} references missing source node {:?}", edge.id, edge.source.node_id));
            }
            if !self.nodes.contains_key(&edge.target.node_id) {
                errors.push(format!("Edge {:?} references missing target node {:?}", edge.id, edge.target.node_id));
            }
        }

        // Check for data flow cycles
        if let Err(_) = self.topological_sort() {
            errors.push("Graph contains cycles in data flow".to_string());
        }

        // Check that all required ports are connected
        for node in self.nodes.values() {
            for port in node.input_ports() {
                if port.is_required {
                    let connected = self.edges.values().any(|e| e.target == port.id);
                    if !connected {
                        errors.push(format!("Required input port {:?} on node {:?} is not connected", port.id, node.id()));
                    }
                }
            }
        }

        // Check type compatibility on all edges
        for edge in self.edges.values() {
            if let (Some(source_node), Some(target_node)) = (self.nodes.get(&edge.source.node_id), self.nodes.get(&edge.target.node_id)) {
                let source_port = source_node.output_ports().iter().find(|p| p.id == edge.source);
                let target_port = target_node.input_ports().iter().find(|p| p.id == edge.target);
                
                if let (Some(sp), Some(tp)) = (source_port, target_port) {
                    if sp.port_type != tp.port_type {
                        errors.push(format!("Type mismatch on edge {:?}: {:?} != {:?}", edge.id, sp.port_type, tp.port_type));
                    }
                }
            }
        }

        errors
    }

    /// Get graph statistics
    pub fn stats(&self) -> GraphStats {
        GraphStats {
            node_count: self.nodes.len(),
            edge_count: self.edges.len(),
            entry_points: self.entry_points.len(),
            node_types: self.nodes.values().map(|n| n.node_type()).collect(),
        }
    }
}

/// Statistics about a graph
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphStats {
    pub node_count: usize,
    pub edge_count: usize,
    pub entry_points: usize,
    pub node_types: HashMap<NodeType, usize>,
}

/// Edge validation result
#[derive(Debug, Clone)]
pub struct EdgeValidationResult {
    pub is_valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

impl EdgeValidationResult {
    pub fn valid() -> Self {
        EdgeValidationResult {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    pub fn invalid(errors: Vec<String>) -> Self {
        EdgeValidationResult {
            is_valid: false,
            errors,
            warnings: Vec::new(),
        }
    }

    pub fn add_error(&mut self, error: String) {
        self.is_valid = false;
        self.errors.push(error);
    }

    pub fn add_warning(&mut self, warning: String) {
        self.warnings.push(warning);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gir::*;
    use crate::gir::nodes::*;

    #[test]
    fn test_graph_creation() {
        let mut graph = GirGraph::new(GraphId(1), "test".to_string());
        
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let node_id = node.id();
        graph.add_node(node);
        
        assert_eq!(graph.nodes.len(), 1);
        assert!(graph.nodes.contains_key(&node_id));
    }

    #[test]
    fn test_edge_creation() {
        let mut graph = GirGraph::new(GraphId(1), "test".to_string());
        
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node1 = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let node1_id = node1.id();
        graph.add_node(node1);

        let node2 = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let node2_id = node2.id();
        graph.add_node(node2);

        let source_port = node1.output_ports()[0].id;
        let target_port = node2.input_ports().first().map(|p| p.id).unwrap_or_else(|| {
            // Add an input port for testing
            Port {
                id: PortId { node_id: node2_id, index: 0, direction: PortDirection::Input },
                name: "test".to_string(),
                port_type: type_id,
                direction: PortDirection::Input,
                is_required: true,
                default_value: None,
            }
        });

        let result = graph.add_edge(source_port, target_port, EdgeType::Data);
        assert!(result.is_ok());
    }

    #[test]
    fn test_cycle_detection() {
        let mut graph = GirGraph::new(GraphId(1), "test".to_string());
        
        let mut ctx = GirContext::new();
        let type_id = TypeId(1);
        
        let node1 = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let node1_id = node1.id();
        graph.add_node(node1);

        let node2 = create_value_node(&mut ctx, ValueKind::Literal, type_id);
        let node2_id = node2.id();
        graph.add_node(node2);

        let source_port = PortId { node_id: node1_id, index: 0, direction: PortDirection::Output };
        let target_port = PortId { node_id: node2_id, index: 0, direction: PortDirection::Input };
        
        // Add edge from node1 to node2
        graph.add_edge(source_port, target_port, EdgeType::Data).unwrap();
        
        // Try to add edge from node2 to node1 - should create cycle
        let back_source = PortId { node_id: node2_id, index: 0, direction: PortDirection::Output };
        let back_target = PortId { node_id: node1_id, index: 0, direction: PortDirection::Input };
        
        // Need to add output port to node2 and input to node1 for this test
        // For now just test would_create_cycle
        assert!(graph.would_create_cycle(node2_id, node1_id));
    }
}