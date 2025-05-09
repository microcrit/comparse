from typing import Dict, Any, List, Callable, TypeVar, Optional, Type, Generic
from functools import wraps
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class WalkContext:
    """Context information for node traversal"""
    parent: Optional[Dict[str, Any]] = None
    level: int = 0
    path: List[str] = None
    
    def __post_init__(self):
        if self.path is None:
            self.path = []

NodeHandler = Callable[['ASTWalker', Dict[str, Any], WalkContext], Any]

class ASTWalker:
    """
    A generic AST walker that applies handlers to nodes in an abstract syntax tree.
    """
    def __init__(self):
        self.handlers: Dict[str, NodeHandler] = {}
        self.default_handler: Optional[NodeHandler] = None
        self.context: Dict[str, Any] = {}
        self.pre_processors: List[Callable] = []
        self.post_processors: List[Callable] = []
        self.auto_traverse: bool = True
    
    def for_node(self, node_type: str, auto_traverse: bool = True) -> Callable[[NodeHandler], NodeHandler]:
        """
        Register a handler for a specific node type.
        
        Args:
            node_type: The name of the node type to handle
            auto_traverse: If True, the walker will automatically traverse child nodes
                           before calling the handler
        """
        def decorator(handler: NodeHandler) -> NodeHandler:
            @wraps(handler)
            def wrapper(node: Dict[str, Any], walk_context: WalkContext = None) -> Any:
                if walk_context is None:
                    walk_context = WalkContext()
                
                if auto_traverse and isinstance(node.get("value"), (dict, list)):
                    if isinstance(node["value"], dict):
                        node["processed_value"] = self.walk(node["value"], 
                                                           parent=node, 
                                                           level=walk_context.level + 1)
                    else:
                        node["processed_value"] = [self.walk(item, 
                                                           parent=node, 
                                                           level=walk_context.level + 1) 
                                                  for item in node["value"]]
                
                return handler(self, node, walk_context)
            
            self.handlers[node_type] = wrapper
            return handler
        return decorator
    
    def default(self, auto_traverse: bool = True) -> Callable[[NodeHandler], NodeHandler]:
        """Register a default handler for unrecognized node types."""
        def decorator(handler: NodeHandler) -> NodeHandler:
            @wraps(handler)
            def wrapper(node: Dict[str, Any], walk_context: WalkContext = None) -> Any:
                if walk_context is None:
                    walk_context = WalkContext()
                    
                if auto_traverse and isinstance(node.get("value"), (dict, list)):
                    if isinstance(node["value"], dict):
                        node["processed_value"] = self.walk(node["value"], 
                                                           parent=node, 
                                                           level=walk_context.level + 1)
                    else:
                        node["processed_value"] = [self.walk(item, 
                                                           parent=node, 
                                                           level=walk_context.level + 1) 
                                                  for item in node["value"]]
                
                return handler(self, node, walk_context)
            
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

    def clear_context(self) -> None:
        """Clear the context data."""
        self.context.clear()

    def walk(self, ast_node: Any, parent: Dict[str, Any] = None, level: int = 0, path: List[str] = None) -> Any:
        """
        Walk the AST and apply registered handlers.
        
        Args:
            ast_node: The current node being processed
            parent: The parent node of the current node
            level: The recursion depth/level of the current node
            path: The path of node types traversed to reach this node
        """
        if path is None:
            path = []
            
        if hasattr(ast_node, 'ast'):
            return self.walk(ast_node.ast(), parent, level, path)
        
        if not isinstance(ast_node, (dict, list)):
            return ast_node
        
        if isinstance(ast_node, list):
            return [self.walk(item, parent, level + 1, path) for item in ast_node]
        
        for processor in self.pre_processors:
            ast_node = processor(ast_node, self.context)
        
        # Use type for handler lookup, but maintain name for path
        node_type = ast_node.get("type", ast_node.get("name"))
        node_name = ast_node.get("name", node_type)
        current_path = path + ([node_name] if node_name else [])
        
        walk_context = WalkContext(parent=parent, level=level, path=current_path)
        
        if node_type in self.handlers:
            result = self.handlers[node_type](ast_node, walk_context)
        elif self.default_handler:
            result = self.default_handler(ast_node, walk_context)
        else:
            result = self._default_process(ast_node, walk_context)
        
        for processor in self.post_processors:
            result = processor(result, self.context)
        
        return result
    
    def _default_process(self, node: Dict[str, Any], walk_context: WalkContext) -> Dict[str, Any]:
        """Default processing for nodes without registered handlers"""
        node_type = node.get("name")
        value = node.get("value")
        
        if isinstance(value, list):
            processed_values = [self.walk(item, 
                                         parent=node, 
                                         level=walk_context.level + 1, 
                                         path=walk_context.path) 
                               for item in value]
            return {"type": node_type, "children": processed_values}
        elif isinstance(value, dict):
            return {"type": node_type, "children": self.walk(value, 
                                                           parent=node, 
                                                           level=walk_context.level + 1,
                                                           path=walk_context.path)}
        else:
            return {"type": node_type, "value": value}

class TypedASTWalker(Generic[T]):
    """
    A strongly-typed AST walker that transforms parse trees into specific types.
    """
    def __init__(self, output_type: Type[T]):
        self.walker = ASTWalker()
        self.output_type = output_type
    
    def for_node(self, node_type: str, auto_traverse: bool = True) -> Callable:
        """
        Register a handler for a specific node type.
        
        Args:
            node_type: The name of the node type to handle
            auto_traverse: If True, the walker will automatically traverse child nodes
                           before calling the handler
        """
        return self.walker.for_node(node_type, auto_traverse)
    
    def default(self, auto_traverse: bool = True) -> Callable:
        return self.walker.default(auto_traverse)
    
    def pre_process(self) -> Callable:
        return self.walker.pre_process()
    
    def post_process(self) -> Callable:
        return self.walker.post_process()
    
    def with_context(self, **kwargs) -> 'TypedASTWalker[T]':
        self.walker.with_context(**kwargs)
        return self
    
    def walk(self, ast_node: Any) -> Any:
        """Walk the AST and return a result (only enforce type at root level)"""
        if hasattr(ast_node, 'ast'):
            actual_ast = ast_node.ast()
        else:
            actual_ast = ast_node
        
        result = self.walker.walk(actual_ast)
        
        if isinstance(actual_ast, dict) and actual_ast.get("name") == "CommandLineParser":
            if not isinstance(result, self.output_type):
                raise TypeError(f"Expected {self.output_type.__name__}, got {type(result).__name__}")
        
        return result