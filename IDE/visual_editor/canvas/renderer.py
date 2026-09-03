"""
Visual Editor - Canvas Renderer
Renders the GIR graph as an interactive node-graph canvas.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple, Set
import json
import math

from parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind,
    Port, TypeRef,
)


class Viewport:
    """Canvas viewport with zoom/pan."""
    
    def __init__(self, x: float = 0, y: float = 0, zoom: float = 1.0, width: float = 1920, height: float = 1080):
        self.x = x
        self.y = y
        self.zoom = zoom
        self.width = width
        self.height = height
        self.min_zoom = 0.1
        self.max_zoom = 5.0
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        screen_x = (world_x - self.x) * self.zoom + self.width / 2
        screen_y = (world_y - self.y) * self.zoom + self.height / 2
        return (screen_x, screen_y)
    
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        world_x = (screen_x - self.width / 2) / self.zoom + self.x
        world_y = (screen_y - self.height / 2) / self.zoom + self.y
        return (world_x, world_y)
    
    def pan(self, dx: float, dy: float):
        """Pan the viewport."""
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom
    
    def zoom_at(self, screen_x: float, screen_y: float, factor: float):
        """Zoom at a specific screen point."""
        world_before = self.screen_to_world(screen_x, screen_y)
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        world_after = self.screen_to_world(screen_x, screen_y)
        self.x += world_before[0] - world_after[0]
        self.y += world_before[1] - world_after[1]
    
    def fit_to_content(self, nodes: Dict[str, Node], padding: float = 100):
        """Fit viewport to show all nodes."""
        if not nodes:
            return
        
        min_x = min(n.metadata.get('x', 0) for n in nodes.values())
        max_x = max(n.metadata.get('x', 0) for n in nodes.values())
        min_y = min(n.metadata.get('y', 0) for n in nodes.values())
        max_y = max(n.metadata.get('y', 0) for n in nodes.values())
        
        content_width = max_x - min_x + 2 * padding
        content_height = max_y - min_y + 2 * padding
        
        if content_width <= 0 or content_height <= 0:
            return
        
        zoom_x = self.width / content_width
        zoom_y = self.height / content_height
        self.zoom = min(zoom_x, zoom_y, self.max_zoom)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.x = center_x
        self.y = center_y
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "zoom": self.zoom,
            "width": self.width,
            "height": self.height,
        }


class RenderLayer(Enum):
    """Rendering layers (back to front)."""
    GRID = 0
    EDGES = 1
    NODES = 2
    PORTS = 3
    SELECTION = 4
    UI_OVERLAY = 5


@dataclass
class RenderContext:
    """Context for rendering a frame."""
    viewport: Viewport
    canvas_width: float
    canvas_height: float
    selected_nodes: Set[str] = field(default_factory=set)
    selected_edges: Set[str] = field(default_factory=set)
    hovered_node: Optional[str] = None
    hovered_port: Optional[Tuple[str, str]] = None  # (node_id, port_name)
    dragging_node: Optional[str] = None
    drag_offset: Tuple[float, float] = (0, 0)
    connecting_from: Optional[Tuple[str, str]] = None  # (node_id, port_name)
    show_grid: bool = True
    show_minimap: bool = True


class NodeRenderer:
    """Renders nodes and their ports."""
    
    # Node type colors
    NODE_COLORS = {
        NodeKind.MODULE: "#2c3e50",
        NodeKind.FUNCTION: "#27ae60",
        NodeKind.SCOPE: "#8e44ad",
        
        NodeKind.LITERAL: "#3498db",
        NodeKind.VARIABLE: "#2980b9",
        NodeKind.PARAMETER: "#1abc9c",
        NodeKind.CONSTANT: "#16a085",
        
        NodeKind.ARITHMETIC: "#e67e22",
        NodeKind.LOGIC: "#d35400",
        NodeKind.COMPARISON: "#e74c3c",
        NodeKind.CAST: "#c0392b",
        NodeKind.CALL: "#9b59b6",
        NodeKind.INDEX: "#8e44ad",
        NodeKind.FIELD_ACCESS: "#8e44ad",
        
        NodeKind.IF: "#f39c12",
        NodeKind.LOOP: "#f1c40f",
        NodeKind.MATCH: "#f39c12",
        NodeKind.TRY: "#e67e22",
        NodeKind.SEQUENCE: "#95a5a6",
        NodeKind.PARALLEL: "#7f8c8d",
        NodeKind.BREAK: "#95a5a6",
        NodeKind.CONTINUE: "#95a5a6",
        NodeKind.RETURN: "#e74c3c",
        
        NodeKind.PRIMITIVE_TYPE: "#34495e",
        NodeKind.COMPOSITE_TYPE: "#34495e",
        NodeKind.FUNCTION_TYPE: "#34495e",
        NodeKind.EFFECT_TYPE: "#34495e",
        NodeKind.GENERIC_TYPE: "#34495e",
        
        NodeKind.IO: "#1abc9c",
        NodeKind.STATE: "#16a085",
        NodeKind.EXCEPTION: "#c0392b",
        NodeKind.ASYNC: "#9b59b6",
        NodeKind.RESOURCE: "#27ae60",
        
        NodeKind.CONTRACT: "#8e44ad",
        NodeKind.ANNOTATION: "#95a5a6",
        NodeKind.DOCUMENTATION: "#7f8c8d",
        NodeKind.SOURCE_MAP: "#95a5a6",
    }
    
    # Node shapes by category
    NODE_SHAPES = {
        # Value nodes - circles
        NodeKind.LITERAL: "circle",
        NodeKind.VARIABLE: "circle",
        NodeKind.PARAMETER: "circle",
        NodeKind.CONSTANT: "circle",
        
        # Operations - diamonds
        NodeKind.ARITHMETIC: "diamond",
        NodeKind.LOGIC: "diamond",
        NodeKind.COMPARISON: "diamond",
        NodeKind.CAST: "diamond",
        NodeKind.CALL: "diamond",
        NodeKind.INDEX: "diamond",
        NodeKind.FIELD_ACCESS: "diamond",
        
        # Control - hexagons
        NodeKind.IF: "hexagon",
        NodeKind.LOOP: "hexagon",
        NodeKind.MATCH: "hexagon",
        NodeKind.TRY: "hexagon",
        NodeKind.SEQUENCE: "hexagon",
        NodeKind.PARALLEL: "hexagon",
        NodeKind.BREAK: "hexagon",
        NodeKind.CONTINUE: "hexagon",
        NodeKind.RETURN: "hexagon",
        
        # Types - rectangles
        NodeKind.PRIMITIVE_TYPE: "rectangle",
        NodeKind.COMPOSITE_TYPE: "rectangle",
        NodeKind.FUNCTION_TYPE: "rectangle",
        NodeKind.EFFECT_TYPE: "rectangle",
        NodeKind.GENERIC_TYPE: "rectangle",
        
        # Effects - rounded rectangles
        NodeKind.IO: "rounded_rect",
        NodeKind.STATE: "rounded_rect",
        NodeKind.EXCEPTION: "rounded_rect",
        NodeKind.ASYNC: "rounded_rect",
        NodeKind.RESOURCE: "rounded_rect",
        
        # Meta - triangles
        NodeKind.CONTRACT: "triangle",
        NodeKind.ANNOTATION: "triangle",
        NodeKind.DOCUMENTATION: "triangle",
        NodeKind.SOURCE_MAP: "triangle",
        
        # Modules - large rectangles
        NodeKind.MODULE: "rectangle",
        NodeKind.FUNCTION: "rounded_rect",
        NodeKind.SCOPE: "rectangle",
    }
    
    DEFAULT_NODE_WIDTH = 180
    DEFAULT_NODE_HEIGHT = 60
    PORT_RADIUS = 8
    PORT_SPACING = 30
    
    def __init__(self, context: RenderContext):
        self.ctx = context
    
    def get_node_color(self, node: Node) -> str:
        """Get color for node kind."""
        return self.NODE_COLORS.get(node.kind, "#7f8c8d")
    
    def get_node_shape(self, node: Node) -> str:
        """Get shape for node kind."""
        return self.NODE_SHAPES.get(node.kind, "rectangle")
    
    def get_node_bounds(self, node: Node) -> Tuple[float, float, float, float]:
        """Get node bounding box in world coordinates."""
        x = node.metadata.get('x', 0)
        y = node.metadata.get('y', 0)
        
        # Calculate size based on ports
        input_count = len(node.input_ports())
        output_count = len(node.output_ports())
        port_rows = max(input_count, output_count)
        
        width = self.DEFAULT_NODE_WIDTH
        height = max(self.DEFAULT_NODE_HEIGHT, port_rows * self.PORT_SPACING + 20)
        
        return (x - width/2, y - height/2, width, height)
    
    def get_port_position(self, node: Node, port: Port) -> Tuple[float, float]:
        """Get port position in world coordinates."""
        bounds = self.get_node_bounds(node)
        x, y, width, height = bounds
        
        # Find port index
        ports = node.input_ports() if port.is_input else node.output_ports()
        port_index = next((i for i, p in enumerate(ports) if p.name == port.name), 0)
        
        # Calculate vertical position
        total_ports = len(ports)
        start_y = y + (height - (total_ports - 1) * self.PORT_SPACING) / 2
        port_y = start_y + port_index * self.PORT_SPACING
        
        if port.is_input:
            port_x = x  # Left side
        else:
            port_x = x + width  # Right side
        
        return (port_x, port_y)
    
    def render_node(self, node: Node) -> Dict[str, Any]:
        """Render node to draw commands."""
        bounds = self.get_node_bounds(node)
        x, y, width, height = bounds
        color = self.get_node_color(node)
        shape = self.get_node_shape(node)
        
        # Check selection/hover
        is_selected = node.id in self.ctx.selected_nodes
        is_hovered = node.id == self.ctx.hovered_node
        
        # Convert to screen coordinates
        screen_x, screen_y = self.ctx.viewport.world_to_screen(x, y)
        screen_width = width * self.ctx.viewport.zoom
        screen_height = height * self.ctx.viewport.zoom
        
        # Build draw commands
        commands = []
        
        # Node body
        if shape == "circle":
            commands.append({
                "type": "circle",
                "x": screen_x + screen_width/2,
                "y": screen_y + screen_height/2,
                "radius": min(screen_width, screen_height)/2,
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        elif shape == "diamond":
            commands.append({
                "type": "path",
                "points": [
                    (screen_x + screen_width/2, screen_y),
                    (screen_x + screen_width, screen_y + screen_height/2),
                    (screen_x + screen_width/2, screen_y + screen_height),
                    (screen_x, screen_y + screen_height/2),
                ],
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        elif shape == "hexagon":
            # Simplified as rectangle for now
            commands.append({
                "type": "rect",
                "x": screen_x,
                "y": screen_y,
                "width": screen_width,
                "height": screen_height,
                "radius": 8,
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        elif shape == "rounded_rect":
            commands.append({
                "type": "rect",
                "x": screen_x,
                "y": screen_y,
                "width": screen_width,
                "height": screen_height,
                "radius": 12,
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        elif shape == "triangle":
            commands.append({
                "type": "path",
                "points": [
                    (screen_x + screen_width/2, screen_y),
                    (screen_x + screen_width, screen_y + screen_height),
                    (screen_x, screen_y + screen_height),
                ],
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        else:  # rectangle
            commands.append({
                "type": "rect",
                "x": screen_x,
                "y": screen_y,
                "width": screen_width,
                "height": screen_height,
                "radius": 4,
                "fill": color,
                "stroke": "#fff" if is_selected else "#333",
                "stroke_width": 3 if is_selected else 2,
            })
        
        # Node label
        label = node.name or node.kind.value
        commands.append({
            "type": "text",
            "x": screen_x + screen_width/2,
            "y": screen_y + 20 * self.ctx.viewport.zoom,
            "text": label,
            "font": f"{max(10, 12 * self.ctx.viewport.zoom)}px monospace",
            "fill": "#fff",
            "align": "center",
        })
        
        # Type signature if available
        if node.kind == NodeKind.FUNCTION:
            # Show function signature
            pass
        
        # Ports
        for port in node.ports.values():
            port_pos = self.get_port_position(node, port)
            screen_px, screen_py = self.ctx.viewport.world_to_screen(port_pos[0], port_pos[1])
            
            port_color = self._get_port_color(port)
            is_port_hovered = (self.ctx.hovered_port == (node.id, port.name))
            
            commands.append({
                "type": "circle",
                "x": screen_px,
                "y": screen_py,
                "radius": self.PORT_RADIUS * self.ctx.viewport.zoom,
                "fill": port_color,
                "stroke": "#fff" if is_port_hovered else "#333",
                "stroke_width": 2 if is_port_hovered else 1,
                "port_name": port.name,
                "port_type": str(port.type) if port.type else "",
                "is_input": port.is_input,
            })
            
            # Port label
            label_x = screen_px - (10 + 80 * self.ctx.viewport.zoom) if port.is_input else screen_px + (10 * self.ctx.viewport.zoom)
            commands.append({
                "type": "text",
                "x": label_x,
                "y": screen_py + 4 * self.ctx.viewport.zoom,
                "text": port.name,
                "font": f"{max(8, 10 * self.ctx.viewport.zoom)}px monospace",
                "fill": "#ccc",
                "align": "right" if port.is_input else "left",
            })
        
        return {
            "node_id": node.id,
            "layer": RenderLayer.NODES.value,
            "bounds": (screen_x, screen_y, screen_width, screen_height),
            "commands": commands,
        }
    
    def _get_port_color(self, port: Port) -> str:
        """Get color based on port type."""
        if not port.type:
            return "#95a5a6"
        
        type_str = str(port.type).lower()
        if "int" in type_str:
            return "#3498db"
        elif "bool" in type_str:
            return "#e74c3c"
        elif "string" in type_str:
            return "#27ae60"
        elif "float" in type_str:
            return "#f39c12"
        elif "function" in type_str:
            return "#9b59b6"
        elif "array" in type_str or "list" in type_str:
            return "#1abc9c"
        else:
            return "#95a5a6"


class EdgeRenderer:
    """Renders edges between nodes."""
    
    EDGE_COLORS = {
        EdgeKind.DATA: "#3498db",
        EdgeKind.CONTROL: "#e74c3c",
        EdgeKind.DEPENDENCY: "#9b59b6",
        EdgeKind.COMPOSITION: "#27ae60",
        EdgeKind.ANNOTATION: "#95a5a6",
        EdgeKind.TYPE_OF: "#f39c12",
        EdgeKind.SUBTYPE_OF: "#f39c12",
        EdgeKind.IMPLEMENTS: "#f39c12",
        EdgeKind.DEFINES: "#27ae60",
        EdgeKind.USES: "#3498db",
        EdgeKind.CAPTURES: "#9b59b6",
        EdgeKind.HAS_EFFECT: "#e67e22",
        EdgeKind.HANDLES_EFFECT: "#e67e22",
        EdgeKind.REQUIRES: "#8e44ad",
        EdgeKind.ENSURES: "#8e44ad",
        EdgeKind.INVARIANT: "#8e44ad",
    }
    
    EDGE_STYLES = {
        EdgeKind.DATA: "solid",
        EdgeKind.CONTROL: "dashed",
        EdgeKind.DEPENDENCY: "dotted",
        EdgeKind.COMPOSITION: "solid",
        EdgeKind.ANNOTATION: "dotted",
    }
    
    def __init__(self, context: RenderContext, node_renderer: NodeRenderer):
        self.ctx = context
        self.node_renderer = node_renderer
    
    def render_edge(self, edge: Edge) -> Optional[Dict[str, Any]]:
        """Render edge to draw commands."""
        source_node = self.ctx.viewport.graph.nodes.get(edge.source) if hasattr(self.ctx.viewport, 'graph') else None
        target_node = self.ctx.viewport.graph.nodes.get(edge.target) if hasattr(self.ctx.viewport, 'graph') else None
        
        # Need to get nodes from context - pass graph separately
        # For now, return None if we can't resolve
        if not source_node or not target_node:
            return None
        
        source_port = source_node.ports.get(edge.source_port)
        target_port = target_node.ports.get(edge.target_port)
        
        if not source_port or not target_port:
            return None
        
        source_pos = self.node_renderer.get_port_position(source_node, source_port)
        target_pos = self.node_renderer.get_port_position(target_node, target_port)
        
        screen_sx, screen_sy = self.ctx.viewport.world_to_screen(source_pos[0], source_pos[1])
        screen_tx, screen_ty = self.ctx.viewport.world_to_screen(target_pos[0], target_pos[1])
        
        color = self.EDGE_COLORS.get(edge.kind, "#7f8c8d")
        style = self.EDGE_STYLES.get(edge.kind, "solid")
        
        is_selected = edge.id in self.ctx.selected_edges
        
        # Calculate bezier curve control points
        mid_x = (screen_sx + screen_tx) / 2
        mid_y = (screen_sy + screen_ty) / 2
        
        # Offset for curved edges
        dx = screen_tx - screen_sx
        dy = screen_ty - screen_sy
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            # Perpendicular offset
            offset = min(dist * 0.3, 100)
            ctrl_x = mid_x - dy / dist * offset
            ctrl_y = mid_y + dx / dist * offset
        else:
            ctrl_x = mid_x
            ctrl_y = mid_y
        
        return {
            "edge_id": edge.id,
            "layer": RenderLayer.EDGES.value,
            "kind": edge.kind.value,
            "commands": [{
                "type": "bezier",
                "start": (screen_sx, screen_sy),
                "control": (ctrl_x, ctrl_y),
                "end": (screen_tx, screen_ty),
                "stroke": color,
                "stroke_width": 3 if is_selected else 2,
                "style": style,
                "arrow": True,
                "arrow_size": 10 * self.ctx.viewport.zoom,
            }],
        }


class GridRenderer:
    """Renders background grid."""
    
    def __init__(self, context: RenderContext):
        self.ctx = context
    
    def render(self) -> Dict[str, Any]:
        if not self.ctx.show_grid:
            return {"layer": RenderLayer.GRID.value, "commands": []}
        
        viewport = self.ctx.viewport
        zoom = viewport.zoom
        
        # Grid spacing in world units
        major_spacing = 100
        minor_spacing = 20
        
        # Calculate visible world bounds
        tl_world = viewport.screen_to_world(0, 0)
        br_world = viewport.screen_to_world(viewport.width, viewport.height)
        
        min_x = math.floor(tl_world[0] / major_spacing) * major_spacing
        max_x = math.ceil(br_world[0] / major_spacing) * major_spacing
        min_y = math.floor(tl_world[1] / major_spacing) * major_spacing
        max_y = math.ceil(br_world[1] / major_spacing) * major_spacing
        
        commands = []
        
        # Minor grid
        if zoom > 0.3:
            minor_min_x = math.floor(tl_world[0] / minor_spacing) * minor_spacing
            minor_max_x = math.ceil(br_world[0] / minor_spacing) * minor_spacing
            minor_min_y = math.floor(tl_world[1] / minor_spacing) * minor_spacing
            minor_max_y = math.ceil(br_world[1] / minor_spacing) * minor_spacing
            
            for x in range(int(minor_min_x), int(minor_max_x) + 1, minor_spacing):
                sx, _ = viewport.world_to_screen(x, 0)
                commands.append({
                    "type": "line",
                    "start": (sx, 0),
                    "end": (sx, viewport.height),
                    "stroke": "#222",
                    "stroke_width": 0.5,
                })
            
            for y in range(int(minor_min_y), int(minor_max_y) + 1, minor_spacing):
                _, sy = viewport.world_to_screen(0, y)
                commands.append({
                    "type": "line",
                    "start": (0, sy),
                    "end": (viewport.width, sy),
                    "stroke": "#222",
                    "stroke_width": 0.5,
                })
        
        # Major grid
        for x in range(int(min_x), int(max_x) + 1, major_spacing):
            sx, _ = viewport.world_to_screen(x, 0)
            commands.append({
                "type": "line",
                "start": (sx, 0),
                "end": (sx, viewport.height),
                "stroke": "#333",
                "stroke_width": 1,
            })
        
        for y in range(int(min_y), int(max_y) + 1, major_spacing):
            _, sy = viewport.world_to_screen(0, y)
            commands.append({
                "type": "line",
                "start": (0, sy),
                "end": (viewport.width, sy),
                "stroke": "#333",
                "stroke_width": 1,
            })
        
        # Origin axes
        ox, _ = viewport.world_to_screen(0, 0)
        _, oy = viewport.world_to_screen(0, 0)
        if 0 <= ox <= viewport.width:
            commands.append({
                "type": "line",
                "start": (ox, 0),
                "end": (ox, viewport.height),
                "stroke": "#555",
                "stroke_width": 2,
            })
        if 0 <= oy <= viewport.height:
            commands.append({
                "type": "line",
                "start": (0, oy),
                "end": (viewport.width, oy),
                "stroke": "#555",
                "stroke_width": 2,
            })
        
        return {"layer": RenderLayer.GRID.value, "commands": commands}


class CanvasRenderer:
    """Main canvas renderer coordinating all renderers."""
    
    def __init__(self, graph: Graph, width: float = 1920, height: float = 1080):
        self.graph = graph
        self.viewport = Viewport(width=width, height=height)
        self.ctx = RenderContext(viewport=self.viewport, canvas_width=width, canvas_height=height)
        self.node_renderer = NodeRenderer(self.ctx)
        self.edge_renderer = EdgeRenderer(self.ctx, self.node_renderer)
        self.grid_renderer = GridRenderer(self.ctx)
        # Attach graph to viewport for edge renderer
        self.ctx.viewport.graph = graph
    
    def render(self) -> List[Dict[str, Any]]:
        """Render full frame, returns layered draw commands."""
        layers = {}
        
        # Grid
        grid_layer = self.grid_renderer.render()
        layers.setdefault(grid_layer["layer"], []).extend(grid_layer["commands"])
        
        # Edges
        for edge in self.graph.edges:
            edge_render = self.edge_renderer.render_edge(edge)
            if edge_render:
                layers.setdefault(edge_render["layer"], []).extend(edge_render["commands"])
        
        # Nodes
        for node in self.graph.nodes.values():
            node_render = self.node_renderer.render_node(node)
            layers.setdefault(node_render["layer"], []).extend(node_render["commands"])
        
        # Sort layers and flatten
        result = []
        for layer in sorted(layers.keys()):
            result.extend(layers[layer])
        
        return result
    
    def hit_test_node(self, screen_x: float, screen_y: float) -> Optional[str]:
        """Find node at screen position."""
        world_x, world_y = self.viewport.screen_to_world(screen_x, screen_y)
        
        # Check nodes in reverse order (topmost first)
        for node in reversed(list(self.graph.nodes.values())):
            bounds = self.node_renderer.get_node_bounds(node)
            x, y, width, height = bounds
            if x <= world_x <= x + width and y <= world_y <= y + height:
                return node.id
        return None
    
    def hit_test_port(self, screen_x: float, screen_y: float) -> Optional[Tuple[str, str]]:
        """Find port at screen position."""
        world_x, world_y = self.viewport.screen_to_world(screen_x, screen_y)
        
        for node in self.graph.nodes.values():
            for port in node.ports.values():
                port_pos = self.node_renderer.get_port_position(node, port)
                dist = math.hypot(world_x - port_pos[0], world_y - port_pos[1])
                if dist < 15 / self.viewport.zoom:  # Port hit radius
                    return (node.id, port.name)
        return None
    
    def to_json(self) -> str:
        """Export render state as JSON."""
        return json.dumps({
            "viewport": self.viewport.to_dict(),
            "nodes": {
                nid: {
                    "x": node.metadata.get('x', 0),
                    "y": node.metadata.get('y', 0),
                    "kind": node.kind.value,
                    "name": node.name,
                }
                for nid, node in self.graph.nodes.items()
            },
        }, indent=2)


def create_canvas_renderer(graph: Graph, width: float = 1920, height: float = 1080) -> CanvasRenderer:
    """Factory function to create canvas renderer."""
    return CanvasRenderer(graph, width, height)