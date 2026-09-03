//! OREO Visual Editor - Canvas, Nodes, Edges
//!
//! Visual-first editor for the Graph Intermediate Representation.
//! Implements the canvas, node rendering, edge connections, and interaction.

use super::*;
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};

/// Visual editor state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisualEditor {
    pub canvas: Canvas,
    pub nodes: HashMap<NodeId, VisualNode>,
    pub edges: HashMap<EdgeId, VisualEdge>,
    pub selection: Selection,
    pub viewport: Viewport,
    pub tool: EditorTool,
    pub grid: Grid,
    pub layers: Vec<Layer>,
    pub history: History,
    pub clipboard: Clipboard,
}

/// Canvas for the visual editor
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Canvas {
    pub size: (f32, f32),
    pub background_color: [f32; 4],
    pub grid_color: [f32; 4],
    pub grid_size: f32,
    pub snap_to_grid: bool,
}

impl Default for Canvas {
    fn default() -> Self {
        Canvas {
            size: (1920.0, 1080.0),
            background_color: [0.1, 0.1, 0.12, 1.0],
            grid_color: [0.3, 0.3, 0.35, 0.5],
            grid_size: 20.0,
            snap_to_grid: true,
        }
    }
}

/// Viewport for panning and zooming
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Viewport {
    pub offset: (f32, f32),
    pub zoom: f32,
    pub min_zoom: f32,
    pub max_zoom: f32,
}

impl Default for Viewport {
    fn default() -> Self {
        Viewport {
            offset: (0.0, 0.0),
            zoom: 1.0,
            min_zoom: 0.1,
            max_zoom: 5.0,
        }
    }
}

impl Viewport {
    pub fn world_to_screen(&self, world: (f32, f32)) -> (f32, f32) {
        (
            (world.0 - self.offset.0) * self.zoom,
            (world.1 - self.offset.1) * self.zoom,
        )
    }

    pub fn screen_to_world(&self, screen: (f32, f32)) -> (f32, f32) {
        (
            screen.0 / self.zoom + self.offset.0,
            screen.1 / self.zoom + self.offset.1,
        )
    }

    pub fn zoom_at(&mut self, screen_pos: (f32, f32), factor: f32) {
        let world_before = self.screen_to_world(screen_pos);
        self.zoom = (self.zoom * factor).clamp(self.min_zoom, self.max_zoom);
        let world_after = self.screen_to_world(screen_pos);
        self.offset.0 += world_after.0 - world_before.0;
        self.offset.1 += world_after.1 - world_before.1;
    }

    pub fn pan(&mut self, delta: (f32, f32)) {
        self.offset.0 -= delta.0 / self.zoom;
        self.offset.1 -= delta.1 / self.zoom;
    }
}

/// Visual node on the canvas
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisualNode {
    pub id: NodeId,
    pub gir_node_id: NodeId,
    pub position: (f32, f32),
    pub size: (f32, f32),
    pub node_type: NodeType,
    pub kind: u8,
    pub title: String,
    pub input_ports: Vec<VisualPort>,
    pub output_ports: Vec<VisualPort>,
    pub style: NodeStyle,
    pub state: NodeState,
    pub metadata: NodeMetadata,
}

/// Visual port on a node
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisualPort {
    pub id: PortId,
    pub name: String,
    pub port_type: TypeId,
    pub direction: PortDirection,
    pub position: (f32, f32), // Relative to node center
    pub is_connected: bool,
    pub connected_edges: Vec<EdgeId>,
}

/// Node visual style
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeStyle {
    pub shape: NodeShape,
    pub fill_color: [f32; 4],
    pub border_color: [f32; 4],
    pub border_width: f32,
    pub text_color: [f32; 4],
    pub font_size: f32,
    pub corner_radius: f32,
    pub port_radius: f32,
    pub shadow: bool,
}

impl Default for NodeStyle {
    fn default() -> Self {
        NodeStyle {
            shape: NodeShape::Rectangle,
            fill_color: [0.2, 0.25, 0.3, 1.0],
            border_color: [0.5, 0.55, 0.6, 1.0],
            border_width: 2.0,
            text_color: [0.9, 0.9, 0.95, 1.0],
            font_size: 14.0,
            corner_radius: 8.0,
            port_radius: 8.0,
            shadow: true,
        }
    }
}

/// Node shape
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum NodeShape {
    Rectangle,
    RoundedRectangle,
    Circle,
    Diamond,
    Hexagon,
    Custom(String),
}

/// Node state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum NodeState {
    Normal,
    Selected,
    Hovered,
    Dragging,
    Executing,
    Error,
    Warning,
    Disabled,
}

/// Visual edge
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisualEdge {
    pub id: EdgeId,
    pub gir_edge_id: EdgeId,
    pub source: PortId,
    pub target: PortId,
    pub control_points: Vec<(f32, f32)>, // Bezier control points
    pub style: EdgeStyle,
    pub state: EdgeState,
    pub label: Option<String>,
}

/// Edge visual style
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeStyle {
    pub color: [f32; 4],
    pub width: f32,
    pub style: EdgeLineStyle,
    pub arrow_size: f32,
    pub show_flow: bool,
    pub flow_speed: f32,
}

impl Default for EdgeStyle {
    fn default() -> Self {
        EdgeStyle {
            color: [0.6, 0.65, 0.7, 1.0],
            width: 2.0,
            style: EdgeLineStyle::Solid,
            arrow_size: 12.0,
            show_flow: false,
            flow_speed: 1.0,
        }
    }
}

/// Edge line style
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EdgeLineStyle {
    Solid,
    Dashed,
    Dotted,
    Double,
}

/// Edge state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EdgeState {
    Normal,
    Selected,
    Hovered,
    Highlighted,
    Flowing,
    Error,
}

/// Selection state
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Selection {
    pub nodes: HashSet<NodeId>,
    pub edges: HashSet<EdgeId>,
    pub anchor: Option<NodeId>, // For multi-select
    pub marquee: Option<Marquee>,
}

/// Marquee selection rectangle
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Marquee {
    pub start: (f32, f32),
    pub end: (f32, f32),
}

/// Grid settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Grid {
    pub size: f32,
    pub color: [f32; 4],
    pub visible: bool,
    pub snap: bool,
    pub subdivisions: u32,
}

impl Default for Grid {
    fn default() -> Self {
        Grid {
            size: 20.0,
            color: [0.3, 0.3, 0.35, 0.5],
            visible: true,
            snap: true,
            subdivisions: 5,
        }
    }
}

/// Layer for organizing nodes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Layer {
    pub id: u32,
    pub name: String,
    pub visible: bool,
    pub locked: bool,
    pub opacity: f32,
    pub nodes: HashSet<NodeId>,
}

/// Editor tool
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EditorTool {
    Select,
    Pan,
    CreateNode,
    CreateEdge,
    Delete,
    Marquee,
    Text,
    Measure,
}

/// History for undo/redo
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct History {
    pub past: Vec<HistoryAction>,
    pub future: Vec<HistoryAction>,
    pub max_size: usize,
}

impl History {
    pub fn new(max_size: usize) -> Self {
        History {
            past: Vec::new(),
            future: Vec::new(),
            max_size,
        }
    }

    pub fn push(&mut self, action: HistoryAction) {
        self.past.push(action);
        if self.past.len() > self.max_size {
            self.past.remove(0);
        }
        self.future.clear();
    }

    pub fn undo(&mut self) -> Option<HistoryAction> {
        self.past.pop().map(|action| {
            self.future.push(action.clone());
            action
        })
    }

    pub fn redo(&mut self) -> Option<HistoryAction> {
        self.future.pop().map(|action| {
            self.past.push(action.clone());
            action
        })
    }

    pub fn can_undo(&self) -> bool {
        !self.past.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.future.is_empty()
    }
}

/// History action
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HistoryAction {
    AddNode { node: VisualNode },
    RemoveNode { node_id: NodeId, node: VisualNode },
    MoveNode { node_id: NodeId, from: (f32, f32), to: (f32, f32) },
    AddEdge { edge: VisualEdge },
    RemoveEdge { edge_id: EdgeId, edge: VisualEdge },
    MoveEdge { edge_id: EdgeId, from_source: PortId, from_target: PortId, to_source: PortId, to_target: PortId },
    ChangeNodeStyle { node_id: NodeId, from: NodeStyle, to: NodeStyle },
    ChangeEdgeStyle { edge_id: EdgeId, from: EdgeStyle, to: EdgeStyle },
    MultiAction { actions: Vec<HistoryAction> },
}

/// Clipboard for copy/paste
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Clipboard {
    pub nodes: Vec<VisualNode>,
    pub edges: Vec<VisualEdge>,
    pub offset: (f32, f32),
}

/// Port direction for layout
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PortSide {
    Top,
    Bottom,
    Left,
    Right,
    Auto,
}

/// Node layout algorithm
pub mod layout {
    use super::*;
    use std::collections::VecDeque;

    /// Force-directed layout
    pub fn force_directed(nodes: &mut HashMap<NodeId, VisualNode>, edges: &HashMap<EdgeId, VisualEdge>, iterations: usize) {
        let mut positions: HashMap<NodeId, (f32, f32)> = nodes.iter()
            .map(|(id, node)| (*id, node.position))
            .collect();

        let k = 50.0; // Spring constant
        let repulsion = 1000.0;
        let damping = 0.9;

        for _ in 0..iterations {
            let mut forces: HashMap<NodeId, (f32, f32)> = HashMap::new();

            // Repulsion between all nodes
            let node_ids: Vec<NodeId> = nodes.keys().copied().collect();
            for i in 0..node_ids.len() {
                for j in i+1..node_ids.len() {
                    let id1 = node_ids[i];
                    let id2 = node_ids[j];
                    let pos1 = positions[&id1];
                    let pos2 = positions[&j];
                    
                    let dx = pos1.0 - pos2.0;
                    let dy = pos1.1 - pos2.1;
                    let dist = (dx*dx + dy*dy).sqrt().max(1.0);
                    
                    let force = repulsion / (dist * dist);
                    let fx = force * dx / dist;
                    let fy = force * dy / dist;
                    
                    *forces.entry(id1).or_insert((0.0, 0.0)) = (
                        forces.get(&id1).map(|f| f.0).unwrap_or(0.0) + fx,
                        forces.get(&id1).map(|f| f.1).unwrap_or(0.0) + fy,
                    );
                    *forces.entry(id2).or_insert((0.0, 0.0)) = (
                        forces.get(&id2).map(|f| f.0).unwrap_or(0.0) - fx,
                        forces.get(&id2).map(|f| f.1).unwrap_or(0.0) - fy,
                    );
                }
            }

            // Attraction along edges
            for edge in edges.values() {
                if let (Some(&pos1), Some(&pos2)) = (positions.get(&edge.source.node_id), positions.get(&edge.target.node_id)) {
                    let dx = pos2.0 - pos1.0;
                    let dy = pos2.1 - pos1.1;
                    let dist = (dx*dx + dy*dy).sqrt().max(1.0);
                    
                    let force = (dist - 100.0) * 0.01;
                    let fx = force * dx / dist;
                    let fy = force * dy / dist;
                    
                    *forces.entry(edge.source.node_id).or_insert((0.0, 0.0)) = (
                        forces.get(&edge.source.node_id).map(|f| f.0).unwrap_or(0.0) + fx,
                        forces.get(&edge.source.node_id).map(|f| f.1).unwrap_or(0.0) + fy,
                    );
                    *forces.entry(edge.target.node_id).or_insert((0.0, 0.0)) = (
                        forces.get(&edge.target.node_id).map(|f| f.0).unwrap_or(0.0) - fx,
                        forces.get(&edge.target.node_id).map(|f| f.1).unwrap_or(0.0) - fy,
                    );
                }
            }

            // Apply forces
            for (id, (fx, fy)) in forces {
                if let Some(pos) = positions.get_mut(&id) {
                    pos.0 += fx * damping;
                    pos.1 += fy * damping;
                }
            }
        }

        // Update node positions
        for (id, pos) in positions {
            if let Some(node) = nodes.get_mut(&id) {
                node.position = pos;
            }
        }
    }

    /// Hierarchical layout for data flow graphs
    pub fn hierarchical(nodes: &mut HashMap<NodeId, VisualNode>, edges: &HashMap<EdgeId, VisualEdge>) {
        // Build adjacency
        let mut adj: HashMap<NodeId, Vec<NodeId>> = HashMap::new();
        let mut reverse_adj: HashMap<NodeId, Vec<NodeId>> = HashMap::new();
        let mut in_degree: HashMap<NodeId, usize> = HashMap::new();

        for node_id in nodes.keys() {
            in_degree.insert(*node_id, 0);
        }

        for edge in edges.values() {
            adj.entry(edge.source.node_id).or_default().push(edge.target.node_id);
            reverse_adj.entry(edge.target.node_id).or_default().push(edge.source.node_id);
            *in_degree.entry(edge.target.node_id).or_insert(0) += 1;
        }

        // Topological sort
        let mut queue = VecDeque::new();
        for (id, &deg) in &in_degree {
            if deg == 0 {
                queue.push_back(*id);
            }
        }

        let mut layers: Vec<Vec<NodeId>> = Vec::new();
        while !queue.is_empty() {
            let mut next_layer = Vec::new();
            for _ in 0..queue.len() {
                let id = queue.pop_front().unwrap();
                next_layer.push(id);
                for &next_id in adj.get(&id).unwrap_or(&Vec::new()) {
                    *in_degree.get_mut(&next_id).unwrap() -= 1;
                    if in_degree[&next_id] == 0 {
                        queue.push_back(next_id);
                    }
                }
            }
            if !next_layer.is_empty() {
                layers.push(next_layer);
            }
        }

        // Position nodes by layer
        let layer_spacing = 200.0;
        let node_spacing = 150.0;

        for (layer_idx, layer) in layers.iter().enumerate() {
            let x = layer_idx as f32 * layer_spacing + 100.0;
            let total_width = (layer.len() - 1) as f32 * node_spacing;
            let start_x = x - total_width / 2.0;

            for (node_idx, &id) in layer.iter().enumerate() {
                let y = start_x + node_idx as f32 * node_spacing;
                if let Some(node) = nodes.get_mut(&id) {
                    node.position = (x, y);
                }
            }
        }
    }

    /// Grid layout
    pub fn grid(nodes: &mut HashMap<NodeId, VisualNode>, cols: usize, spacing: f32) {
        let mut nodes_vec: Vec<_> = nodes.values_mut().collect();
        for (i, node) in nodes_vec.iter_mut().enumerate() {
            let col = i % cols;
            let row = i / cols;
            node.position = (
                (col as f32) * spacing + 100.0,
                (row as f32) * spacing + 100.0,
            );
        }
    }

    /// Circular layout
    pub fn circular(nodes: &mut HashMap<NodeId, VisualNode>, center: (f32, f32), radius: f32) {
        let node_ids: Vec<NodeId> = nodes.keys().copied().collect();
        let count = node_ids.len() as f32;
        
        for (i, &id) in node_ids.iter().enumerate() {
            let angle = (i as f32 / count) * 2.0 * std::f32::consts::PI;
            if let Some(node) = nodes.get_mut(&id) {
                node.position = (
                    center.0 + radius * angle.cos(),
                    center.1 + radius * angle.sin(),
                );
            }
        }
    }
}

/// Auto-layout triggers
pub fn auto_layout(editor: &mut VisualEditor, algorithm: LayoutAlgorithm) {
    match algorithm {
        LayoutAlgorithm::ForceDirected => {
            layout::force_directed(&mut editor.nodes, &editor.edges, 100);
        }
        LayoutAlgorithm::Hierarchical => {
            layout::hierarchical(&mut editor.nodes, &editor.edges);
        }
        LayoutAlgorithm::Grid => {
            layout::grid(&mut editor.nodes, 4, 200.0);
        }
        LayoutAlgorithm::Circular => {
            layout::circular(&mut editor.nodes, (960.0, 540.0), 300.0);
        }
    }
    
    // Record in history
    editor.history.push(HistoryAction::MultiAction { actions: vec![] });
}

/// Layout algorithms
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum LayoutAlgorithm {
    ForceDirected,
    Hierarchical,
    Grid,
    Circular,
}

/// Port layout helpers
pub fn calculate_port_positions(node: &VisualNode) -> Vec<(PortId, (f32, f32))> {
    let mut positions = Vec::new();
    let (w, h) = node.size;
    
    // Input ports on left, output on right
    let input_count = node.input_ports.len() as f32;
    let output_count = node.output_ports.len() as f32;
    
    for (i, port) in node.input_ports.iter().enumerate() {
        let y = if input_count <= 1.0 {
            h / 2.0
        } else {
            (i as f32 + 0.5) * h / input_count
        };
        positions.push((port.id, (0.0, y - h/2.0)));
    }
    
    for (i, port) in node.output_ports.iter().enumerate() {
        let y = if output_count <= 1.0 {
            h / 2.0
        } else {
            (i as f32 + 0.5) * h / output_count
        };
        positions.push((port.id, (w, y - h/2.0)));
    }
    
    positions
}

/// Edge path calculation (Bezier curves)
pub fn calculate_edge_path(
    source_pos: (f32, f32),
    source_port_pos: (f32, f32),
    target_pos: (f32, f32),
    target_port_pos: (f32, f32),
) -> Vec<(f32, f32)> {
    let source_abs = (source_pos.0 + source_port_pos.0, source_pos.1 + source_port_pos.1);
    let target_abs = (target_pos.0 + target_port_pos.0, target_pos.1 + target_port_pos.1);
    
    let dx = target_abs.0 - source_abs.0;
    let dy = target_abs.1 - source_abs.1;
    let dist = (dx*dx + dy*dy).sqrt();
    
    // Control point offset based on distance
    let offset = (dist * 0.3).clamp(50.0, 200.0);
    
    // Determine curve direction based on port positions
    let cp1 = (
        source_abs.0 + offset * (target_abs.0 - source_abs.0).signum(),
        source_abs.1,
    );
    let cp2 = (
        target_abs.0 - offset * (target_abs.0 - source_abs.0).signum(),
        target_abs.1,
    );
    
    vec![source_abs, cp1, cp2, target_abs]
}

/// Hit testing
pub fn hit_test_node(node: &VisualNode, world_pos: (f32, f32)) -> bool {
    let half_w = node.size.0 / 2.0;
    let half_h = node.size.1 / 2.0;
    
    world_pos.0 >= node.position.0 - half_w &&
    world_pos.0 <= node.position.0 + half_w &&
    world_pos.1 >= node.position.1 - half_h &&
    world_pos.1 <= node.position.1 + half_h
}

pub fn hit_test_port(node: &VisualNode, world_pos: (f32, f32), port_radius: f32) -> Option<PortId> {
    for port in &node.input_ports {
        let port_abs = (
            node.position.0 + port.position.0,
            node.position.1 + port.position.1,
        );
        let dx = world_pos.0 - port_abs.0;
        let dy = world_pos.1 - port_abs.1;
        if dx*dx + dy*dy <= port_radius * port_radius {
            return Some(port.id);
        }
    }
    
    for port in &node.output_ports {
        let port_abs = (
            node.position.0 + port.position.0,
            node.position.1 + port.position.1,
        );
        let dx = world_pos.0 - port_abs.0;
        let dy = world_pos.1 - port_abs.1;
        if dx*dx + dy*dy <= port_radius * port_radius {
            return Some(port.id);
        }
    }
    
    None
}

pub fn hit_test_edge(edge: &VisualEdge, world_pos: (f32, f32), threshold: f32) -> bool {
    let points = &edge.control_points;
    if points.len() < 2 { return false; }
    
    // Check distance to line segments
    for i in 0..points.len()-1 {
        let p1 = points[i];
        let p2 = points[i+1];
        
        // Distance from point to line segment
        let dx = p2.0 - p1.0;
        let dy = p2.1 - p1.1;
        let len_sq = dx*dx + dy*dy;
        
        if len_sq == 0.0 {
            let dx = world_pos.0 - p1.0;
            let dy = world_pos.1 - p1.1;
            if dx*dx + dy*dy <= threshold * threshold {
                return true;
            }
            continue;
        }
        
        let t = ((world_pos.0 - p1.0) * dx + (world_pos.1 - p1.1) * dy) / len_sq;
        let t = t.clamp(0.0, 1.0);
        
        let closest_x = p1.0 + t * dx;
        let closest_y = p1.1 + t * dy;
        
        let dx = world_pos.0 - closest_x;
        let dy = world_pos.1 - closest_y;
        if dx*dx + dy*dy <= threshold * threshold {
            return true;
        }
    }
    
    false
}

/// Connection validation
pub fn can_connect(
    source_node: &VisualNode,
    source_port: &VisualPort,
    target_node: &VisualNode,
    target_port: &VisualPort,
) -> Result<(), String> {
    // Can't connect to self
    if source_node.id == target_node.id {
        return Err("Cannot connect node to itself".to_string());
    }
    
    // Source must be output, target must be input
    if source_port.direction != PortDirection::Output {
        return Err("Source port must be an output".to_string());
    }
    if target_port.direction != PortDirection::Input {
        return Err("Target port must be an input".to_string());
    }
    
    // Check type compatibility
    if source_port.port_type != target_port.port_type {
        return Err(format!(
            "Type mismatch: {} != {}",
            source_port.port_type, target_port.port_type
        ));
    }
    
    // Check if target port already has a connection (if not multi-input)
    if target_port.is_connected && target_port.connected_edges.len() > 0 {
        // Check if multi-input is allowed (would need metadata)
        // For now, allow multiple connections
    }
    
    // Check for cycles (would create a cycle in data flow)
    // This is a simplified check - real implementation would do full cycle detection
    
    Ok(())
}

/// Node factory for common node types
pub mod node_factory {
    use super::*;
    
    pub fn create_value_node(
        editor: &mut VisualEditor,
        gir_node_id: NodeId,
        kind: ValueKind,
        value_type: TypeId,
        position: (f32, f32),
    ) -> NodeId {
        let node_id = NodeId(rand::random());
        let node = VisualNode {
            id: node_id,
            gir_node_id,
            position,
            size: (180.0, 100.0),
            node_type: NodeType::Value,
            kind: kind as u8,
            title: format!("{:?}", kind),
            input_ports: vec![],
            output_ports: vec![VisualPort {
                id: PortId { node_id, index: 0, direction: PortDirection::Output },
                name: "value".to_string(),
                port_type: value_type,
                direction: PortDirection::Output,
                position: (90.0, 0.0),
                is_connected: false,
                connected_edges: vec![],
            }],
            style: NodeStyle {
                shape: NodeShape::Rectangle,
                fill_color: [0.25, 0.3, 0.35, 1.0],
                border_color: [0.5, 0.6, 0.65, 1.0],
                ..NodeStyle::default()
            },
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        editor.nodes.insert(node_id, node);
        node_id
    }
    
    pub fn create_op_node(
        editor: &mut VisualEditor,
        gir_node_id: NodeId,
        op: OpKind,
        input_types: Vec<TypeId>,
        output_type: TypeId,
        position: (f32, f32),
    ) -> NodeId {
        let node_id = NodeId(rand::random());
        let mut input_ports = Vec::new();
        for (i, ty) in input_types.iter().enumerate() {
            input_ports.push(VisualPort {
                id: PortId { node_id, index: i as u32, direction: PortDirection::Input },
                name: format!("arg{}", i),
                port_type: *ty,
                direction: PortDirection::Input,
                position: (0.0, 0.0), // Will be calculated
                is_connected: false,
                connected_edges: vec![],
            });
        }
        
        let output_port = VisualPort {
            id: PortId { node_id, index: input_types.len() as u32, direction: PortDirection::Output },
            name: "result".to_string(),
            port_type: output_type,
            direction: PortDirection::Output,
            position: (0.0, 0.0),
            is_connected: false,
            connected_edges: vec![],
        };
        
        let node = VisualNode {
            id: node_id,
            gir_node_id,
            position,
            size: (200.0, 120.0),
            node_type: NodeType::Op,
            kind: op as u8,
            title: format!("{:?}", op),
            input_ports,
            output_ports: vec![output_port],
            style: NodeStyle {
                shape: NodeShape::RoundedRectangle,
                fill_color: [0.3, 0.25, 0.35, 1.0],
                border_color: [0.6, 0.5, 0.65, 1.0],
                ..NodeStyle::default()
            },
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        editor.nodes.insert(node_id, node);
        node_id
    }
    
    pub fn create_control_node(
        editor: &mut VisualEditor,
        gir_node_id: NodeId,
        kind: ControlKind,
        input_types: Vec<TypeId>,
        output_types: Vec<TypeId>,
        position: (f32, f32),
    ) -> NodeId {
        let node_id = NodeId(rand::random());
        let mut input_ports = Vec::new();
        for (i, ty) in input_types.iter().enumerate() {
            input_ports.push(VisualPort {
                id: PortId { node_id, index: i as u32, direction: PortDirection::Input },
                name: format!("in{}", i),
                port_type: *ty,
                direction: PortDirection::Input,
                position: (0.0, 0.0),
                is_connected: false,
                connected_edges: vec![],
            });
        }
        
        let mut output_ports = Vec::new();
        for (i, ty) in output_types.iter().enumerate() {
            output_ports.push(VisualPort {
                id: PortId { node_id, index: (i + 100) as u32, direction: PortDirection::Output },
                name: format!("out{}", i),
                port_type: *ty,
                direction: PortDirection::Output,
                position: (0.0, 0.0),
                is_connected: false,
                connected_edges: vec![],
            });
        }
        
        let node = VisualNode {
            id: node_id,
            gir_node_id,
            position,
            size: (220.0, 140.0),
            node_type: NodeType::Control,
            kind: kind as u8,
            title: format!("{:?}", kind),
            input_ports,
            output_ports,
            style: NodeStyle {
                shape: NodeShape::Diamond,
                fill_color: [0.35, 0.3, 0.25, 1.0],
                border_color: [0.65, 0.55, 0.5, 1.0],
                ..NodeStyle::default()
            },
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        editor.nodes.insert(node_id, node);
        node_id
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_visual_node_creation() {
        let mut editor = VisualEditor {
            canvas: Canvas::default(),
            nodes: HashMap::new(),
            edges: HashMap::new(),
            selection: Selection::default(),
            viewport: Viewport::default(),
            tool: EditorTool::Select,
            grid: Grid::default(),
            layers: vec![],
            history: History::new(100),
            clipboard: Clipboard::default(),
        };
        
        let node_id = node_factory::create_value_node(
            &mut editor,
            NodeId(1),
            ValueKind::Literal,
            TypeId(1),
            (100.0, 100.0),
        );
        
        assert!(editor.nodes.contains_key(&node_id));
        let node = &editor.nodes[&node_id];
        assert_eq!(node.node_type, NodeType::Value);
        assert_eq!(node.output_ports.len(), 1);
    }
    
    #[test]
    fn test_viewport_transform() {
        let mut viewport = Viewport::default();
        viewport.offset = (100.0, 100.0);
        viewport.zoom = 2.0;
        
        let world = (200.0, 200.0);
        let screen = viewport.world_to_screen(world);
        assert_eq!(screen, (200.0, 200.0)); // (200-100)*2 = 200
        
        let back = viewport.screen_to_world(screen);
        assert_eq!(back, world);
    }
    
    #[test]
    fn test_viewport_zoom_at() {
        let mut viewport = Viewport::default();
        viewport.offset = (0.0, 0.0);
        viewport.zoom = 1.0;
        
        viewport.zoom_at((400.0, 300.0), 2.0);
        assert_eq!(viewport.zoom, 2.0);
        // Zoom at center should adjust offset
    }
    
    #[test]
    fn test_hit_test_node() {
        let node = VisualNode {
            id: NodeId(1),
            gir_node_id: NodeId(1),
            position: (100.0, 100.0),
            size: (100.0, 50.0),
            node_type: NodeType::Value,
            kind: 0,
            title: "Test".to_string(),
            input_ports: vec![],
            output_ports: vec![],
            style: NodeStyle::default(),
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        
        assert!(hit_test_node(&node, (100.0, 100.0))); // Center
        assert!(hit_test_node(&node, (50.0, 75.0)));   // Top-left
        assert!(hit_test_node(&node, (150.0, 125.0))); // Bottom-right
        assert!(!hit_test_node(&node, (0.0, 0.0)));    // Outside
        assert!(!hit_test_node(&node, (200.0, 200.0))); // Outside
    }
    
    #[test]
    fn test_edge_path_calculation() {
        let path = calculate_edge_path(
            (100.0, 100.0), (50.0, 0.0),  // Source node + port
            (300.0, 200.0), (0.0, 50.0),   // Target node + port
        );
        
        assert_eq!(path.len(), 4);
        assert_eq!(path[0], (150.0, 100.0));  // Source port absolute
        assert_eq!(path[3], (300.0, 250.0));  // Target port absolute
    }
    
    #[test]
    fn test_can_connect() {
        let mut source_node = VisualNode {
            id: NodeId(1),
            gir_node_id: NodeId(1),
            position: (0.0, 0.0),
            size: (100.0, 50.0),
            node_type: NodeType::Value,
            kind: 0,
            title: "Source".to_string(),
            input_ports: vec![],
            output_ports: vec![VisualPort {
                id: PortId { node_id: NodeId(1), index: 0, direction: PortDirection::Output },
                name: "out".to_string(),
                port_type: TypeId(1),
                direction: PortDirection::Output,
                position: (50.0, 0.0),
                is_connected: false,
                connected_edges: vec![],
            }],
            style: NodeStyle::default(),
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        
        let mut target_node = VisualNode {
            id: NodeId(2),
            gir_node_id: NodeId(2),
            position: (200.0, 0.0),
            size: (100.0, 50.0),
            node_type: NodeType::Op,
            kind: 0,
            title: "Target".to_string(),
            input_ports: vec![VisualPort {
                id: PortId { node_id: NodeId(2), index: 0, direction: PortDirection::Input },
                name: "in".to_string(),
                port_type: TypeId(1),
                direction: PortDirection::Input,
                position: (0.0, 25.0),
                is_connected: false,
                connected_edges: vec![],
            }],
            output_ports: vec![],
            style: NodeStyle::default(),
            state: NodeState::Normal,
            metadata: NodeMetadata::default(),
        };
        
        let source_port = source_node.output_ports[0].clone();
        let target_port = target_node.input_ports[0].clone();
        
        assert!(can_connect(&source_node, &source_port, &target_node, &target_port).is_ok());
        
        // Test self-connection prevention
        assert!(can_connect(&source_node, &source_port, &source_node, &source_port).is_err());
        
        // Test type mismatch
        let mut bad_target = target_node.clone();
        bad_target.input_ports[0].port_type = TypeId(999);
        assert!(can_connect(&source_node, &source_port, &bad_target, &bad_target.input_ports[0]).is_err());
    }
    
    #[test]
    fn test_layout_algorithms() {
        let mut nodes = HashMap::new();
        let mut edges = HashMap::new();
        
        // Create test graph
        for i in 0..5 {
            let id = NodeId(i);
            nodes.insert(id, VisualNode {
                id,
                gir_node_id: id,
                position: (0.0, 0.0),
                size: (100.0, 50.0),
                node_type: NodeType::Value,
                kind: 0,
                title: format!("Node {}", i),
                input_ports: vec![],
                output_ports: vec![VisualPort {
                    id: PortId { node_id: id, index: 0, direction: PortDirection::Output },
                    name: "out".to_string(),
                    port_type: TypeId(1),
                    direction: PortDirection::Output,
                    position: (50.0, 0.0),
                    is_connected: false,
                    connected_edges: vec![],
                }],
                style: NodeStyle::default(),
                state: NodeState::Normal,
                metadata: NodeMetadata::default(),
            });
        }
        
        // Chain them
        for i in 0..4 {
            let edge_id = EdgeId(i as u64);
            edges.insert(edge_id, VisualEdge {
                id: edge_id,
                gir_edge_id: edge_id,
                source: PortId { node_id: NodeId(i), index: 0, direction: PortDirection::Output },
                target: PortId { node_id: NodeId(i+1), index: 0, direction: PortDirection::Input },
                control_points: vec![],
                style: EdgeStyle::default(),
                state: EdgeState::Normal,
                label: None,
            });
        }
        
        // Test hierarchical layout
        layout::hierarchical(&mut nodes, &edges);
        
        // Check that nodes are positioned in layers
        let pos0 = nodes[&NodeId(0)].position;
        let pos4 = nodes[&NodeId(4)].position;
        assert!(pos4.0 > pos0.0); // Layer 4 should be to the right of layer 0
    }
}