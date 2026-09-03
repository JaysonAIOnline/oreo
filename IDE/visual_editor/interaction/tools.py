"""
Visual Editor - Interaction Tools
User interaction handling for the node-graph editor.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple, Set
import math

from parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind, Port, TypeRef,
    connect_data, connect_control, connect_composition,
)
from ..nodes.node_registry import get_node_registry, NodeTemplate


class ToolMode(Enum):
    """Editor tool modes."""
    SELECT = "select"
    PAN = "pan"
    CREATE_NODE = "create_node"
    CONNECT = "connect"
    DELETE = "delete"
    INSPECT = "inspect"
    NL_INPUT = "nl_input"


class InteractionEventType(Enum):
    """Types of interaction events."""
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOUSE_MOVE = "mouse_move"
    MOUSE_WHEEL = "mouse_wheel"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    DOUBLE_CLICK = "double_click"
    CONTEXT_MENU = "context_menu"


@dataclass
class InteractionEvent:
    """User interaction event."""
    type: InteractionEventType
    screen_x: float
    screen_y: float
    world_x: float = 0
    world_y: float = 0
    button: int = 0  # 0=left, 1=middle, 2=right
    modifiers: Set[str] = field(default_factory=set)  # shift, ctrl, alt, meta
    key: str = ""
    timestamp: float = 0
    handled: bool = False


@dataclass
class InteractionState:
    """Current interaction state."""
    mode: ToolMode = ToolMode.SELECT
    selected_nodes: Set[str] = field(default_factory=set)
    selected_edges: Set[str] = field(default_factory=set)
    hovered_node: Optional[str] = None
    hovered_edge: Optional[str] = None
    hovered_port: Optional[Tuple[str, str]] = None  # (node_id, port_name)
    
    # Drag state
    dragging: bool = False
    drag_start_screen: Tuple[float, float] = (0, 0)
    drag_start_world: Tuple[float, float] = (0, 0)
    drag_nodes: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # node_id -> (orig_x, orig_y)
    drag_offset: Tuple[float, float] = (0, 0)
    
    # Connection state
    connecting: bool = False
    connect_from: Optional[Tuple[str, str]] = None  # (node_id, port_name)
    connect_preview: Optional[Tuple[float, float]] = None  # current mouse pos
    
    # Box selection
    box_selecting: bool = False
    box_start: Tuple[float, float] = (0, 0)
    box_end: Tuple[float, float] = (0, 0)
    
    # Create node
    pending_node_template: Optional[NodeTemplate] = None
    pending_node_position: Tuple[float, float] = (0, 0)
    
    # NL Input
    nl_input_active: bool = False
    nl_input_text: str = ""
    nl_input_position: Tuple[float, float] = (0, 0)
    
    # Clipboard
    clipboard: List[Dict[str, Any]] = field(default_factory=list)


class InteractionHandler:
    """Handles user interactions for the visual editor."""
    
    def __init__(self, graph: Graph, canvas_renderer):
        self.graph = graph
        self.renderer = canvas_renderer
        self.state = InteractionState()
        self.registry = get_node_registry()
        
        # Callbacks
        self.on_selection_change: Optional[Callable[[Set[str], Set[str]], None]] = None
        self.on_graph_change: Optional[Callable[[], None]] = None
        self.on_inspect_node: Optional[Callable[[str], None]] = None
        self.on_nl_submit: Optional[Callable[[str, Tuple[float, float]], None]] = None
        self.on_status_message: Optional[Callable[[str], None]] = None
    
    def handle_event(self, event: InteractionEvent) -> bool:
        """Handle an interaction event. Returns True if handled."""
        # Convert screen to world coordinates
        event.world_x, event.world_y = self.renderer.viewport.screen_to_world(
            event.screen_x, event.screen_y
        )
        
        # Handle based on current mode and event type
        if event.type == InteractionEventType.MOUSE_DOWN:
            return self._handle_mouse_down(event)
        elif event.type == InteractionEventType.MOUSE_UP:
            return self._handle_mouse_up(event)
        elif event.type == InteractionEventType.MOUSE_MOVE:
            return self._handle_mouse_move(event)
        elif event.type == InteractionEventType.MOUSE_WHEEL:
            return self._handle_mouse_wheel(event)
        elif event.type == InteractionEventType.KEY_DOWN:
            return self._handle_key_down(event)
        elif event.type == InteractionEventType.DOUBLE_CLICK:
            return self._handle_double_click(event)
        elif event.type == InteractionEventType.CONTEXT_MENU:
            return self._handle_context_menu(event)
        
        return False
    
    # --- Mouse Handlers ---
    
    def _handle_mouse_down(self, event: InteractionEvent) -> bool:
        if event.button == 2:  # Right click - context menu or pan
            if "shift" in event.modifiers or "alt" in event.modifiers:
                self.state.mode = ToolMode.PAN
                self.state.dragging = True
                self.state.drag_start_screen = (event.screen_x, event.screen_y)
                self.state.drag_start_world = (event.world_x, event.world_y)
                return True
            return False  # Let context menu handle
        
        if event.button == 1:  # Middle click - pan
            self.state.mode = ToolMode.PAN
            self.state.dragging = True
            self.state.drag_start_screen = (event.screen_x, event.screen_y)
            self.state.drag_start_world = (event.world_x, event.world_y)
            return True
        
        if event.button != 0:  # Not left click
            return False
        
        # Left click handling depends on mode
        if self.state.mode == ToolMode.SELECT:
            return self._handle_select_down(event)
        elif self.state.mode == ToolMode.PAN:
            return self._handle_pan_down(event)
        elif self.state.mode == ToolMode.CONNECT:
            return self._handle_connect_down(event)
        elif self.state.mode == ToolMode.CREATE_NODE:
            return self._handle_create_node_down(event)
        elif self.state.mode == ToolMode.DELETE:
            return self._handle_delete_down(event)
        elif self.state.mode == ToolMode.NL_INPUT:
            return self._handle_nl_input_down(event)
        
        return False
    
    def _handle_select_down(self, event: InteractionEvent) -> bool:
        # Check for port hit (start connection)
        port_hit = self.renderer.hit_test_port(event.screen_x, event.screen_y)
        if port_hit:
            node_id, port_name = port_hit
            node = self.graph.nodes.get(node_id)
            port = node.ports.get(port_name) if node else None
            
            if port and not port.is_input:  # Only start from output ports
                self.state.connecting = True
                self.state.connect_from = (node_id, port_name)
                self.state.mode = ToolMode.CONNECT
                return True
        
        # Check for node hit
        node_hit = self.renderer.hit_test_node(event.screen_x, event.screen_y)
        if node_hit:
            node = self.graph.nodes.get(node_hit)
            
            if "shift" in event.modifiers or "ctrl" in event.modifiers:
                # Toggle selection
                if node_hit in self.state.selected_nodes:
                    self.state.selected_nodes.remove(node_hit)
                else:
                    self.state.selected_nodes.add(node_hit)
            else:
                # Single select
                self.state.selected_nodes = {node_hit}
            
            self._fire_selection_change()
            
            # Start drag
            self.state.dragging = True
            self.state.drag_start_screen = (event.screen_x, event.screen_y)
            self.state.drag_start_world = (event.world_x, event.world_y)
            self.state.drag_nodes = {}
            for nid in self.state.selected_nodes:
                n = self.graph.nodes.get(nid)
                if n:
                    self.state.drag_nodes[nid] = (n.metadata.get('x', 0), n.metadata.get('y', 0))
            
            return True
        
        # Click on empty canvas - start box selection or clear selection
        if not ("shift" in event.modifiers or "ctrl" in event.modifiers):
            self.state.selected_nodes.clear()
            self.state.selected_edges.clear()
            self._fire_selection_change()
        
        # Start box selection
        self.state.box_selecting = True
        self.state.box_start = (event.world_x, event.world_y)
        self.state.box_end = (event.world_x, event.world_y)
        
        return True
    
    def _handle_pan_down(self, event: InteractionEvent) -> bool:
        self.state.dragging = True
        self.state.drag_start_screen = (event.screen_x, event.screen_y)
        self.state.drag_start_world = (event.world_x, event.world_y)
        return True
    
    def _handle_connect_down(self, event: InteractionEvent) -> bool:
        # Check if clicking on a valid target port
        port_hit = self.renderer.hit_test_port(event.screen_x, event.screen_y)
        if port_hit and self.state.connect_from:
            target_node_id, target_port_name = port_hit
            source_node_id, source_port_name = self.state.connect_from
            
            target_node = self.graph.nodes.get(target_node_id)
            target_port = target_node.ports.get(target_port_name) if target_node else None
            
            if target_port and target_port.is_input:  # Only connect to input ports
                # Check type compatibility (simplified)
                source_node = self.graph.nodes.get(source_node_id)
                source_port = source_node.ports.get(source_port_name) if source_node else None
                
                if source_port and target_port:
                    # Create the connection
                    connect_data(self.graph, source_node, source_port_name, target_node, target_port_name)
                    self._fire_graph_change()
                    
                    if self.on_status_message:
                        self.on_status_message(f"Connected {source_port_name} → {target_port_name}")
            
            # End connection mode
            self.state.connecting = False
            self.state.connect_from = None
            self.state.mode = ToolMode.SELECT
            return True
        
        # Click elsewhere - cancel connection
        self.state.connecting = False
        self.state.connect_from = None
        self.state.mode = ToolMode.SELECT
        return True
    
    def _handle_create_node_down(self, event: InteractionEvent) -> bool:
        if self.state.pending_node_template:
            # Create node at position
            self._create_node_at(self.state.pending_node_template, 
                               self.state.pending_node_position)
            self.state.pending_node_template = None
            self.state.mode = ToolMode.SELECT
            return True
        return False
    
    def _handle_delete_down(self, event: InteractionEvent) -> bool:
        # Delete selected nodes/edges
        if self.state.selected_nodes or self.state.selected_edges:
            self._delete_selected()
            return True
        
        # Delete clicked node/edge
        node_hit = self.renderer.hit_test_node(event.screen_x, event.screen_y)
        if node_hit:
            self._delete_node(node_hit)
            return True
        
        return False
    
    def _handle_nl_input_down(self, event: InteractionEvent) -> bool:
        # Place NL input at click position
        self.state.nl_input_active = True
        self.state.nl_input_position = (event.world_x, event.world_y)
        self.state.nl_input_text = ""
        return True
    
    def _handle_mouse_up(self, event: InteractionEvent) -> bool:
        if event.button != 0:
            return False
        
        # End drag
        if self.state.dragging:
            self.state.dragging = False
            self.state.drag_nodes.clear()
            
            if self.state.mode == ToolMode.PAN:
                self.state.mode = ToolMode.SELECT
            return True
        
        # End box selection
        if self.state.box_selecting:
            self.state.box_selecting = False
            self._complete_box_selection()
            return True
        
        return False
    
    def _handle_mouse_move(self, event: InteractionEvent) -> bool:
        # Update hover state
        self._update_hover(event)
        
        if self.state.dragging:
            if self.state.mode == ToolMode.PAN:
                self._handle_pan_move(event)
            elif self.state.mode == ToolMode.SELECT and self.state.drag_nodes:
                self._handle_drag_nodes(event)
            return True
        
        if self.state.box_selecting:
            self.state.box_end = (event.world_x, event.world_y)
            return True
        
        if self.state.connecting:
            self.state.connect_preview = (event.world_x, event.world_y)
            return True
        
        return False
    
    def _handle_pan_move(self, event: InteractionEvent):
        dx = event.screen_x - self.state.drag_start_screen[0]
        dy = event.screen_y - self.state.drag_start_screen[1]
        self.renderer.viewport.pan(dx, dy)
        self.state.drag_start_screen = (event.screen_x, event.screen_y)
    
    def _handle_drag_nodes(self, event: InteractionEvent):
        dx = event.world_x - self.state.drag_start_world[0]
        dy = event.world_y - self.state.drag_start_world[1]
        
        for nid, (orig_x, orig_y) in self.state.drag_nodes.items():
            node = self.graph.nodes.get(nid)
            if node:
                node.metadata['x'] = orig_x + dx
                node.metadata['y'] = orig_y + dy
        
        self._fire_graph_change()
    
    def _handle_mouse_wheel(self, event: InteractionEvent) -> bool:
        # Zoom at mouse position
        factor = 1.1 if event.modifiers.get('delta_y', 0) < 0 else 1/1.1
        self.renderer.viewport.zoom_at(event.screen_x, event.screen_y, factor)
        return True
    
    def _handle_key_down(self, event: InteractionEvent) -> bool:
        key = event.key.lower()
        
        # Escape - cancel current operation
        if key == "escape":
            self._cancel_current_operation()
            return True
        
        # Delete/Backspace - delete selection
        if key in ("delete", "backspace"):
            if self.state.selected_nodes or self.state.selected_edges:
                self._delete_selected()
                return True
        
        # Copy/Paste
        if "ctrl" in event.modifiers or "meta" in event.modifiers:
            if key == "c":
                self._copy_selection()
                return True
            elif key == "v":
                self._paste_selection(event.world_x, event.world_y)
                return True
            elif key == "x":
                self._copy_selection()
                self._delete_selected()
                return True
            elif key == "a":
                self._select_all()
                return True
            elif key == "z":
                # Undo - not implemented yet
                return True
            elif key == "s":
                # Save - trigger external handler
                return True
        
        # Tool shortcuts
        if not event.modifiers:
            if key == "v":
                self.set_mode(ToolMode.SELECT)
                return True
            elif key == "h":
                self.set_mode(ToolMode.PAN)
                return True
            elif key == "c":
                self.set_mode(ToolMode.CONNECT)
                return True
            elif key == "n":
                self.set_mode(ToolMode.CREATE_NODE)
                return True
            elif key == "d":
                self.set_mode(ToolMode.DELETE)
                return True
            elif key == "i":
                self.set_mode(ToolMode.INSPECT)
                return True
            elif key == "/":
                self.set_mode(ToolMode.NL_INPUT)
                return True
        
        return False
    
    def _handle_double_click(self, event: InteractionEvent) -> bool:
        node_hit = self.renderer.hit_test_node(event.screen_x, event.screen_y)
        if node_hit:
            if self.on_inspect_node:
                self.on_inspect_node(node_hit)
            return True
        return False
    
    def _handle_context_menu(self, event: InteractionEvent) -> bool:
        # Context menu handled by UI layer
        return False
    
    # --- Hover Handling ---
    
    def _update_hover(self, event: InteractionEvent):
        # Update node hover
        node_hit = self.renderer.hit_test_node(event.screen_x, event.screen_y)
        self.state.hovered_node = node_hit
        
        # Update port hover
        port_hit = self.renderer.hit_test_port(event.screen_x, event.screen_y)
        self.state.hovered_port = port_hit
    
    # --- Selection Handling ---
    
    def _complete_box_selection(self):
        """Complete box selection."""
        x1, y1 = self.state.box_start
        x2, y2 = self.state.box_end
        
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        new_selection = set()
        for node in self.graph.nodes.values():
            nx = node.metadata.get('x', 0)
            ny = node.metadata.get('y', 0)
            if min_x <= nx <= max_x and min_y <= ny <= max_y:
                new_selection.add(node.id)
        
        if "shift" in set():  # No modifier access here, would need event
            self.state.selected_nodes.update(new_selection)
        else:
            self.state.selected_nodes = new_selection
        
        self._fire_selection_change()
    
    def _fire_selection_change(self):
        if self.on_selection_change:
            self.on_selection_change(self.state.selected_nodes, self.state.selected_edges)
    
    def _fire_graph_change(self):
        if self.on_graph_change:
            self.on_graph_change()
    
    # --- Actions ---
    
    def set_mode(self, mode: ToolMode):
        """Change interaction mode."""
        self._cancel_current_operation()
        self.state.mode = mode
        
        if self.on_status_message:
            mode_names = {
                ToolMode.SELECT: "Select (V)",
                ToolMode.PAN: "Pan (H)",
                ToolMode.CONNECT: "Connect (C)",
                ToolMode.CREATE_NODE: "Create Node (N)",
                ToolMode.DELETE: "Delete (D)",
                ToolMode.INSPECT: "Inspect (I)",
                ToolMode.NL_INPUT: "Natural Language (/)",
            }
            self.on_status_message(f"Mode: {mode_names.get(mode, mode.value)}")
    
    def _cancel_current_operation(self):
        """Cancel any ongoing operation."""
        self.state.dragging = False
        self.state.drag_nodes.clear()
        self.state.box_selecting = False
        self.state.connecting = False
        self.state.connect_from = None
        self.state.connect_preview = None
        self.state.pending_node_template = None
        self.state.nl_input_active = False
        self.state.nl_input_text = ""
    
    def start_create_node(self, template: NodeTemplate, position: Tuple[float, float]):
        """Start creating a node from template."""
        self.state.pending_node_template = template
        self.state.pending_node_position = position
        self.state.mode = ToolMode.CREATE_NODE
    
    def _create_node_at(self, template: NodeTemplate, position: Tuple[float, float]):
        """Create a node at the given position."""
        node = template.factory() if template.factory else Node(kind=template.kind)
        
        # Add default ports
        for port in template.default_ports:
            node.add_port(port)
        
        # Set properties
        node.properties.update(template.default_properties)
        
        # Set position
        node.metadata['x'] = position[0]
        node.metadata['y'] = position[1]
        
        # Add to graph
        self.graph.add_node(node)
        
        # Select the new node
        self.state.selected_nodes = {node.id}
        self._fire_selection_change()
        self._fire_graph_change()
    
    def _delete_node(self, node_id: str):
        """Delete a node and its edges."""
        # Remove connected edges
        edges_to_remove = [
            e.id for e in self.graph.edges
            if e.source == node_id or e.target == node_id
        ]
        for edge_id in edges_to_remove:
            self.graph.remove_edge(edge_id)
        
        # Remove node
        self.graph.remove_node(node_id)
        
        # Update selection
        self.state.selected_nodes.discard(node_id)
        self._fire_selection_change()
        self._fire_graph_change()
    
    def _delete_selected(self):
        """Delete all selected nodes and edges."""
        # Delete selected edges
        for edge_id in self.state.selected_edges:
            self.graph.remove_edge(edge_id)
        
        # Delete selected nodes
        for node_id in list(self.state.selected_nodes):
            self.graph.remove_node(node_id)
        
        self.state.selected_nodes.clear()
        self.state.selected_edges.clear()
        self._fire_selection_change()
        self._fire_graph_change()
    
    def _copy_selection(self):
        """Copy selected nodes to clipboard."""
        self.state.clipboard = []
        
        # Include all selected nodes and their internal edges
        for node_id in self.state.selected_nodes:
            node = self.graph.nodes.get(node_id)
            if node:
                node_data = {
                    "node": node,
                    "edges": [e for e in self.graph.edges 
                             if e.source == node_id or e.target == node_id]
                }
                self.state.clipboard.append(node_data)
        
        if self.on_status_message:
            self.on_status_message(f"Copied {len(self.state.clipboard)} nodes")
    
    def _paste_selection(self, x: float, y: float):
        """Paste clipboard at position."""
        if not self.state.clipboard:
            return
        
        # Calculate offset to center of clipboard
        min_x = min(n["node"].metadata.get('x', 0) for n in self.state.clipboard)
        max_x = max(n["node"].metadata.get('x', 0) for n in self.state.clipboard)
        min_y = min(n["node"].metadata.get('y', 0) for n in self.state.clipboard)
        max_y = max(n["node"].metadata.get('y', 0) for n in self.state.clipboard)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        offset_x = x - center_x
        offset_y = y - center_y
        
        # Create ID mapping
        id_map = {}
        
        # Paste nodes
        for item in self.state.clipboard:
            old_node = item["node"]
            # Create new node (simplified - would need deep copy)
            new_node = Node(kind=old_node.kind, name=old_node.name)
            new_node.properties = old_node.properties.copy()
            new_node.metadata = old_node.metadata.copy()
            new_node.metadata['x'] = new_node.metadata.get('x', 0) + offset_x
            new_node.metadata['y'] = new_node.metadata.get('y', 0) + offset_y
            
            for port in old_node.ports.values():
                new_node.add_port(Port(
                    name=port.name,
                    type=port.type,
                    is_input=port.is_input,
                    is_required=port.is_required,
                    default_value=port.default_value,
                    description=port.description,
                ))
            
            self.graph.add_node(new_node)
            id_map[old_node.id] = new_node.id
        
        # Paste edges
        for item in self.state.clipboard:
            for edge in item["edges"]:
                if edge.source in id_map and edge.target in id_map:
                    source_node = self.graph.nodes.get(id_map[edge.source])
                    target_node = self.graph.nodes.get(id_map[edge.target])
                    if source_node and target_node:
                        # Recreate edge
                        if edge.kind == EdgeKind.DATA:
                            connect_data(self.graph, source_node, edge.source_port, 
                                       target_node, edge.target_port)
                        elif edge.kind == EdgeKind.CONTROL:
                            connect_control(self.graph, source_node, target_node,
                                          edge.source_port, edge.target_port)
                        elif edge.kind == EdgeKind.COMPOSITION:
                            connect_composition(self.graph, source_node, target_node)
        
        # Select pasted nodes
        self.state.selected_nodes = set(id_map.values())
        self._fire_selection_change()
        self._fire_graph_change()
        
        if self.on_status_message:
            self.on_status_message(f"Pasted {len(id_map)} nodes")
    
    def _select_all(self):
        """Select all nodes."""
        self.state.selected_nodes = set(self.graph.nodes.keys())
        self._fire_selection_change()
    
    # --- NL Input ---
    
    def handle_nl_input(self, text: str, submit: bool = False):
        """Handle natural language input."""
        self.state.nl_input_text = text
        
        if submit and text.strip():
            if self.on_nl_submit:
                self.on_nl_submit(text, self.state.nl_input_position)
            self.state.nl_input_active = False
            self.state.nl_input_text = ""
            self.state.mode = ToolMode.SELECT


def create_interaction_handler(graph: Graph, canvas_renderer) -> InteractionHandler:
    """Factory function to create interaction handler."""
    return InteractionHandler(graph, canvas_renderer)