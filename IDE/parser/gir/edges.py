"""
GIR (Graph Intermediate Representation) - Edge Definitions
Edge types and graph structure for the OREO language.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from uuid import uuid4


class EdgeKind(Enum):
    """Categories of edges in the GIR."""
    # Data flow - values flowing between nodes
    DATA = "data"
    
    # Control flow - execution order
    CONTROL = "control"
    
    # Dependencies - compile-time relationships
    DEPENDENCY = "dependency"
    
    # Composition - structural containment (parent/child)
    COMPOSITION = "composition"
    
    # Annotations - metadata attachments
    ANNOTATION = "annotation"
    
    # Type relationships
    TYPE_OF = "type_of"
    SUBTYPE_OF = "subtype_of"
    IMPLEMENTS = "implements"
    
    # Scope/binding relationships
    DEFINES = "defines"
    USES = "uses"
    CAPTURES = "captures"
    
    # Effect relationships
    HAS_EFFECT = "has_effect"
    HANDLES_EFFECT = "handles_effect"
    
    # Contract relationships
    REQUIRES = "requires"  # precondition
    ENSURES = "ensures"    # postcondition
    INVARIANT = "invariant"


@dataclass
class Edge:
    """Base edge in the GIR."""
    source: str  # source node ID
    target: str  # target node ID
    # kind is defaulted so concrete subclasses (which set their own kind in
    # __post_init__) can be constructed without passing it.
    kind: EdgeKind = EdgeKind.DATA
    source_port: str = ""  # output port name on source
    target_port: str = ""  # input port name on target
    id: str = field(default_factory=lambda: str(uuid4()))
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.id == other.id


@dataclass
class DataEdge(Edge):
    """Value flows from source output to target input."""
    value_type: Optional[str] = None  # type of data flowing
    
    def __post_init__(self):
        self.kind = EdgeKind.DATA


@dataclass
class ControlEdge(Edge):
    """Execution flows from source to target."""
    is_conditional: bool = False
    condition_port: str = ""  # port name for condition if conditional
    
    def __post_init__(self):
        self.kind = EdgeKind.CONTROL


@dataclass
class DependencyEdge(Edge):
    """Compile-time dependency (e.g., module imports, type dependencies)."""
    dependency_kind: str = ""  # import, type_dep, const_dep
    
    def __post_init__(self):
        self.kind = EdgeKind.DEPENDENCY


@dataclass
class CompositionEdge(Edge):
    """Structural containment - parent contains child."""
    is_owning: bool = True  # parent owns child lifecycle
    
    def __post_init__(self):
        self.kind = EdgeKind.COMPOSITION


@dataclass
class AnnotationEdge(Edge):
    """Metadata attachment."""
    annotation_key: str = ""
    annotation_value: Any = None
    
    def __post_init__(self):
        self.kind = EdgeKind.ANNOTATION


@dataclass
class TypeEdge(Edge):
    """Type relationship."""
    type_relationship: str = ""  # type_of, subtype_of, implements
    
    def __post_init__(self):
        self.kind = EdgeKind.TYPE_OF


@dataclass
class ScopeEdge(Edge):
    """Scope/binding relationship."""
    scope_kind: str = ""  # defines, uses, captures
    
    def __post_init__(self):
        self.kind = EdgeKind.DEFINES


@dataclass
class EffectEdge(Edge):
    """Effect relationship."""
    effect_kind: str = ""  # has_effect, handles_effect
    effect_name: str = ""
    
    def __post_init__(self):
        self.kind = EdgeKind.HAS_EFFECT


@dataclass
class ContractEdge(Edge):
    """Contract relationship."""
    contract_kind: str = ""  # requires, ensures, invariant
    
    def __post_init__(self):
        self.kind = EdgeKind.REQUIRES


# --- Graph Structure ---

@dataclass
class Graph:
    """A GIR graph - collection of nodes and edges."""
    nodes: Dict[str, 'Node'] = field(default_factory=dict)  # node_id -> Node
    edges: List[Edge] = field(default_factory=list)
    name: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    # For hierarchical graphs
    parent_graph: Optional['Graph'] = None
    subgraphs: Dict[str, 'Graph'] = field(default_factory=dict)
    
    def add_node(self, node: 'Node') -> 'Node':
        """Add a node to the graph."""
        self.nodes[node.id] = node
        return node
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its edges."""
        if node_id not in self.nodes:
            return False
        # Remove edges connected to this node
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        del self.nodes[node_id]
        return True
    
    def get_node(self, node_id: str) -> Optional['Node']:
        return self.nodes.get(node_id)
    
    def add_edge(self, edge: Edge) -> Edge:
        """Add an edge to the graph."""
        # Verify nodes exist
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge references non-existent node: {edge.source} -> {edge.target}")
        self.edges.append(edge)
        return edge
    
    def remove_edge(self, edge_id: str) -> bool:
        for i, e in enumerate(self.edges):
            if e.id == edge_id:
                self.edges.pop(i)
                return True
        return False
    
    def get_edges_from(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source == node_id]
    
    def get_edges_to(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target == node_id]
    
    def get_data_edges_from(self, node_id: str) -> List[DataEdge]:
        return [e for e in self.edges if e.source == node_id and e.kind == EdgeKind.DATA]
    
    def get_data_edges_to(self, node_id: str) -> List[DataEdge]:
        return [e for e in self.edges if e.target == node_id and e.kind == EdgeKind.DATA]
    
    def get_control_edges_from(self, node_id: str) -> List[ControlEdge]:
        return [e for e in self.edges if e.source == node_id and e.kind == EdgeKind.CONTROL]
    
    def get_control_edges_to(self, node_id: str) -> List[ControlEdge]:
        return [e for e in self.edges if e.target == node_id and e.kind == EdgeKind.CONTROL]
    
    def get_children(self, node_id: str) -> List['Node']:
        """Get child nodes via composition edges."""
        child_edges = [e for e in self.edges 
                      if e.source == node_id and e.kind == EdgeKind.COMPOSITION]
        return [self.nodes[e.target] for e in child_edges if e.target in self.nodes]
    
    def get_parent(self, node_id: str) -> Optional['Node']:
        """Get parent node via composition edge."""
        parent_edges = [e for e in self.edges 
                       if e.target == node_id and e.kind == EdgeKind.COMPOSITION]
        if parent_edges:
            return self.nodes.get(parent_edges[0].source)
        return None
    
    def topological_sort(self) -> List[str]:
        """Return node IDs in topological order (data flow)."""
        # Kahn's algorithm
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            if edge.kind == EdgeKind.DATA:
                in_degree[edge.target] += 1
        
        queue = [node_id for node_id, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for edge in self.get_data_edges_from(node_id):
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0:
                    queue.append(edge.target)
        
        if len(result) != len(self.nodes):
            # Cycle detected - return partial order
            pass
        
        return result
    
    def validate(self) -> List[str]:
        """Validate graph structure, return list of errors."""
        errors = []
        
        # Check all edges reference valid nodes
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge {edge.id}: source node {edge.source} not found")
            if edge.target not in self.nodes:
                errors.append(f"Edge {edge.id}: target node {edge.target} not found")
        
        # Check for cycles in data flow
        try:
            self.topological_sort()
        except Exception as e:
            errors.append(f"Data flow cycle detected: {e}")
        
        # Check port compatibility on data edges
        for edge in self.edges:
            if edge.kind == EdgeKind.DATA:
                source_node = self.nodes.get(edge.source)
                target_node = self.nodes.get(edge.target)
                if source_node and target_node:
                    source_port = source_node.ports.get(edge.source_port)
                    target_port = target_node.ports.get(edge.target_port)
                    if source_port and target_port:
                        if source_port.type and target_port.type:
                            # TODO: implement type compatibility check
                            pass
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "nodes": {nid: node_to_dict(node) for nid, node in self.nodes.items()},
            "edges": [edge_to_dict(e) for e in self.edges],
            "subgraphs": {name: sg.to_dict() for name, sg in self.subgraphs.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Graph':
        """Deserialize graph from dictionary."""
        graph = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )
        
        # Load nodes
        for nid, ndata in data.get("nodes", {}).items():
            node = dict_to_node(ndata)
            graph.nodes[nid] = node
        
        # Load edges
        for edata in data.get("edges", []):
            edge = dict_to_edge(edata)
            graph.edges.append(edge)
        
        # Load subgraphs
        for name, sgdata in data.get("subgraphs", {}).items():
            graph.subgraphs[name] = cls.from_dict(sgdata)
            graph.subgraphs[name].parent_graph = graph
        
        return graph


# Need to import Node from nodes module
from .nodes import Node, node_to_dict, dict_to_node


def edge_to_dict(edge: Edge) -> Dict[str, Any]:
    """Serialize edge to dictionary."""
    result = {
        "id": edge.id,
        "kind": edge.kind.value,
        "source": edge.source,
        "target": edge.target,
        "source_port": edge.source_port,
        "target_port": edge.target_port,
        "properties": edge.properties,
        "metadata": edge.metadata,
    }
    
    if isinstance(edge, DataEdge):
        result["value_type"] = edge.value_type
    elif isinstance(edge, ControlEdge):
        result["is_conditional"] = edge.is_conditional
        result["condition_port"] = edge.condition_port
    elif isinstance(edge, DependencyEdge):
        result["dependency_kind"] = edge.dependency_kind
    elif isinstance(edge, CompositionEdge):
        result["is_owning"] = edge.is_owning
    elif isinstance(edge, AnnotationEdge):
        result["annotation_key"] = edge.annotation_key
        result["annotation_value"] = edge.annotation_value
    elif isinstance(edge, TypeEdge):
        result["type_relationship"] = edge.type_relationship
    elif isinstance(edge, ScopeEdge):
        result["scope_kind"] = edge.scope_kind
    elif isinstance(edge, EffectEdge):
        result["effect_kind"] = edge.effect_kind
        result["effect_name"] = edge.effect_name
    elif isinstance(edge, ContractEdge):
        result["contract_kind"] = edge.contract_kind
    
    return result


def dict_to_edge(data: Dict[str, Any]) -> Edge:
    """Deserialize edge from dictionary."""
    kind = EdgeKind(data["kind"])
    
    if kind == EdgeKind.DATA:
        edge = DataEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            value_type=data.get("value_type")
        )
    elif kind == EdgeKind.CONTROL:
        edge = ControlEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            is_conditional=data.get("is_conditional", False),
            condition_port=data.get("condition_port", "")
        )
    elif kind == EdgeKind.DEPENDENCY:
        edge = DependencyEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            dependency_kind=data.get("dependency_kind", "")
        )
    elif kind == EdgeKind.COMPOSITION:
        edge = CompositionEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            is_owning=data.get("is_owning", True)
        )
    elif kind == EdgeKind.ANNOTATION:
        edge = AnnotationEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            annotation_key=data.get("annotation_key", ""),
            annotation_value=data.get("annotation_value")
        )
    elif kind == EdgeKind.TYPE_OF:
        edge = TypeEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            type_relationship=data.get("type_relationship", "type_of")
        )
    elif kind == EdgeKind.DEFINES:
        edge = ScopeEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            scope_kind=data.get("scope_kind", "defines")
        )
    elif kind == EdgeKind.HAS_EFFECT:
        edge = EffectEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            effect_kind=data.get("effect_kind", "has_effect"),
            effect_name=data.get("effect_name", "")
        )
    elif kind == EdgeKind.REQUIRES:
        edge = ContractEdge(
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", ""),
            contract_kind=data.get("contract_kind", "requires")
        )
    else:
        edge = Edge(
            kind=kind,
            source=data["source"],
            target=data["target"],
            source_port=data.get("source_port", ""),
            target_port=data.get("target_port", "")
        )
    
    edge.id = data.get("id", str(uuid4()))
    edge.properties = data.get("properties", {})
    edge.metadata = data.get("metadata", {})
    
    return edge


# --- Helper Functions ---

def connect_data(graph: Graph, source_node: Node, source_port: str, 
                 target_node: Node, target_port: str) -> DataEdge:
    """Create a data flow edge between two nodes."""
    edge = DataEdge(
        source=source_node.id,
        target=target_node.id,
        source_port=source_port,
        target_port=target_port,
    )
    return graph.add_edge(edge)


def connect_control(graph: Graph, source_node: Node, target_node: Node,
                   source_port: str = "", target_port: str = "") -> ControlEdge:
    """Create a control flow edge between two nodes."""
    edge = ControlEdge(
        source=source_node.id,
        target=target_node.id,
        source_port=source_port,
        target_port=target_port,
    )
    return graph.add_edge(edge)


def connect_composition(graph: Graph, parent_node: Node, child_node: Node) -> CompositionEdge:
    """Create a composition (parent-child) edge."""
    edge = CompositionEdge(
        source=parent_node.id,
        target=child_node.id,
        is_owning=True,
    )
    return graph.add_edge(edge)


def annotate(graph: Graph, source_node: Node, target_node: Node,
             key: str, value: Any) -> AnnotationEdge:
    """Attach metadata annotation."""
    edge = AnnotationEdge(
        source=source_node.id,
        target=target_node.id,
        annotation_key=key,
        annotation_value=value,
    )
    return graph.add_edge(edge)


def set_type(graph: Graph, node: Node, type_node: Node) -> TypeEdge:
    """Set the type of a node."""
    edge = TypeEdge(
        source=node.id,
        target=type_node.id,
        type_relationship="type_of",
    )
    return graph.add_edge(edge)


def add_effect(graph: Graph, node: Node, effect_node: Node) -> EffectEdge:
    """Add an effect to a node."""
    edge = EffectEdge(
        source=node.id,
        target=effect_node.id,
        effect_kind="has_effect",
        effect_name=effect_node.name if hasattr(effect_node, 'name') else str(effect_node.id),
    )
    return graph.add_edge(edge)


def add_contract(graph: Graph, node: Node, contract_node: Node, 
                 contract_kind: str = "requires") -> ContractEdge:
    """Add a contract (pre/post/invariant) to a node."""
    edge = ContractEdge(
        source=node.id,
        target=contract_node.id,
        contract_kind=contract_kind,
    )
    return graph.add_edge(edge)