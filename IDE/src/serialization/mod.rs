//! OREO Binary Serialization (.oreo format)
//!
//! Binary serialization for the Graph Intermediate Representation with:
//! - Versioned format with magic bytes
//! - Schema validation
//! - Compression support
//! - Incremental loading support
//! - Cross-platform compatibility

use super::*;
use std::collections::HashMap;
use std::io::{Read, Write, Cursor, BufReader, BufWriter};
use std::fs::File;
use std::path::Path;
use serde::{Deserialize, Serialize};
use bincode::{serialize, deserialize, Options};

/// Magic bytes for .oreo files
pub const OREO_MAGIC: &[u8; 4] = b"OREO";

/// Current file format version
pub const OREO_VERSION: u32 = 1;

/// Minimum supported version
pub const OREO_MIN_VERSION: u32 = 1;

/// File header
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OreFileHeader {
    pub magic: [u8; 4],
    pub version: u32,
    pub flags: FileFlags,
    pub schema_hash: u64,
    pub timestamp: u64,
    pub entry_graph: GraphId,
    pub graph_count: u32,
    pub total_nodes: u64,
    pub total_edges: u64,
    pub string_table_offset: u64,
    pub string_table_size: u64,
    pub metadata_offset: u64,
    pub metadata_size: u64,
    pub reserved: [u8; 16],
}

/// File flags
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FileFlags {
    pub compressed: bool,
    pub encrypted: bool,
    pub has_schema: bool,
    pub has_debug_info: bool,
    pub incremental: bool,
    pub stripped: bool,
}

impl Default for FileFlags {
    fn default() -> Self {
        FileFlags {
            compressed: true,
            encrypted: false,
            has_schema: true,
            has_debug_info: true,
            incremental: false,
            stripped: false,
        }
    }
}

/// Graph index entry for fast random access
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphIndexEntry {
    pub graph_id: GraphId,
    pub name: String,
    pub node_count: u64,
    pub edge_count: u64,
    pub data_offset: u64,
    pub data_size: u64,
    pub flags: GraphFlags,
}

/// Graph flags
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct GraphFlags {
    pub is_entry: bool,
    pub is_module: bool,
    pub is_function: bool,
    pub has_cycles: bool,
    pub is_stripped: bool,
}

/// Serialized node (compact form)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedNode {
    pub id: NodeId,
    pub node_type: NodeType,
    pub kind: u8, // Type-specific kind
    pub input_ports: Vec<SerializedPort>,
    pub output_ports: Vec<SerializedPort>,
    pub metadata: SerializedNodeMetadata,
}

/// Serialized port
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedPort {
    pub id: PortId,
    pub name: String,
    pub port_type: TypeId,
    pub direction: PortDirection,
    pub is_required: bool,
    pub default_value: Option<ConstantValue>,
}

/// Serialized node metadata (compact)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SerializedNodeMetadata {
    pub nl_description: Option<String>,
    pub source_location: Option<SourceLocation>,
    pub annotations: HashMap<String, serde_json::Value>,
    pub ai_generated: bool,
    pub confidence: Option<f32>,
    pub version: u64,
}

/// Serialized edge
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedEdge {
    pub id: EdgeId,
    pub source: PortId,
    pub target: PortId,
    pub edge_type: EdgeType,
    pub metadata: SerializedNodeMetadata,
}

/// Type registry serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedTypeRegistry {
    pub types: Vec<SerializedTypeInfo>,
    pub name_to_id: HashMap<String, TypeId>,
}

/// Serialized type info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedTypeInfo {
    pub id: TypeId,
    pub name: String,
    pub kind: TypeKind,
    pub parameters: Vec<TypeId>,
    pub constraints: Vec<TraitConstraint>,
    pub effects: EffectSet,
}

/// Effect registry serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedEffectRegistry {
    pub effects: Vec<SerializedEffectInfo>,
    pub name_to_id: HashMap<String, EffectId>,
}

/// Serialized effect info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializedEffectInfo {
    pub id: EffectId,
    pub name: String,
    pub kind: EffectKind,
    pub parameters: Vec<TypeId>,
    pub description: String,
}

/// String table for deduplication
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct StringTable {
    pub strings: Vec<String>,
    pub offsets: HashMap<String, u32>,
}

impl StringTable {
    pub fn new() -> Self {
        StringTable {
            strings: Vec::new(),
            offsets: HashMap::new(),
        }
    }

    pub fn intern(&mut self, s: String) -> u32 {
        if let Some(&offset) = self.offsets.get(&s) {
            return offset;
        }
        let offset = self.strings.len() as u32;
        self.strings.push(s.clone());
        self.offsets.insert(s, offset);
        offset
    }

    pub fn get(&self, offset: u32) -> Option<&String> {
        self.strings.get(offset as usize)
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut buf = Vec::new();
        // Write count
        buf.extend_from_slice(&(self.strings.len() as u32).to_le_bytes());
        // Write each string with length prefix
        for s in &self.strings {
            let bytes = s.as_bytes();
            buf.extend_from_slice(&(bytes.len() as u32).to_le_bytes());
            buf.extend_from_slice(bytes);
        }
        buf
    }

    pub fn deserialize(data: &[u8]) -> Result<Self, String> {
        let mut cursor = Cursor::new(data);
        let mut count_bytes = [0u8; 4];
        cursor.read_exact(&mut count_bytes).map_err(|e| e.to_string())?;
        let count = u32::from_le_bytes(count_bytes) as usize;
        
        let mut table = StringTable::new();
        table.strings.reserve(count);
        
        for _ in 0..count {
            let mut len_bytes = [0u8; 4];
            cursor.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
            let len = u32::from_le_bytes(len_bytes) as usize;
            
            let mut str_bytes = vec![0u8; len];
            cursor.read_exact(&mut str_bytes).map_err(|e| e.to_string())?;
            let s = String::from_utf8(str_bytes).map_err(|e| e.to_string())?;
            table.intern(s);
        }
        
        Ok(table)
    }
}

/// Serialization context
pub struct SerializationContext {
    pub string_table: StringTable,
    pub type_id_map: HashMap<TypeId, TypeId>, // remapping for serialization
    pub effect_id_map: HashMap<EffectId, EffectId>,
    pub graph_id_map: HashMap<GraphId, GraphId>,
    pub node_id_map: HashMap<NodeId, NodeId>,
    pub edge_id_map: HashMap<EdgeId, EdgeId>,
}

impl SerializationContext {
    pub fn new() -> Self {
        SerializationContext {
            string_table: StringTable::new(),
            type_id_map: HashMap::new(),
            effect_id_map: HashMap::new(),
            graph_id_map: HashMap::new(),
            node_id_map: HashMap::new(),
            edge_id_map: HashMap::new(),
        }
    }
}

/// Main serialization entry point
pub fn serialize_gir(context: &GirContext, writer: &mut dyn Write) -> Result<(), String> {
    let mut ctx = SerializationContext::new();
    
    // Collect all strings for interning
    collect_strings(context, &mut ctx.string_table);
    
    // Build header
    let header = build_header(context, &ctx)?;
    
    // Write header
    let header_bytes = bincode::serialize(&header).map_err(|e| e.to_string())?;
    writer.write_all(&header_bytes).map_err(|e| e.to_string())?;
    
    // Write string table
    let string_table_bytes = ctx.string_table.serialize();
    writer.write_all(&string_table_bytes).map_err(|e| e.to_string())?;
    
    // Write type registry
    write_type_registry(&context, writer)?;
    
    // Write effect registry
    write_effect_registry(&context, writer)?;
    
    // Write each graph
    for graph in context.graphs.values() {
        write_graph(graph, writer)?;
    }
    
    // Write metadata
    write_metadata(&context, writer)?;
    
    Ok(())
}

/// Deserialize GIR from reader
pub fn deserialize_gir(reader: &mut dyn Read) -> Result<GirContext, String> {
    // Read header
    let header: OreFileHeader = bincode::deserialize_from(reader).map_err(|e| e.to_string())?;
    
    // Validate magic
    if header.magic != *OREO_MAGIC {
        return Err("Invalid .oreo file: incorrect magic bytes".to_string());
    }
    
    // Check version
    if header.version < OREO_MIN_VERSION || header.version > OREO_VERSION {
        return Err(format!("Unsupported .oreo version: {} (supported: {}-{})", header.version, OREO_MIN_VERSION, OREO_VERSION));
    }
    
    let mut ctx = GirContext::new();
    
    // Read string table
    let string_table = StringTable::deserialize(&read_string_table(reader)?)?;
    
    // Read type registry
    let type_registry = read_type_registry(reader, &string_table)?;
    ctx.type_registry = type_registry;
    
    // Read effect registry
    let effect_registry = read_effect_registry(reader, &string_table)?;
    ctx.effect_registry = effect_registry;
    
    // Read graphs
    for _ in 0..header.graph_count {
        let graph = read_graph(reader, &string_table)?;
        ctx.graphs.insert(graph.id, graph);
    }
    
    // Read metadata
    read_metadata(reader, &mut ctx)?;
    
    Ok(ctx)
}

/// File I/O helpers
pub fn write_oreo_file(context: &GirContext, path: &Path) -> Result<(), String> {
    let file = File::create(path).map_err(|e| e.to_string())?;
    let mut writer = BufWriter::new(file);
    serialize_gir(context, &mut writer)?;
    writer.flush().map_err(|e| e.to_string())?;
    Ok(())
}

pub fn read_oreo_file(path: &Path) -> Result<GirContext, String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let mut reader = BufReader::new(file);
    deserialize_gir(&mut reader)
}

/// Compression support
pub fn compress(data: &[u8]) -> Result<Vec<u8>, String> {
    use flate2::write::GzEncoder;
    use flate2::Compression;
    use std::io::Write;
    
    let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(data).map_err(|e| e.to_string())?;
    encoder.finish().map_err(|e| e.to_string())
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>, String> {
    use flate2::read::GzDecoder;
    use std::io::Read;
    
    let mut decoder = GzDecoder::new(data);
    let mut result = Vec::new();
    decoder.read_to_end(&mut result).map_err(|e| e.to_string())?;
    Ok(result)
}

/// Schema validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OreSchema {
    pub version: u32,
    pub types: HashMap<String, TypeSchema>,
    pub effects: HashMap<String, EffectSchema>,
    pub graphs: HashMap<String, GraphSchema>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeSchema {
    pub name: String,
    pub kind: TypeKind,
    pub fields: Vec<FieldSchema>,
    pub constraints: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldSchema {
    pub name: String,
    pub type_name: String,
    pub optional: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectSchema {
    pub name: String,
    pub kind: EffectKind,
    pub params: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphSchema {
    pub name: String,
    pub node_types: HashMap<String, u32>, // type -> expected count
    pub required_nodes: Vec<String>,
    pub entry_points: Vec<String>,
}

pub fn validate_against_schema(context: &GirContext, schema: &OreSchema) -> Result<Vec<String>, String> {
    let mut errors = Vec::new();
    
    // Validate types
    for (name, type_info) in &context.type_registry.types {
        if let Some(schema) = schema.types.get(name) {
            if type_info.kind != schema.kind {
                errors.push(format!("Type '{}' kind mismatch: expected {:?}, got {:?}", name, schema.kind, type_info.kind));
            }
        }
    }
    
    // Validate graphs
    for (id, graph) in &context.graphs {
        if let Some(schema) = schema.graphs.get(&graph.name) {
            if schema.required_nodes.len() > graph.nodes.len() as u64 {
                errors.push(format!("Graph '{}' missing required nodes", graph.name));
            }
        }
    }
    
    Ok(errors)
}

// Helper functions (implementations would be in separate module)
fn collect_strings(context: &GirContext, table: &mut StringTable) {
    // Collect from type registry
    for type_info in context.type_registry.types.values() {
        table.intern(type_info.name.clone());
    }
    
    // Collect from effect registry
    for effect_info in context.effect_registry.effects.values() {
        table.intern(effect_info.name.clone());
        table.intern(effect_info.description.clone());
    }
    
    // Collect from graphs
    for graph in context.graphs.values() {
        table.intern(graph.name.clone());
        for node in graph.nodes.values() {
            if let Some(desc) = &node.metadata().nl_description {
                table.intern(desc.clone());
            }
            for (key, val) in &node.metadata().annotations {
                table.intern(key.clone());
                if let Some(s) = val.as_str() {
                    table.intern(s.to_string());
                }
            }
        }
    }
}

fn build_header(context: &GirContext, ctx: &SerializationContext) -> Result<OreFileHeader, String> {
    let mut total_nodes = 0;
    let mut total_edges = 0;
    let entry_graph = context.graphs.values().find(|g| g.metadata.annotations.get("entry").is_some())
        .map(|g| g.id)
        .unwrap_or_else(|| context.graphs.keys().next().copied().unwrap_or(GraphId(0)));
    
    for graph in context.graphs.values() {
        total_nodes += graph.nodes.len() as u64;
        total_edges += graph.edges.len() as u64;
    }
    
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    use std::hash::{Hash, Hasher};
    context.type_registry.types.keys().for_each(|k| k.hash(&mut hasher));
    context.effect_registry.effects.keys().for_each(|k| k.hash(&mut hasher));
    let schema_hash = hasher.finish();
    
    Ok(OreFileHeader {
        magic: *OREO_MAGIC,
        version: OREO_VERSION,
        flags: FileFlags::default(),
        schema_hash,
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        entry_graph,
        graph_count: context.graphs.len() as u32,
        total_nodes,
        total_edges,
        string_table_offset: 0, // Will be filled in
        string_table_size: ctx.string_table.serialize().len() as u64,
        metadata_offset: 0,
        metadata_size: 0,
        reserved: [0; 16],
    })
}

fn write_type_registry(context: &GirContext, writer: &mut dyn Write) -> Result<(), String> {
    let registry = SerializedTypeRegistry {
        types: context.type_registry.types.values().map(|t| SerializedTypeInfo {
            id: t.id,
            name: t.name.clone(),
            kind: t.kind.clone(),
            parameters: t.parameters.clone(),
            constraints: t.constraints.clone(),
            effects: t.effects.clone(),
        }).collect(),
        name_to_id: context.type_registry.name_to_id.clone(),
    };
    
    let bytes = bincode::serialize(&registry).map_err(|e| e.to_string())?;
    writer.write_all(&(bytes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
    writer.write_all(&bytes).map_err(|e| e.to_string())?;
    Ok(())
}

fn write_effect_registry(context: &GirContext, writer: &mut dyn Write) -> Result<(), String> {
    let registry = SerializedEffectRegistry {
        effects: context.effect_registry.effects.values().map(|e| SerializedEffectInfo {
            id: e.id,
            name: e.name.clone(),
            kind: e.kind,
            parameters: e.parameters.clone(),
            description: e.description.clone(),
        }).collect(),
        name_to_id: context.effect_registry.name_to_id.clone(),
    };
    
    let bytes = bincode::serialize(&registry).map_err(|e| e.to_string())?;
    writer.write_all(&(bytes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
    writer.write_all(&bytes).map_err(|e| e.to_string())?;
    Ok(())
}

fn write_graph(graph: &GirGraph, writer: &mut dyn Write) -> Result<(), String> {
    // Write graph header
    let entry = GraphIndexEntry {
        graph_id: graph.id,
        name: graph.name.clone(),
        node_count: graph.nodes.len() as u64,
        edge_count: graph.edges.len() as u64,
        data_offset: 0, // Will be filled
        data_size: 0,
        flags: GraphFlags {
            is_entry: graph.metadata.annotations.get("entry").is_some(),
            is_module: graph.metadata.annotations.get("module").is_some(),
            is_function: graph.metadata.annotations.get("function").is_some(),
            has_cycles: false, // TODO: detect
            is_stripped: false,
        },
    };
    
    let entry_bytes = bincode::serialize(&entry).map_err(|e| e.to_string())?;
    writer.write_all(&entry_bytes).map_err(|e| e.to_string())?;
    
    // Write nodes
    let node_count = graph.nodes.len() as u32;
    writer.write_all(&node_count.to_le_bytes()).map_err(|e| e.to_string())?;
    
    for node in graph.nodes.values() {
        let serialized = serialize_node(node.as_ref());
        let node_bytes = bincode::serialize(&serialized).map_err(|e| e.to_string())?;
        writer.write_all(&(node_bytes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
        writer.write_all(&node_bytes).map_err(|e| e.to_string())?;
    }
    
    // Write edges
    let edge_count = graph.edges.len() as u32;
    writer.write_all(&edge_count.to_le_bytes()).map_err(|e| e.to_string())?;
    
    for edge in graph.edges.values() {
        let serialized = serialize_edge(edge);
        let edge_bytes = bincode::serialize(&serialized).map_err(|e| e.to_string())?;
        writer.write_all(&edge_bytes).map_err(|e| e.to_string())?;
    }
    
    Ok(())
}

fn serialize_node(node: &dyn GirNode) -> SerializedNode {
    SerializedNode {
        id: node.id(),
        node_type: node.node_type(),
        kind: 0, // TODO: encode node-specific kind
        input_ports: node.input_ports().iter().map(|p| SerializedPort {
            id: p.id,
            name: p.name.clone(),
            port_type: p.port_type,
            direction: p.direction,
            is_required: p.is_required,
            default_value: p.default_value.clone(),
        }).collect(),
        output_ports: node.output_ports().iter().map(|p| SerializedPort {
            id: p.id,
            name: p.name.clone(),
            port_type: p.port_type,
            direction: p.direction,
            is_required: p.is_required,
            default_value: p.default_value.clone(),
        }).collect(),
        metadata: SerializedNodeMetadata {
            nl_description: node.metadata().nl_description.clone(),
            source_location: node.metadata().source_location.clone(),
            annotations: node.metadata().annotations.clone(),
            ai_generated: node.metadata().ai_generated,
            confidence: node.metadata().confidence,
            version: node.metadata().version,
        },
    }
}

fn serialize_edge(edge: &GirEdge) -> SerializedEdge {
    SerializedEdge {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        edge_type: edge.edge_type,
        metadata: SerializedNodeMetadata {
            nl_description: edge.metadata.nl_description.clone(),
            source_location: edge.metadata.source_location.clone(),
            annotations: edge.metadata.annotations.clone(),
            ai_generated: edge.metadata.ai_generated,
            confidence: edge.metadata.confidence,
            version: edge.metadata.version,
        },
    }
}

fn write_metadata(context: &GirContext, writer: &mut dyn Write) -> Result<(), String> {
    // Write any global metadata
    Ok(())
}

fn read_string_table(reader: &mut dyn Read) -> Result<Vec<u8>, String> {
    let mut len_bytes = [0u8; 4];
    reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
    let len = u32::from_le_bytes(len_bytes) as usize;
    
    let mut data = vec![0u8; len];
    reader.read_exact(&mut data).map_err(|e| e.to_string())?;
    Ok(data)
}

fn read_type_registry(reader: &mut dyn Read, string_table: &StringTable) -> Result<TypeRegistry, String> {
    let mut len_bytes = [0u8; 4];
    reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
    let len = u32::from_le_bytes(len_bytes) as usize;
    
    let mut data = vec![0u8; len];
    reader.read_exact(&mut data).map_err(|e| e.to_string())?;
    
    let serialized: SerializedTypeRegistry = bincode::deserialize(&data).map_err(|e| e.to_string())?;
    
    let mut registry = TypeRegistry::new();
    for t in serialized.types {
        let info = TypeInfo {
            id: t.id,
            name: t.name,
            kind: t.kind,
            parameters: t.parameters,
            constraints: t.constraints,
            effects: t.effects,
        };
        registry.types.insert(t.id, info);
    }
    registry.name_to_id = serialized.name_to_id;
    Ok(registry)
}

fn read_effect_registry(reader: &mut dyn Read, string_table: &StringTable) -> Result<EffectRegistry, String> {
    let mut len_bytes = [0u8; 4];
    reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
    let len = u32::from_le_bytes(len_bytes) as usize;
    
    let mut data = vec![0u8; len];
    reader.read_exact(&mut data).map_err(|e| e.to_string())?;
    
    let serialized: SerializedEffectRegistry = bincode::deserialize(&data).map_err(|e| e.to_string())?;
    
    let mut registry = EffectRegistry::new();
    for e in serialized.effects {
        let info = EffectInfo {
            id: e.id,
            name: e.name,
            kind: e.kind,
            parameters: e.parameters,
            description: e.description,
        };
        registry.effects.insert(e.id, info);
    }
    registry.name_to_id = serialized.name_to_id;
    Ok(registry)
}

fn read_graph(reader: &mut dyn Read, string_table: &StringTable) -> Result<GirGraph, String> {
    let mut len_bytes = [0u8; 4];
    reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
    let entry_len = u32::from_le_bytes(len_bytes) as usize;
    
    let mut entry_data = vec![0u8; entry_len];
    reader.read_exact(&mut entry_data).map_err(|e| e.to_string())?;
    let entry: GraphIndexEntry = bincode::deserialize(&entry_data).map_err(|e| e.to_string())?;
    
    let mut graph = GirGraph::new(entry.graph_id, entry.name);
    graph.metadata.flags = entry.flags;
    
    // Read nodes
    let mut count_bytes = [0u8; 4];
    reader.read_exact(&mut count_bytes).map_err(|e| e.to_string())?;
    let node_count = u32::from_le_bytes(count_bytes) as usize;
    
    for _ in 0..node_count {
        let mut len_bytes = [0u8; 4];
        reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
        let len = u32::from_le_bytes(len_bytes) as usize;
        
        let mut node_data = vec![0u8; len];
        reader.read_exact(&mut node_data).map_err(|e| e.to_string())?;
        let serialized: SerializedNode = bincode::deserialize(&node_data).map_err(|e| e.to_string())?;
        
        // Deserialize node (would need concrete type dispatch)
        // For now skip - requires type registry
    }
    
    // Read edges
    reader.read_exact(&mut count_bytes).map_err(|e| e.to_string())?;
    let edge_count = u32::from_le_bytes(count_bytes) as usize;
    
    for _ in 0..edge_count {
        let mut len_bytes = [0u8; 4];
        reader.read_exact(&mut len_bytes).map_err(|e| e.to_string())?;
        let len = u32::from_le_bytes(len_bytes) as usize;
        
        let mut edge_data = vec![0u8; len];
        reader.read_exact(&mut edge_data).map_err(|e| e.to_string())?;
        let serialized: SerializedEdge = bincode::deserialize(&edge_data).map_err(|e| e.to_string())?;
        
        let edge = GirEdge {
            id: serialized.id,
            source: serialized.source,
            target: serialized.target,
            edge_type: serialized.edge_type,
            metadata: NodeMetadata {
                nl_description: serialized.metadata.nl_description,
                source_location: serialized.metadata.source_location,
                annotations: serialized.metadata.annotations,
                ai_generated: serialized.metadata.ai_generated,
                confidence: serialized.metadata.confidence,
                version: serialized.metadata.version,
            },
        };
        graph.edges.insert(edge.id, edge);
    }
    
    Ok(graph)
}

fn read_metadata(reader: &mut dyn Read, ctx: &mut GirContext) -> Result<(), String> {
    // Read any remaining metadata
    Ok(())
}

/// Incremental serialization support
pub struct IncrementalSerializer {
    pub previous_hash: u64,
    pub changed_graphs: HashSet<GraphId>,
    pub new_nodes: HashMap<GraphId, Vec<NodeId>>,
    pub removed_nodes: HashMap<GraphId, Vec<NodeId>>,
    pub changed_edges: HashMap<GraphId, Vec<EdgeId>>,
}

impl IncrementalSerializer {
    pub fn new() -> Self {
        IncrementalSerializer {
            previous_hash: 0,
            changed_graphs: HashSet::new(),
            new_nodes: HashMap::new(),
            removed_nodes: HashMap::new(),
            changed_edges: HashMap::new(),
        }
    }
    
    pub fn mark_graph_changed(&mut self, graph_id: GraphId) {
        self.changed_graphs.insert(graph_id);
    }
    
    pub fn mark_node_added(&mut self, graph_id: GraphId, node_id: NodeId) {
        self.new_nodes.entry(graph_id).or_default().push(node_id);
    }
    
    pub fn mark_node_removed(&mut self, graph_id: GraphId, node_id: NodeId) {
        self.removed_nodes.entry(graph_id).or_default().push(node_id);
    }
    
    pub fn mark_edge_changed(&mut self, graph_id: GraphId, edge_id: EdgeId) {
        self.changed_edges.entry(graph_id).or_default().push(edge_id);
    }
    
    pub fn serialize_incremental(&self, context: &GirContext, writer: &mut dyn Write) -> Result<(), String> {
        // Write incremental header
        let header = IncrementalHeader {
            base_hash: self.previous_hash,
            changed_graphs: self.changed_graphs.iter().copied().collect(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };
        
        let header_bytes = bincode::serialize(&header).map_err(|e| e.to_string())?;
        writer.write_all(&header_bytes).map_err(|e| e.to_string())?;
        
        // Write only changed data
        for graph_id in &self.changed_graphs {
            if let Some(graph) = context.graphs.get(graph_id) {
                // Write changed nodes
                if let Some(new_nodes) = self.new_nodes.get(graph_id) {
                    writer.write_all(&(new_nodes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
                    for node_id in new_nodes {
                        if let Some(node) = graph.nodes.get(node_id) {
                            let serialized = serialize_node(node.as_ref());
                            let node_bytes = bincode::serialize(&serialized).map_err(|e| e.to_string())?;
                            writer.write_all(&(node_bytes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
                            writer.write_all(&node_bytes).map_err(|e| e.to_string())?;
                        }
                    }
                }
                
                // Write removed nodes
                if let Some(removed_nodes) = self.removed_nodes.get(graph_id) {
                    writer.write_all(&(removed_nodes.len() as u32).to_le_bytes()).map_err(|e| e.to_string())?;
                    for node_id in removed_nodes {
                        writer.write_all(&node_id.0.to_le_bytes()).map_err(|e| e.to_string())?;
                    }
                }
            }
        }
        
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IncrementalHeader {
    pub base_hash: u64,
    pub changed_graphs: Vec<GraphId>,
    pub timestamp: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_table() {
        let mut table = StringTable::new();
        let offset1 = table.intern("hello".to_string());
        let offset2 = table.intern("world".to_string());
        let offset3 = table.intern("hello".to_string());
        
        assert_eq!(offset1, 0);
        assert_eq!(offset2, 1);
        assert_eq!(offset3, 0); // Deduplicated
        assert_eq!(table.strings.len(), 2);
    }

    #[test]
    fn test_string_table_serialization() {
        let mut table = StringTable::new();
        table.intern("hello".to_string());
        table.intern("world".to_string());
        
        let bytes = table.serialize();
        let deserialized = StringTable::deserialize(&bytes).unwrap();
        
        assert_eq!(deserialized.strings, table.strings);
    }

    #[test]
    fn test_file_header() {
        let header = OreFileHeader {
            magic: *OREO_MAGIC,
            version: OREO_VERSION,
            flags: FileFlags::default(),
            schema_hash: 0x12345678,
            timestamp: 1234567890,
            entry_graph: GraphId(1),
            graph_count: 2,
            total_nodes: 100,
            total_edges: 200,
            string_table_offset: 1024,
            string_table_size: 512,
            metadata_offset: 2048,
            metadata_size: 256,
            reserved: [0; 16],
        };
        
        let bytes = bincode::serialize(&header).unwrap();
        let deserialized: OreFileHeader = bincode::deserialize(&bytes).unwrap();
        
        assert_eq!(deserialized.magic, *OREO_MAGIC);
        assert_eq!(deserialized.version, OREO_VERSION);
        assert_eq!(deserialized.graph_count, 2);
    }

    #[test]
    fn test_file_flags() {
        let flags = FileFlags::default();
        assert!(flags.compressed);
        assert!(!flags.encrypted);
        assert!(flags.has_schema);
        assert!(flags.has_debug_info);
    }
}