# OREO Visual Editor

> Documentation for the node-graph canvas, interaction system, node registry, and architecture bridge.

---

## 1. Overview

The visual editor is the **primary interface** for OREO — a node-graph canvas where programs are built by dragging nodes and connecting ports. It provides live execution visualization, type-checking on connection, and round-trip NL ↔ Graph editing.

### 1.1 Key Features
- **Infinite canvas** with zoom/pan, grid snap, mini-map
- **Typed ports** — connections validated on drop
- **Node palette** organized by category (Value, Operation, Control, Type, Effect, Meta, Scope)
- **Live execution visualization** — token highlighting, heat maps, time travel
- **NL input box** — type natural language, see graph appear
- **Voice input** — speech-to-text → NL → graph
- **AI generation** — LLM → Intent → Graph

---

## 2. Canvas Renderer

### 2.1 File
`/home/jayson/OREO/IDE/visual_editor/canvas/renderer.py` (721 lines)

### 2.2 Core Classes

#### Viewport
```python
class Viewport:
    """Canvas viewport with zoom/pan."""
    
    def __init__(self, x: float = 0, y: float = 0, zoom: float = 1.0, 
                 width: float = 1920, height: float = 1080):
        self.x = x
        self.y = y
        self.zoom = zoom
        self.width = width
        self.height = height
        self.min_zoom = 0.1
        self.max_zoom = 5.0
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]
    def pan(self, dx: float, dy: float)
    def zoom_at(self, screen_x: float, screen_y: float, factor: float)
    def fit_to_content(self, nodes: Dict[str, Node], padding: float = 100)
    def to_dict(self) -> Dict[str, Any]
```

#### Render Layers (back to front)
```python
class RenderLayer(Enum):
    GRID = 0
    EDGES = 1
    NODES = 2
    PORTS = 3
    SELECTION = 4
    UI_OVERLAY = 5
```

#### RenderContext
```python
@dataclass
class RenderContext:
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
```

#### NodeRenderer
Renders nodes with category-based colors:

| NodeKind | Color | Shape |
|----------|-------|-------|
| `MODULE` | `#2c3e50` | Rectangle |
| `FUNCTION` | `#27ae60` | Rectangle |
| `SCOPE` | `#8e44ad` | Rectangle |
| `LITERAL` | `#3498db` | Circle |
| `VARIABLE` | `#2980b9` | Circle |
| `PARAMETER` | `#1abc9c` | Circle |
| `CONSTANT` | `#16a085` | Circle |
| `ARITHMETIC` | `#e67e22` | Rectangle |
| `LOGIC` | `#d35400` | Rectangle |
| `COMPARISON` | `#e74c3c` | Rectangle |
| `CAST` | `#c0392b` | Rectangle |
| `CALL` | `#9b59b6` | Rectangle |
| `IF` | `#f39c12` | Diamond |
| `LOOP` | `#f1c40f` | Diamond |
| `MATCH` | `#f39c12` | Diamond |
| `TRY` | `#e67e22` | Diamond |
| `SEQUENCE` | `#95a5a6` | Rounded rect |
| `PARALLEL` | `#7f8c8d` | Rounded rect |
| `PRIMITIVE_TYPE` | `#34495e` | Hexagon |
| `COMPOSITE_TYPE` | `#34495e` | Hexagon |
| `IO` | `#e67e22` | Octagon |
| `STATE` | `#e67e22` | Octagon |
| `CONTRACT` | `#95a5a6` | Document |

**Node rendering includes:**
- Node body (colored shape)
- Ports (small circles on boundary, color-coded by type)
- Labels (name + type signature)
- Selection highlight (glow)
- Error indicator (red border if type mismatch)

#### EdgeRenderer
- **Bezier curves** for smooth connections
- **Data edges** — solid, colored by type
- **Control edges** — dashed, gray
- **Composition edges** — dotted, light gray
- **Arrowheads** at target port
- **Highlight** on hover/selection

#### Minimap
- Bottom-right corner
- Shows all nodes as colored dots
- Viewport rectangle indicates visible area
- Click to jump

---

## 3. Interaction System

### 3.1 File
`/home/jayson/OREO/IDE/visual_editor/interaction/tools.py`

### 3.2 Interaction Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Select** | Click node/edge | Add to selection, show properties |
| **Pan** | Middle drag / Space+drag | Move viewport |
| **Box Select** | Drag on empty canvas | Select multiple nodes |
| **Connect** | Drag from port | Create edge preview, validate on drop |
| **Drag Node** | Drag node body | Move node, update edge paths |
| **Create** | Palette click / NL input | Add node at cursor position |

### 3.3 Connection Validation

```python
def validate_connection(source_port: Port, target_port: Port) -> ValidationResult:
    """Check if connection is type-compatible."""
    # 1. Direction: source must be output, target must be input
    if not source_port.is_output or target_port.is_output:
        return ValidationResult(False, "Port direction mismatch")
    
    # 2. Type compatibility: source_type ⊆ target_type
    if source_port.type and target_port.type:
        if not is_subtype(source_port.type, target_port.type):
            return ValidationResult(False, f"Type mismatch: {source_port.type} → {target_port.type}")
    
    # 3. Required check: target port not already connected (if single-input)
    if target_port.is_required and target_port.is_connected:
        return ValidationResult(False, "Port already connected")
    
    return ValidationResult(True, "OK")
```

### 3.4 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` + drag | Pan canvas |
| `Ctrl` + scroll | Zoom |
| `Delete` | Delete selected |
| `Ctrl`+C / `Ctrl`+V | Copy/paste nodes |
| `Ctrl`+Z / `Ctrl`+Y | Undo/redo |
| `F` | Fit to content |
| `/` | Focus NL input box |
| `V` | Toggle voice input |

---

## 4. Node Registry (Palette)

### 4.1 File
`/home/jayson/OREO/IDE/visual_editor/nodes/node_registry.py`

### 4.2 Registry Structure

```python
@dataclass
class NodeTemplate:
    """Template for creating nodes from palette."""
    kind: NodeKind
    name: str
    description: str
    category: NodeCategory
    default_ports: List[Port]
    default_properties: Dict[str, Any]
    icon: str  # emoji or icon name
    search_tags: List[str]

class NodeRegistry:
    """Registry of node types available in the visual editor palette."""
    
    def __init__(self):
        self.templates: Dict[NodeKind, NodeTemplate] = {}
        self._register_builtin()
    
    def get_template(self, kind: NodeKind) -> Optional[NodeTemplate]
    def search(self, query: str) -> List[NodeTemplate]
    def get_by_category(self, category: NodeCategory) -> List[NodeTemplate]
    def create_node(self, kind: NodeKind, **overrides) -> Node
```

### 4.3 Categories

| Category | NodeKinds | Icon |
|----------|-----------|------|
| **Module** | MODULE, FUNCTION, SCOPE | 📦 |
| **Value** | LITERAL, VARIABLE, PARAMETER, CONSTANT | 🔵 |
| **Operation** | ARITHMETIC, LOGIC, COMPARISON, CAST, CALL, INDEX, FIELD_ACCESS | ⚙️ |
| **Control** | IF, LOOP, MATCH, TRY, SEQUENCE, PARALLEL, BREAK, CONTINUE, RETURN | 🔀 |
| **Type** | PRIMITIVE_TYPE, COMPOSITE_TYPE, FUNCTION_TYPE, EFFECT_TYPE, GENERIC_TYPE | 🏷️ |
| **Effect** | IO, STATE, EXCEPTION, ASYNC, RESOURCE | ⚡ |
| **Meta** | CONTRACT, ANNOTATION, DOCUMENTATION, SOURCE_MAP | 📝 |

### 4.4 Palette UI
- **Search box** — filter by name, description, tags
- **Category tabs** — Module, Value, Operation, Control, Type, Effect, Meta
- **Drag to canvas** — creates node at drop position
- **Right-click** — show documentation, example usage

---

## 5. Architecture Bridge (GraphLang)

### 5.1 File
`/home/jayson/OREO/IDE/visual_editor/architecture.py`

### 5.2 Purpose
Bridges the Architecture subsystem's self-contained web editor (merged from GraphLang) into the visual_editor module namespace.

```python
from parser.architecture.visual import (
    EDITOR_PATH,  # Path to graphlang_editor.html
    run_editor,   # Launch talk+draw web editor
)

# The architecture editor provides:
# - Talk: NL input → architecture graph
# - Draw: Canvas for pages, databases, auth, includes
# - Model view: Graph visualization
# - Voice: TTS narration of graph state
```

### 5.3 GraphLang Editor (`parser/architecture/visual.py`)

**Features:**
- **Talk** — NL commands for architecture (pages, dbs, auth, includes)
- **Draw** — Visual canvas for architecture graph
- **Voice** — `narrate()` speaks graph state
- **Emit** — Generate runnable web app from graph
- **Runtime** — Handshake enforcement (CONNECTS_TO + AUTHENTICATES_WITH)

**Launch:**
```bash
python3 -m parser.architecture.visual
# Opens http://localhost:8080 (talk+draw editor)
```

---

## 6. Web Frontend

### 6.1 Structure
```
/home/jayson/OREO/IDE/visual_editor/web/
├── package.json
├── src/
│   ├── main.tsx           # React entry
│   ├── components/
│   │   ├── Canvas.tsx     # Main canvas (Konva/Canvas API)
│   │   ├── Node.tsx       # Node component
│   │   ├── Edge.tsx       # Edge component (Bezier)
│   │   ├── Port.tsx       # Port component
│   │   ├── Palette.tsx    # Node palette sidebar
│   │   ├── Properties.tsx # Properties panel
│   │   ├── Minimap.tsx    # Minimap
│   │   ├── NLInput.tsx    # NL input box
│   │   └── Toolbar.tsx    # Top toolbar
│   ├── hooks/
│   │   ├── useViewport.ts
│   │   ├── useSelection.ts
│   │   └── useConnection.ts
│   └── api/
│       └── python.ts      # WebSocket to Python backend
├── vite.config.ts
└── index.html
```

### 6.2 Python ↔ Web Communication

**WebSocket protocol:**
```json
// Python → Web
{ "type": "graph_update", "graph": { "nodes": [...], "edges": [...] } }
{ "type": "execution_state", "node_id": "n1", "status": "running", "value": 42 }
{ "type": "type_error", "edge_id": "e1", "message": "Type mismatch: Int → String" }

// Web → Python
{ "type": "create_node", "kind": "ARITHMETIC", "position": { "x": 100, "y": 200 } }
{ "type": "connect", "source": { "node": "n1", "port": "result" }, "target": { "node": "n2", "port": "arg0" } }
{ "type": "execute", "entry": "main", "args": [] }
{ "type": "nl_input", "text": "define function add taking two integers" }
```

### 6.3 Development
```bash
cd /home/jayson/OREO/IDE/visual_editor/web
npm install
npm run dev  # Starts Vite dev server on :5173
```

---

## 7. Live Execution Visualization

### 7.1 Token Highlighting
- Values flow through edges in real-time
- Animated particles on DATA edges
- Color-coded by type (blue=Int, green=Bool, orange=String, etc.)

### 7.2 Heat Map
- Execution frequency per node
- Hot paths highlighted in red
- Cold paths in blue

### 7.3 Time Travel
- Execution history recorded
- Scrubber to replay execution
- Step forward/backward

### 7.4 Diff View
- Compare two graph versions
- Added nodes (green), removed (red), modified (yellow)
- Side-by-side or overlay

---

## 8. Properties Panel

When a node is selected, the properties panel shows:

| Section | Content |
|---------|---------|
| **Identity** | Node ID, kind, name |
| **Ports** | List of ports with types, connections |
| **Properties** | Key-value properties (editable) |
| **Type** | Inferred type, effect row |
| **Contracts** | Pre/post conditions, invariants |
| **Source** | Original NL text, file location |
| **Execution** | Last value, execution count, timing |

---

## 9. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `/home/jayson/OREO/IDE/visual_editor/canvas/renderer.py` | 721 | Canvas rendering engine |
| `/home/jayson/OREO/IDE/visual_editor/interaction/tools.py` | ~1700 | Interaction handling |
| `/home/jayson/OREO/IDE/visual_editor/nodes/node_registry.py` | ~1600 | Node palette registry |
| `/home/jayson/OREO/IDE/visual_editor/architecture.py` | ~500 | GraphLang bridge |
| `/home/jayson/OREO/IDE/parser/architecture/visual.py` | ~1900 | Talk+draw web editor |
| `/home/jayson/OREO/IDE/visual_editor/web/` | — | React frontend |

---

## 10. Usage Examples

### 10.1 Create a Function Graph Visually
1. Open visual editor: `cargo run --bin oreo-editor` (or web frontend)
2. From **Module** category, drag **FUNCTION** node
3. Set name: `add`, params: `a: Int`, `b: Int`, return: `Int`
4. From **Operation**, drag **ARITHMETIC** node, set op: `ADD`
5. Connect: `a` output → `ARITHMETIC.lhs`, `b` output → `ARITHMETIC.rhs`
6. Connect: `ARITHMETIC.result` → function `return` port
7. Press **Execute** → see result

### 10.2 Architecture Modeling (GraphLang)
1. Launch: `python3 -m parser.architecture.visual`
2. **Talk**: Type "create a landing page at /"
3. **Talk**: Type "add a postgres database called MainDB"
4. **Talk**: Type "create a secure JWT auth"
5. **Talk**: Type "connect the db to the landing page with a secure auth"
6. **Draw**: See pages, databases, auth as nodes; handshake as edges
7. **Emit**: Click "Emit App" → generates runnable web app
8. **Test**: Click "Hit Routes" → verifies handshake enforcement

### 10.3 NL Input in Visual Editor
1. Press `/` to focus NL input box
2. Type: "define function factorial taking integer n returning integer"
3. Press Enter → graph appears on canvas
4. Edit visually, or continue with more NL

---

## 11. Extending the Visual Editor

### 11.1 Adding Custom Node Types
```python
# In node_registry.py
registry.register(NodeTemplate(
    kind=NodeKind.CUSTOM_OP,
    name="Custom Op",
    description="My custom operation",
    category=NodeCategory.OPERATION,
    default_ports=[
        Port("input", TypeRef("Int"), is_input=True),
        Port("output", TypeRef("Int"), is_input=False),
    ],
    icon="🔧",
    search_tags=["custom", "op"],
))
```

### 11.2 Custom Renderers
```python
# Extend NodeRenderer
class CustomNodeRenderer(NodeRenderer):
    def render(self, ctx: RenderContext, node: Node):
        # Custom drawing logic
        pass
```

---

*Generated from OREO source code — see `/home/jayson/OREO/IDE/visual_editor/` and `/home/jayson/OREO/IDE/parser/architecture/` for implementation.*