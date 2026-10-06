# OREO Runtime & Compiler

> Documentation for the graph interpreter, effect system, memory model, and compiler backends.

---

## 1. Runtime Semantics

### 1.1 Evaluation Model

- **Graph reduction** — nodes fire when all inputs ready
- **Parallel by default** — independent nodes execute concurrently
- **Deterministic** — same graph + same inputs = same outputs
- **Incremental** — only re-evaluate changed subgraph

### 1.2 Execution Algorithm (Worklist)

```python
class GraphInterpreter:
    """Reference interpreter for GIR graphs."""
    
    def execute(self, graph: Graph, entry_function: str, args: List[Value]) -> Value:
        # 1. Build dependency graph from DATA edges
        # 2. Initialize worklist with entry function node
        # 3. While worklist not empty:
        #    a. Pop ready node (all input ports satisfied)
        #    b. Execute node → produce output values
        #    c. Propagate values to connected target ports
        #    d. Add newly-ready nodes to worklist
        # 4. Return value at entry function's return port
```

**Readiness condition:** A node is ready when all its required input ports have values.

### 1.3 Node Execution Semantics

| Node Kind | Execution |
|-----------|-----------|
| `LITERAL` | Push constant value to output port |
| `VARIABLE` | Read/write from/to environment |
| `PARAMETER` | Bind argument value |
| `ARITHMETIC` | Compute op(lhs, rhs) |
| `LOGIC` | Compute op(lhs, rhs) |
| `COMPARISON` | Compute op(lhs, rhs) → Bool |
| `CAST` | Convert value to target type |
| `CALL` | Push args, invoke callee, await result |
| `IF` | Evaluate condition, activate then/else branch |
| `LOOP` | Iterate: bind iterator, execute body, repeat |
| `MATCH` | Evaluate subject, find matching case |
| `TRY` | Execute body, catch exceptions, run finally |
| `SEQUENCE` | Execute steps in order |
| `PARALLEL` | Execute all branches concurrently |
| `RETURN` | Propagate value to caller |

---

## 2. Graph Interpreter Implementation

### 2.1 File
`/home/jayson/OREO/IDE/runtime/interpreter/evaluator.py`

### 2.2 Core Classes

```python
@dataclass
class Frame:
    """Execution frame for a function."""
    function: FunctionNode
    locals: Dict[str, Value]  # parameter/variable bindings
    pc: int = 0  # program counter (for bytecode)
    parent: Optional["Frame"] = None

@dataclass
class Value:
    """Runtime value with type tag."""
    type: TypeRef
    data: Any  # actual value (int, float, bool, string, ref, etc.)

class GraphInterpreter:
    def __init__(self):
        self.call_stack: List[Frame] = []
        self.heap: Dict[str, Value] = {}  # for mutable state
        self.effect_handlers: Dict[Effect, EffectHandler] = {}
        self.worklist: Deque[Node] = deque()
    
    def execute(self, graph: Graph, entry: str, args: List[Value]) -> Value:
        # Find entry function
        entry_fn = self._find_function(graph, entry)
        # Create initial frame
        frame = Frame(function=entry_fn, locals={})
        for i, param in enumerate(entry_fn.params):
            frame.locals[param.param_name] = args[i]
        self.call_stack.append(frame)
        
        # Initialize worklist with entry function body
        if entry_fn.body:
            self.worklist.append(entry_fn.body)
        
        # Reduction loop
        while self.worklist:
            node = self.worklist.popleft()
            if self._is_ready(node, frame):
                result = self._execute_node(node, frame)
                self._propagate(node, result, frame)
        
        # Return result from entry function
        return frame.locals.get("return", Value(UNIT, None))
    
    def _is_ready(self, node: Node, frame: Frame) -> bool:
        for port in node.input_ports():
            if port.is_required and port.name not in frame.locals:
                return False
        return True
```

### 2.3 Effect Handling

```python
class EffectHandler(ABC):
    @abstractmethod
    def handle(self, effect: Effect, continuation: Callable) -> Any:
        pass

class IOHandler(EffectHandler):
    def handle(self, effect: IO, continuation: Callable) -> Any:
        # Perform IO, resume continuation with result
        result = perform_io(effect.operation, effect.args)
        return continuation(result)

class StateHandler(EffectHandler):
    def handle(self, effect: State, continuation: Callable) -> Any:
        # Read/write heap location
        if effect.operation == "read":
            value = self.heap.get(effect.location)
        elif effect.operation == "write":
            self.heap[effect.location] = effect.value
        return continuation(value)

class ExceptionHandler(EffectHandler):
    def handle(self, effect: Exception, continuation: Callable) -> Any:
        # Unwind stack to nearest TRY node
        try:
            return continuation()
        except Exception as e:
            # Find matching catch clause
            handler = self._find_handler(e)
            return handler(e)

class AsyncHandler(EffectHandler):
    def handle(self, effect: Async, continuation: Callable) -> Any:
        # Spawn task, return future
        future = spawn_async(effect.computation)
        return continuation(future)
```

---

## 3. Memory Model

### 3.1 Value Semantics
- **Immutable by default** — all values are immutable
- **Explicit mutability** — `mut` keyword required, tracked in effect system
- **Ownership** — single owner, borrow checker (Rust-style)
- **GC for cycles** — reference counting + cycle detector

### 3.2 Memory Layout

```
Stack (per frame):
├── Parameters (bound at call)
├── Locals (variables, temporaries)
└── Return value

Heap (global):
├── Mutable state (State effect locations)
├── Closures (captured environments)
├── Channels (Async effect)
└── Resources (Resource effect)
```

### 3.3 Borrow Checking (Simplified)
- `&T` — shared borrow (multiple allowed)
- `&mut T` — exclusive borrow (one at a time)
- Checked at compile time via type checker
- Runtime enforcement for dynamic cases

---

## 4. Concurrency

### 4.1 Structured Concurrency
- **Scopes** — all child tasks bound to parent scope
- **Cancellation propagation** — parent cancellation cancels children
- **Error propagation** — first error cancels siblings

```python
class ConcurrencyScope:
    def __init__(self, parent: Optional["ConcurrencyScope"] = None):
        self.parent = parent
        self.children: List[Task] = []
        self.cancelled = False
    
    def spawn(self, coro: Callable) -> Task:
        task = Task(coro, scope=self)
        self.children.append(task)
        return task
    
    def cancel_all(self):
        self.cancelled = True
        for child in self.children:
            child.cancel()
```

### 4.2 Async/Await
- Effect-polymorphic: `fn[T](x: T) -> T [Async]`
- Compiles to state machine (bytecode) or native async (LLVM/WASM)
- Channels for communication: `Channel<T>` (typed, bounded/unbounded)

### 4.3 Actors (Optional)
- For distributed systems
- Message-passing, mailbox-based
- Location transparency

---

## 5. Compiler Backends

### 5.1 Target Backends

| Backend | Target | File Extension | Status |
|---------|--------|----------------|--------|
| `BYTECODE` | Custom VM | `.oreobc` | ✅ Implemented |
| `LLVM_IR` | LLVM | `.ll` | 🔄 Planned |
| `WASM` | WebAssembly | `.wat`/`.wasm` | 🔄 Planned |
| `C` | C source | `.c` | 🔄 Planned |
| `RUST` | Rust source | `.rs` | 🔄 Planned |
| `PYTHON` | Python source | `.py` | 🔄 Planned |
| `JAVASCRIPT` | JS/TS source | `.js`/`.ts` | 🔄 Planned |

### 5.2 File
`/home/jayson/OREO/IDE/runtime/compiler/backends.py`

### 5.3 Abstract Interface

```python
class CompilerBackend(ABC):
    def __init__(self, target: TargetBackend):
        self.target = target
    
    @abstractmethod
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        pass

@dataclass
class CompilationUnit:
    name: str
    graph: Graph
    entry_function: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompilationResult:
    success: bool
    output: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
```

### 5.4 Bytecode Compiler (Implemented)

**Class:** `BytecodeCompiler`

```python
class BytecodeCompiler(CompilerBackend):
    """Compiles GIR to custom bytecode for OREO VM."""
    
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        # 1. Collect all functions in graph
        functions = [n for n in unit.graph.nodes.values() 
                     if n.kind == NodeKind.FUNCTION]
        
        # 2. Build function table + string pool
        self.function_table = {f.name: i for i, f in enumerate(functions)}
        self.string_pool = self._collect_strings(unit.graph)
        
        # 3. Emit header
        bytecode = [
            "; OREO Bytecode v1",
            f"; Module: {unit.name}",
            "",
            ".strings:",
            *[f'  {i}: "{self._escape_string(s)}"' for i, s in enumerate(self.string_pool)],
            "",
            ".functions:",
            *[f"  {idx}: {name}" for name, idx in self.function_table.items()],
            "",
        ]
        
        # 4. Compile each function
        for func in functions:
            if func.name == unit.entry_function or unit.entry_function is None:
                bytecode.extend(self._compile_function(func, unit.graph))
                bytecode.append("")
        
        return CompilationResult(
            success=True,
            output="\n".join(bytecode),
            artifacts={"functions": self.function_table, "strings": self.string_pool}
        )
```

### 5.5 Bytecode Instruction Set

| Instruction | Operands | Description |
|-------------|----------|-------------|
| `ldint` | `<value>` | Load integer constant |
| `ldfloat` | `<value>` | Load float constant |
| `ldbool` | `<0\|1>` | Load boolean |
| `ldstr` | `<index>` | Load string from pool |
| `ldnull` | — | Load null |
| `ldloc` | `<index>` | Load local variable |
| `stloc` | `<index>` | Store local variable |
| `ldglob` | `<name>` | Load global variable |
| `stglob` | `<name>` | Store global variable |
| `call` | `<func_idx>` | Call function by index |
| `call_dyn` | — | Dynamic call (function ref on stack) |
| `ret` | — | Return from function |
| `br` | `<label>` | Unconditional branch |
| `brfalse` | `<label>` | Branch if false |
| `add`, `sub`, `mul`, `div`, `mod` | — | Arithmetic |
| `eq`, `ne`, `lt`, `le`, `gt`, `ge` | — | Comparison |
| `and`, `or`, `not`, `xor` | — | Logic |

### 5.6 Example Bytecode Output

```text
; OREO Bytecode v1
; Module: math

.strings:
  0: "add"
  1: "main"

.functions:
  0: add
  1: main

.function add:
  ; params: 2
  ; returns: Int(32)
  ; effects: []
  param 0 -> local 0  ; a: Int(32)
  param 1 -> local 1  ; b: Int(32)
  ldloc 0
  ldloc 1
  add
  ret
  end

.function main:
  ; params: 0
  ; returns: Int(32)
  ; effects: [IO]
  ldint 5
  ldint 3
  call 0
  call_dyn  ; print
  ret
  end
```

---

## 6. Rust Implementation (Core)

### 6.1 Crate Structure
```
oreo-runtime/
├── src/
│   ├── interpreter/      # Graph interpreter
│   │   ├── evaluator.rs  # Worklist executor
│   │   ├── frame.rs      # Call frames
│   │   ├── value.rs      # Value representation
│   │   └── effects.rs    # Effect handlers
│   ├── compiler/         # Compiler backends
│   │   ├── bytecode.rs   # Bytecode emission
│   │   ├── llvm.rs       # LLVM backend (planned)
│   │   └── wasm.rs       # WASM backend (planned)
│   ├── memory/           # Memory model
│   │   ├── heap.rs       # Heap allocator
│   │   ├── borrow.rs     # Borrow checker
│   │   └── gc.rs         # Cycle detector
│   └── concurrency/      # Structured concurrency
│       ├── scope.rs
│       ├── task.rs
│       └── channel.rs
```

### 6.2 Key Types

```rust
// Value representation
enum Value {
    Int(i64),
    UInt(u64),
    Float(f64),
    Bool(bool),
    String(String),
    Bytes(Vec<u8>),
    Ref(HeapRef),       // heap reference
    Closure(Closure),   // function + captured env
    Channel(Channel),   // async channel
}

// Frame for execution
struct Frame {
    function: FunctionNode,
    locals: HashMap<String, Value>,
    pc: usize,
    parent: Option<Box<Frame>>,
}

// Effect handlers
trait EffectHandler: Send + Sync {
    fn handle(&self, effect: Effect, cont: Box<dyn FnOnce(Value) -> Value>) -> Value;
}
```

---

## 7. VM Specification (Bytecode Interpreter)

### 7.1 VM State
```python
class VM:
    def __init__(self, bytecode: str):
        self.instructions = self._parse(bytecode)
        self.string_pool = []
        self.function_table = {}
        self.globals = {}
        self.call_stack = []
        self.pc = 0
    
    def run(self, entry: str = "main") -> Value:
        # 1. Load string pool
        # 2. Load function table
        # 3. Jump to entry function
        # 4. Execute instructions until RET
```

### 7.2 Instruction Encoding
Each instruction is a line: `opcode [operand...]`
- Comments start with `;`
- Labels: `label_name:`
- Jump targets reference labels

---

## 8. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `/home/jayson/OREO/IDE/runtime/interpreter/evaluator.py` | ~1700 | Graph interpreter |
| `/home/jayson/OREO/IDE/runtime/compiler/backends.py` | 565 | Compiler backends (bytecode + stubs) |
| `/home/jayson/OREO/IDE/src/runtime/interpreter/` | ~2000 | Rust interpreter |
| `/home/jayson/OREO/IDE/src/runtime/compiler/` | ~1500 | Rust compiler |
| `/home/jayson/OREO/IDE/src/runtime/memory/` | ~1200 | Memory model |
| `/home/jayson/OREO/IDE/src/runtime/concurrency/` | ~1000 | Structured concurrency |

---

## 9. Running the Runtime

### 9.1 Graph Interpreter (Python)
```bash
# When implemented
python3 -m runtime.interpreter examples/hello_world.oreo
```

### 9.2 Bytecode Compiler
```bash
# Compile to bytecode
python3 -m runtime.compiler --target bytecode examples/factorial.oreo -o factorial.oreobc

# Run bytecode
python3 -m runtime.vm factorial.oreobc
```

### 9.3 Architecture Runtime (GraphLang - runnable now)
```bash
# Handshake enforcement demo
python3 examples/architecture/runtime_handshake.py

# Emit web app and hit routes
python3 examples/architecture/emit_and_hit.py

# Live editor
python3 -m parser.architecture.visual
```

---

## 10. Future Work

### 10.1 Compiler Backends
- [ ] LLVM IR backend (via `inkwell` crate)
- [ ] WebAssembly backend (via `wasm-encoder`)
- [ ] C backend (for embedded)
- [ ] Rust backend (for systems integration)

### 10.2 Runtime Features
- [ ] JIT compilation for hot functions
- [ ] Profile-guided optimization
- [ ] Distributed actor runtime
- [ ] WASM host integration

### 10.3 Debugging & Profiling
- [ ] Visual debugger (step through graph)
- [ ] Flame graph profiler
- [ ] Memory leak detector
- [ ] Time-travel debugging

---

*Generated from OREO source code — see `/home/jayson/OREO/IDE/runtime/` and `/home/jayson/OREO/IDE/src/runtime/` for implementation.*