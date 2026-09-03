"""
AI Integration - Code Generation
Generates GIR graphs from natural language using AI.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import json

from parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind, Port, TypeRef,
    FunctionNode, create_function, create_parameter, create_call,
    create_literal, connect_data, connect_control, connect_composition,
    INT, BOOL, STRING, UNIT, Type,
)
from parser.nl_parser.semantic_parser import parse_nl, NLParser


class GenerationMode(Enum):
    """Code generation modes."""
    FROM_NL = "from_nl"           # Natural language → GIR
    FROM_SPEC = "from_spec"       # Formal spec → GIR
    FROM_EXAMPLES = "from_examples"  # Examples → GIR
    REFACTOR = "refactor"         # Existing GIR → Improved GIR
    COMPLETE = "complete"         # Partial GIR → Complete GIR


@dataclass
class GenerationRequest:
    """Request for code generation."""
    mode: GenerationMode
    input_text: str
    context: Dict[str, Any] = field(default_factory=dict)
    target_graph: Optional[Graph] = None
    constraints: List[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.1


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    graph: Optional[Graph] = None
    generated_code: str = ""
    explanation: str = ""
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GIRGenerator:
    """Generates GIR graphs using AI."""
    
    def __init__(self, llm_client: Optional[Callable] = None):
        self.llm_client = llm_client
        self.nl_parser = NLParser()
    
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate GIR from request."""
        if request.mode == GenerationMode.FROM_NL:
            return self._generate_from_nl(request)
        elif request.mode == GenerationMode.FROM_SPEC:
            return self._generate_from_spec(request)
        elif request.mode == GenerationMode.COMPLETE:
            return self._generate_completion(request)
        else:
            return GenerationResult(
                success=False,
                errors=[f"Generation mode {request.mode} not implemented"]
            )
    
    def _generate_from_nl(self, request: GenerationRequest) -> GenerationResult:
        """Generate GIR from natural language."""
        try:
            # Use the NL parser for basic parsing
            graph = parse_nl(request.input_text)
            
            # If LLM client available, enhance with AI
            if self.llm_client:
                enhanced = self._enhance_with_llm(request.input_text, graph)
                if enhanced:
                    graph = enhanced
            
            return GenerationResult(
                success=True,
                graph=graph,
                generated_code=graph.to_dict() if hasattr(graph, 'to_dict') else str(graph),
                explanation=f"Parsed natural language: {request.input_text[:100]}...",
                confidence=0.8,
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                errors=[f"NL parsing failed: {str(e)}"]
            )
    
    def _enhance_with_llm(self, nl_text: str, graph: Graph) -> Optional[Graph]:
        """Enhance parsed graph with LLM."""
        if not self.llm_client:
            return None
        
        # TODO: Implement LLM enhancement
        # This would send the NL and parsed graph to LLM for refinement
        return graph
    
    def _generate_from_spec(self, request: GenerationRequest) -> GenerationResult:
        """Generate GIR from formal specification."""
        # TODO: Implement spec-based generation
        return GenerationResult(
            success=False,
            errors=["Spec-based generation not yet implemented"]
        )
    
    def _generate_completion(self, request: GenerationRequest) -> GenerationResult:
        """Complete a partial GIR graph."""
        if not request.target_graph:
            return GenerationResult(
                success=False,
                errors=["No target graph provided for completion"]
            )
        
        # TODO: Implement graph completion
        return GenerationResult(
            success=False,
            errors=["Graph completion not yet implemented"]
        )


class TypeChecker:
    """Type checks GIR graphs."""
    
    def __init__(self):
        from parser.gir import validate_graph
        self.validator = validate_graph
    
    def check(self, graph: Graph) -> GenerationResult:
        """Type check a graph."""
        result = self.validator(graph)
        
        if result.has_errors():
            return GenerationResult(
                success=False,
                errors=[str(e) for e in result.errors()],
                warnings=[str(w) for w in result.warnings()],
            )
        
        return GenerationResult(
            success=True,
            graph=graph,
            explanation="Type checking passed",
            confidence=1.0,
        )


class ContractVerifier:
    """Verifies contracts (pre/post conditions) using SMT."""
    
    def __init__(self, z3_available: bool = True):
        self.z3_available = z3_available
        try:
            import z3
            self.z3 = z3
        except ImportError:
            self.z3_available = False
    
    def verify(self, graph: Graph) -> GenerationResult:
        """Verify contracts in graph."""
        if not self.z3_available:
            return GenerationResult(
                success=True,
                graph=graph,
                warnings=["Z3 not available, skipping contract verification"],
                confidence=0.5,
            )
        
        # TODO: Implement contract verification with Z3
        # Would extract pre/post conditions and verify with SMT solver
        
        return GenerationResult(
            success=True,
            graph=graph,
            explanation="Contract verification (stub)",
            confidence=0.7,
        )


class AIGenerationPipeline:
    """Complete AI generation pipeline."""
    
    def __init__(self, llm_client: Optional[Callable] = None):
        self.generator = GIRGenerator(llm_client)
        self.type_checker = TypeChecker()
        self.contract_verifier = ContractVerifier()
    
    def generate_and_verify(self, request: GenerationRequest) -> GenerationResult:
        """Generate, type check, and verify contracts."""
        # Generate
        gen_result = self.generator.generate(request)
        if not gen_result.success:
            return gen_result
        
        # Type check
        type_result = self.type_checker.check(gen_result.graph)
        if not type_result.success:
            return type_result
        
        # Verify contracts
        verify_result = self.contract_verifier.verify(gen_result.graph)
        
        # Combine results
        return GenerationResult(
            success=verify_result.success,
            graph=gen_result.graph,
            generated_code=gen_result.generated_code,
            explanation=f"{gen_result.explanation}\n{verify_result.explanation}",
            confidence=min(gen_result.confidence, verify_result.confidence),
            errors=gen_result.errors + verify_result.errors,
            warnings=gen_result.warnings + verify_result.warnings,
        )


def create_gir_generator(llm_client: Optional[Callable] = None) -> GIRGenerator:
    """Factory function."""
    return GIRGenerator(llm_client)


def create_ai_pipeline(llm_client: Optional[Callable] = None) -> AIGenerationPipeline:
    """Factory function."""
    return AIGenerationPipeline(llm_client)