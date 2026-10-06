"""
Natural Language Parser for OREO
Converts natural language descriptions into GIR graphs.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from abc import ABC, abstractmethod

from ..gir import (
    Graph, Node, NodeKind, Port, TypeRef,
    LiteralNode, VariableNode, ParameterNode, FunctionNode,
    IfNode, CallNode, ArithmeticNode, LogicNode, ComparisonNode,
    SequenceNode, ReturnNode, ArithmeticOp, LogicOp, ComparisonOp,
    connect_data, connect_control, connect_composition, validate_graph, ValidationResult,
    INT, BOOL, STRING, UNIT, make_function,
    create_literal, create_variable, create_parameter,
    EFFECT_IO,
)


class TokenType(Enum):
    """Token types for NL tokenization."""
    # Keywords
    DEFINE = "define"
    FUNCTION = "function"
    IF = "if"
    THEN = "then"
    ELSE = "else"
    LOOP = "loop"
    FOR = "for"
    WHILE = "while"
    RETURN = "return"
    VAR = "var"
    LET = "let"
    CONST = "const"
    
    # Types
    INT_TYPE = "int"
    BOOL_TYPE = "bool"
    STRING_TYPE = "string"
    FLOAT_TYPE = "float"
    
    # Operators
    PLUS = "plus"
    MINUS = "minus"
    MUL = "multiply"
    DIV = "divide"
    MOD = "modulo"
    EQ = "equals"
    NE = "not_equals"
    LT = "less_than"
    LE = "less_equal"
    GT = "greater_than"
    GE = "greater_equal"
    AND = "and"
    OR = "or"
    NOT = "not"
    
    # Punctuation
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    COMMA = ","
    COLON = ":"
    ARROW = "->"
    ASSIGN = "="
    
    # Literals
    NUMBER = "number"
    STRING_LIT = "string"
    BOOL_LIT = "bool"
    IDENTIFIER = "identifier"
    
    # Special
    EOF = "eof"
    UNKNOWN = "unknown"


@dataclass
class Token:
    type: TokenType
    value: str
    line: int = 1
    column: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class NLTokenizer:
    """Tokenizes natural language into structured tokens."""
    
    # Keyword mappings
    KEYWORDS = {
        "define": TokenType.DEFINE,
        "function": TokenType.FUNCTION,
        "fn": TokenType.FUNCTION,
        "if": TokenType.IF,
        "then": TokenType.THEN,
        "else": TokenType.ELSE,
        "loop": TokenType.LOOP,
        "for": TokenType.FOR,
        "while": TokenType.WHILE,
        "return": TokenType.RETURN,
        "var": TokenType.VAR,
        "let": TokenType.LET,
        "const": TokenType.CONST,
        "int": TokenType.INT_TYPE,
        "integer": TokenType.INT_TYPE,
        "bool": TokenType.BOOL_TYPE,
        "boolean": TokenType.BOOL_TYPE,
        "string": TokenType.STRING_TYPE,
        "float": TokenType.FLOAT_TYPE,
        "plus": TokenType.PLUS,
        "add": TokenType.PLUS,
        "minus": TokenType.MINUS,
        "subtract": TokenType.MINUS,
        "multiply": TokenType.MUL,
        "times": TokenType.MUL,
        "divide": TokenType.DIV,
        "modulo": TokenType.MOD,
        "mod": TokenType.MOD,
        "equals": TokenType.EQ,
        "equal": TokenType.EQ,
        "not equals": TokenType.NE,
        "not equal": TokenType.NE,
        "less than": TokenType.LT,
        "less equal": TokenType.LE,
        "greater than": TokenType.GT,
        "greater equal": TokenType.GE,
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
        "true": TokenType.BOOL_LIT,
        "false": TokenType.BOOL_LIT,
    }
    
    def __init__(self):
        self.text = ""
        self.pos = 0
        self.line = 1
        self.column = 1
    
    def tokenize(self, text: str) -> List[Token]:
        self.text = text.lower()
        self.pos = 0
        self.line = 1
        self.column = 1
        tokens = []
        
        while self.pos < len(self.text):
            # Skip whitespace
            if self.text[self.pos].isspace():
                if self.text[self.pos] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue
            
            # Try multi-word keywords first
            matched = False
            for kw in sorted(self.KEYWORDS.keys(), key=len, reverse=True):
                if self.text.startswith(kw, self.pos):
                    # Check word boundaries
                    end_pos = self.pos + len(kw)
                    if end_pos == len(self.text) or not self.text[end_pos].isalnum():
                        tokens.append(Token(
                            type=self.KEYWORDS[kw],
                            value=kw,
                            line=self.line,
                            column=self.column
                        ))
                        self._advance(len(kw))
                        matched = True
                        break
            
            if matched:
                continue
            
            # Single character tokens
            char = self.text[self.pos]
            if char == '(':
                tokens.append(Token(TokenType.LPAREN, char, self.line, self.column))
            elif char == ')':
                tokens.append(Token(TokenType.RPAREN, char, self.line, self.column))
            elif char == '{':
                tokens.append(Token(TokenType.LBRACE, char, self.line, self.column))
            elif char == '}':
                tokens.append(Token(TokenType.RBRACE, char, self.line, self.column))
            elif char == ',':
                tokens.append(Token(TokenType.COMMA, char, self.line, self.column))
            elif char == ':':
                tokens.append(Token(TokenType.COLON, char, self.line, self.column))
            elif char == '+':
                tokens.append(Token(TokenType.PLUS, char, self.line, self.column))
            elif char == '-':
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '>':
                    tokens.append(Token(TokenType.ARROW, '->', self.line, self.column))
                    self._advance(2)
                    continue
                tokens.append(Token(TokenType.MINUS, char, self.line, self.column))
            elif char == '*':
                tokens.append(Token(TokenType.MUL, char, self.line, self.column))
            elif char == '/':
                tokens.append(Token(TokenType.DIV, char, self.line, self.column))
            elif char == '%':
                tokens.append(Token(TokenType.MOD, char, self.line, self.column))
            elif char == '=':
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '>':
                    tokens.append(Token(TokenType.ARROW, '->', self.line, self.column))
                    self._advance(2)
                    continue
                elif self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '=':
                    tokens.append(Token(TokenType.EQ, '==', self.line, self.column))
                    self._advance(2)
                    continue
                else:
                    tokens.append(Token(TokenType.ASSIGN, char, self.line, self.column))
            elif char == '!':
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '=':
                    tokens.append(Token(TokenType.NE, '!=', self.line, self.column))
                    self._advance(2)
                    continue
                tokens.append(Token(TokenType.NOT, char, self.line, self.column))
            elif char == '<':
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '=':
                    tokens.append(Token(TokenType.LE, '<=', self.line, self.column))
                    self._advance(2)
                    continue
                tokens.append(Token(TokenType.LT, char, self.line, self.column))
            elif char == '>':
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '=':
                    tokens.append(Token(TokenType.GE, '>=', self.line, self.column))
                    self._advance(2)
                    continue
                tokens.append(Token(TokenType.GT, char, self.line, self.column))
            elif char.isdigit():
                tokens.append(self._read_number())
                continue
            elif char == '"' or char == "'":
                tokens.append(self._read_string(char))
                continue
            elif char.isalpha() or char == '_':
                tokens.append(self._read_identifier())
                continue
            else:
                tokens.append(Token(TokenType.UNKNOWN, char, self.line, self.column))
            
            self._advance(1)
        
        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return tokens
    
    def _advance(self, n: int):
        for _ in range(n):
            if self.pos < len(self.text) and self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def _read_number(self) -> Token:
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            self._advance(1)
        value = self.text[start:self.pos]
        return Token(TokenType.NUMBER, value, self.line, self.column)
    
    def _read_string(self, quote: str) -> Token:
        start = self.pos
        self._advance(1)  # skip opening quote
        while self.pos < len(self.text) and self.text[self.pos] != quote:
            self._advance(1)
        if self.pos < len(self.text):
            self._advance(1)  # skip closing quote
        value = self.text[start+1:self.pos-1]
        return Token(TokenType.STRING_LIT, value, self.line, self.column)
    
    def _read_identifier(self) -> Token:
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self._advance(1)
        value = self.text[start:self.pos]
        # Check if it's a keyword
        tok_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        return Token(tok_type, value, self.line, self.column)


@dataclass
class ParseContext:
    """Context for parsing - tracks variables, functions, scopes."""
    variables: Dict[str, TypeRef] = field(default_factory=dict)
    functions: Dict[str, FunctionNode] = field(default_factory=dict)
    current_scope: Optional[Node] = None
    current_function: Optional[FunctionNode] = None


class NLParser:
    """Parses tokenized natural language into GIR graphs."""
    
    def __init__(self):
        self.tokenizer = NLTokenizer()
        self.tokens: List[Token] = []
        self.pos = 0
        self.context = ParseContext()
        self.graph = Graph(name="parsed_program")
    
    def parse(self, text: str) -> Graph:
        """Parse natural language text into a GIR graph."""
        self.tokens = self.tokenizer.tokenize(text)
        self.pos = 0
        self.context = ParseContext()
        self.graph = Graph(name="parsed_program")
        
        self._parse_program()
        
        # Validate
        result = validate_graph(self.graph)
        if result.has_errors():
            raise ParseError(f"Parse validation failed: {result}")
        
        return self.graph
    
    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "", 0, 0)
    
    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok
    
    def _expect(self, tok_type: TokenType) -> Token:
        tok = self._current()
        if tok.type != tok_type:
            raise ParseError(f"Expected {tok_type}, got {tok.type} at line {tok.line}")
        return self._advance()
    
    def _match(self, *tok_types: TokenType) -> bool:
        return self._current().type in tok_types
    
    def _parse_program(self):
        """Parse top-level program (module)."""
        module = Node(kind=NodeKind.MODULE, name="main")
        self.graph.add_node(module)
        self.context.current_scope = module
        
        while not self._match(TokenType.EOF):
            if self._match(TokenType.DEFINE, TokenType.FUNCTION):
                self._parse_function_definition(module)
            elif self._match(TokenType.VAR, TokenType.LET, TokenType.CONST):
                self._parse_variable_declaration(module)
            else:
                self._parse_statement()
    
    def _parse_function_definition(self, parent: Node):
        """Parse function definition."""
        # consume 'define function' or 'function'
        if self._match(TokenType.DEFINE):
            self._advance()
        self._expect(TokenType.FUNCTION)
        
        name_tok = self._expect(TokenType.IDENTIFIER)
        func_name = name_tok.value
        
        self._expect(TokenType.LPAREN)
        params = []
        while not self._match(TokenType.RPAREN):
            param_name = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.COLON)
            param_type = self._parse_type()
            params.append(create_parameter(param_name, param_type))
            if self._match(TokenType.COMMA):
                self._advance()
        self._expect(TokenType.RPAREN)
        
        return_type = TypeRef("Unit")
        if self._match(TokenType.ARROW):
            self._advance()
            return_type = self._parse_type()
        
        self._expect(TokenType.LBRACE)
        
        func_node = FunctionNode(
            func_name=func_name,
            params=params,
            return_type=return_type,
            is_public=True
        )
        self.graph.add_node(func_node)
        connect_composition(self.graph, parent, func_node)
        
        old_function = self.context.current_function
        old_scope = self.context.current_scope
        self.context.current_function = func_node
        self.context.current_scope = func_node
        
        # Add parameters to scope
        for param in params:
            self.context.variables[param.param_name] = param.param_type
        
        # Parse body
        body = self._parse_block()
        func_node.body = body
        
        self._expect(TokenType.RBRACE)
        
        self.context.current_function = old_function
        self.context.current_scope = old_scope
        self.context.functions[func_name] = func_node
    
    def _parse_type(self) -> TypeRef:
        """Parse type annotation."""
        if self._match(TokenType.INT_TYPE):
            self._advance()
            return TypeRef("Int")
        elif self._match(TokenType.BOOL_TYPE):
            self._advance()
            return TypeRef("Bool")
        elif self._match(TokenType.STRING_TYPE):
            self._advance()
            return TypeRef("String")
        elif self._match(TokenType.FLOAT_TYPE):
            self._advance()
            return TypeRef("Float")
        elif self._match(TokenType.IDENTIFIER):
            name = self._advance().value
            if self._match(TokenType.LPAREN):
                self._advance()
                args = []
                while not self._match(TokenType.RPAREN):
                    args.append(self._parse_type())
                    if self._match(TokenType.COMMA):
                        self._advance()
                self._expect(TokenType.RPAREN)
                return TypeRef(name, args)
            return TypeRef(name)
        return TypeRef("Any")
    
    def _parse_block(self) -> Node:
        """Parse a block of statements."""
        seq = SequenceNode()
        self.graph.add_node(seq)
        
        while not self._match(TokenType.RBRACE, TokenType.EOF, TokenType.ELSE):
            stmt = self._parse_statement()
            if stmt:
                connect_composition(self.graph, seq, stmt)
        
        return seq
    
    def _parse_statement(self, parent: Optional[Node] = None) -> Optional[Node]:
        """Parse a single statement."""
        if self._match(TokenType.VAR, TokenType.LET, TokenType.CONST):
            return self._parse_variable_declaration(parent)
        elif self._match(TokenType.IF):
            return self._parse_if_statement()
        elif self._match(TokenType.RETURN):
            return self._parse_return_statement()
        elif self._match(TokenType.IDENTIFIER):
            # Could be assignment or call
            return self._parse_expression_statement()
        else:
            self._advance()
            return None
    
    def _parse_variable_declaration(self, parent: Optional[Node]) -> Node:
        """Parse variable declaration. parent may be None when the enclosing
        block already composes the statement into its sequence node."""
        is_mutable = False
        if self._match(TokenType.VAR):
            self._advance()
            is_mutable = True
        elif self._match(TokenType.LET):
            self._advance()
        elif self._match(TokenType.CONST):
            self._advance()
        
        name_tok = self._expect(TokenType.IDENTIFIER)
        var_name = name_tok.value
        
        var_type = TypeRef("Any")
        if self._match(TokenType.COLON):
            self._advance()
            var_type = self._parse_type()
        
        init_value = None
        if self._match(TokenType.ASSIGN):
            self._advance()
            init_value = self._parse_expression()
        
        var_node = create_variable(var_name, var_type, is_mutable)
        self.graph.add_node(var_node)
        if parent is not None:
            connect_composition(self.graph, parent, var_node)
        
        if init_value:
            connect_data(self.graph, init_value, "result", var_node, "value")
        
        self.context.variables[var_name] = var_type
        return var_node
    
    def _parse_if_statement(self) -> Node:
        """Parse if-then-else statement."""
        self._expect(TokenType.IF)
        
        condition = self._parse_expression()
        self._expect(TokenType.THEN)
        
        then_branch = self._parse_block()
        
        else_branch = None
        if self._match(TokenType.ELSE):
            self._advance()
            else_branch = self._parse_block()
        
        if_node = IfNode()
        self.graph.add_node(if_node)
        
        connect_data(self.graph, condition, "result", if_node, "condition")
        connect_control(self.graph, then_branch, if_node, "", "then")
        if else_branch:
            connect_control(self.graph, else_branch, if_node, "", "else")
        
        return if_node
    
    def _parse_return_statement(self) -> Node:
        """Parse return statement."""
        self._expect(TokenType.RETURN)
        
        value = None
        if not self._match(TokenType.RBRACE, TokenType.EOF, TokenType.ELSE):
            value = self._parse_expression()
        
        ret_node = ReturnNode()
        self.graph.add_node(ret_node)
        
        if value:
            connect_data(self.graph, value, "result", ret_node, "value")
        
        return ret_node
    
    def _parse_expression_statement(self) -> Optional[Node]:
        """Parse expression statement (assignment or call)."""
        expr = self._parse_expression()
        return expr
    
    def _parse_expression(self) -> Node:
        """Parse expression with precedence."""
        return self._parse_logical_or()
    
    def _parse_logical_or(self) -> Node:
        left = self._parse_logical_and()
        while self._match(TokenType.OR):
            self._advance()
            right = self._parse_logical_and()
            op_node = LogicNode(op=LogicOp.OR)
            self.graph.add_node(op_node)
            connect_data(self.graph, left, "result", op_node, "lhs")
            connect_data(self.graph, right, "result", op_node, "rhs")
            left = op_node
        return left
    
    def _parse_logical_and(self) -> Node:
        left = self._parse_comparison()
        while self._match(TokenType.AND):
            self._advance()
            right = self._parse_comparison()
            op_node = LogicNode(op=LogicOp.AND)
            self.graph.add_node(op_node)
            connect_data(self.graph, left, "result", op_node, "lhs")
            connect_data(self.graph, right, "result", op_node, "rhs")
            left = op_node
        return left
    
    def _parse_comparison(self) -> Node:
        left = self._parse_additive()
        while self._match(TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op_tok = self._advance()
            right = self._parse_additive()
            op_map = {
                TokenType.EQ: ComparisonOp.EQ,
                TokenType.NE: ComparisonOp.NE,
                TokenType.LT: ComparisonOp.LT,
                TokenType.LE: ComparisonOp.LE,
                TokenType.GT: ComparisonOp.GT,
                TokenType.GE: ComparisonOp.GE,
            }
            op_node = ComparisonNode(op=op_map[op_tok.type])
            self.graph.add_node(op_node)
            connect_data(self.graph, left, "result", op_node, "lhs")
            connect_data(self.graph, right, "result", op_node, "rhs")
            left = op_node
        return left
    
    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            op = ArithmeticOp.ADD if op_tok.type == TokenType.PLUS else ArithmeticOp.SUB
            op_node = ArithmeticNode(op=op)
            self.graph.add_node(op_node)
            connect_data(self.graph, left, "result", op_node, "lhs")
            connect_data(self.graph, right, "result", op_node, "rhs")
            left = op_node
        return left
    
    def _parse_multiplicative(self) -> Node:
        left = self._parse_primary()
        while self._match(TokenType.MUL, TokenType.DIV, TokenType.MOD):
            op_tok = self._advance()
            right = self._parse_primary()
            op_map = {
                TokenType.MUL: ArithmeticOp.MUL,
                TokenType.DIV: ArithmeticOp.DIV,
                TokenType.MOD: ArithmeticOp.MOD,
            }
            op_node = ArithmeticNode(op=op_map[op_tok.type])
            self.graph.add_node(op_node)
            connect_data(self.graph, left, "result", op_node, "lhs")
            connect_data(self.graph, right, "result", op_node, "rhs")
            left = op_node
        return left
    
    def _parse_primary(self) -> Node:
        """Parse primary expression (literals, identifiers, calls, parens)."""
        tok = self._current()
        
        if self._match(TokenType.NUMBER):
            self._advance()
            node = create_literal(int(tok.value), TypeRef("Int"))
            self.graph.add_node(node)
            return node
        
        elif self._match(TokenType.STRING_LIT):
            self._advance()
            node = create_literal(tok.value, TypeRef("String"))
            self.graph.add_node(node)
            return node
        
        elif self._match(TokenType.BOOL_LIT):
            self._advance()
            node = create_literal(tok.value == "true", TypeRef("Bool"))
            self.graph.add_node(node)
            return node
        
        elif self._match(TokenType.IDENTIFIER):
            name = self._advance().value
            
            # Check for function call
            if self._match(TokenType.LPAREN):
                self._advance()
                args = []
                while not self._match(TokenType.RPAREN):
                    args.append(self._parse_expression())
                    if self._match(TokenType.COMMA):
                        self._advance()
                self._expect(TokenType.RPAREN)
                
                call_node = CallNode()
                self.graph.add_node(call_node)
                
                # Resolve function
                func = self.context.functions.get(name)
                if func:
                    call_node.add_port(Port("function", TypeRef("Any"), is_input=True))
                    func.add_port(Port("function", TypeRef("Any"), is_input=False))
                    connect_data(self.graph, func, "function", call_node, "function")
                
                for i, arg in enumerate(args):
                    call_node.add_port(Port(f"arg{i}", TypeRef("Any"), is_input=True))
                    connect_data(self.graph, arg, "result", call_node, f"arg{i}")
                
                return call_node
            
            # Variable reference
            var_node = create_variable(name, self.context.variables.get(name, TypeRef("Any")))
            self.graph.add_node(var_node)
            return var_node
        
        elif self._match(TokenType.LPAREN):
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr
        
        else:
            self._advance()
            node = create_literal(None, TypeRef("Unit"))
            self.graph.add_node(node)
            return node


class ParseError(Exception):
    pass


# --- Higher-level API ---

def parse_nl(text: str) -> Graph:
    """Parse natural language text into GIR graph."""
    parser = NLParser()
    return parser.parse(text)


def parse_nl_to_json(text: str) -> Dict[str, Any]:
    """Parse NL and return JSON-serializable graph."""
    graph = parse_nl(text)
    return graph.to_dict()