from typing import Dict, Any, List, Callable, TypeVar, Optional, Union, Type, Generic
import inspect
from functools import wraps

T = TypeVar('T')
NodeHandler = Callable[['ASTWalker', Dict[str, Any]], Any]

class ASTWalker:
    """
    A flexible AST walker that transforms parse trees into other representations.
    
    Features:
    - Register handlers for specific node types using decorators
    - Chain transformations using fluent API
    - Support for pre/post processing steps
    - Contextual data shared between handlers
    """
    def __init__(self):
        self.handlers: Dict[str, NodeHandler] = {}
        self.default_handler: Optional[NodeHandler] = None
        self.context: Dict[str, Any] = {}
        self.pre_processors: List[Callable] = []
        self.post_processors: List[Callable] = []
    
    def for_node(self, node_type: str) -> Callable[[NodeHandler], NodeHandler]:
        """Register a handler for a specific node type."""
        def decorator(handler: NodeHandler) -> NodeHandler:
            @wraps(handler)
            def wrapper(node: Dict[str, Any]) -> Any:
                return handler(self, node)
            
            self.handlers[node_type] = wrapper
            return handler
        return decorator
    
    def default(self) -> Callable[[NodeHandler], NodeHandler]:
        """Register a default handler for unrecognized node types."""
        def decorator(handler: NodeHandler) -> NodeHandler:
            @wraps(handler)
            def wrapper(node: Dict[str, Any]) -> Any:
                return handler(self, node)
            
            self.default_handler = wrapper
            return handler
        return decorator
    
    def pre_process(self) -> Callable[[Callable], Callable]:
        """Register a pre-processing function."""
        def decorator(func: Callable) -> Callable:
            self.pre_processors.append(func)
            return func
        return decorator
    
    def post_process(self) -> Callable[[Callable], Callable]:
        """Register a post-processing function."""
        def decorator(func: Callable) -> Callable:
            self.post_processors.append(func)
            return func
        return decorator
    
    def with_context(self, **kwargs) -> 'ASTWalker':
        """Add context data for handler use."""
        self.context.update(kwargs)
        return self
    
    def walk(self, ast_node: Any) -> Any:
        """
        Walk through the AST, applying transformations based on registered handlers.
        
        Args:
            ast_node: The AST node to process (could be an object with ast() method,
                     a dictionary, a list, or a primitive value)
        
        Returns:
            The transformed AST
        """
        if hasattr(ast_node, 'ast'):
            return self.walk(ast_node.ast())
        
        if not isinstance(ast_node, (dict, list)):
            return ast_node
        
        if isinstance(ast_node, list):
            return [self.walk(item) for item in ast_node]
        
        for processor in self.pre_processors:
            ast_node = processor(ast_node, self.context)
        
        node_type = ast_node.get("name")
        node_value = ast_node.get("value")
        
        if node_type in self.handlers:
            result = self.handlers[node_type](ast_node)
        elif self.default_handler:
            result = self.default_handler(ast_node)
        else:
            result = self._default_process(node_type, node_value)
        
        for processor in self.post_processors:
            result = processor(result, self.context)
        
        return result
    
    def _default_process(self, node_type: str, value: Any) -> Dict[str, Any]:
        """Default processing for nodes without specific handlers."""
        if isinstance(value, list):
            processed_values = [self.walk(item) for item in value]
            return {"type": node_type, "children": processed_values}
        elif isinstance(value, dict):
            return {"type": node_type, "children": self.walk(value)}
        else:
            return {"type": node_type, "value": value}

class TypedASTWalker(Generic[T]):
    """
    A strongly-typed AST walker that transforms parse trees into specific types.
    """
    def __init__(self, output_type: Type[T]):
        self.walker = ASTWalker()
        self.output_type = output_type
    
    def for_node(self, node_type: str) -> Callable:
        return self.walker.for_node(node_type)
    
    def default(self) -> Callable:
        return self.walker.default()
    
    def pre_process(self) -> Callable:
        return self.walker.pre_process()
    
    def post_process(self) -> Callable:
        return self.walker.post_process()
    
    def with_context(self, **kwargs) -> 'TypedASTWalker[T]':
        self.walker.with_context(**kwargs)
        return self
    
    def walk(self, ast_node: Any) -> T:
        """Walk the AST and return a strongly-typed result."""
        result = self.walker.walk(ast_node)
        if not isinstance(result, self.output_type):
            raise TypeError(f"Expected {self.output_type.__name__}, got {type(result).__name__}")
        return result