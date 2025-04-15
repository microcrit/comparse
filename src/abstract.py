from typing import List, Dict, Tuple, Union, TypeVar, Callable, Any, Type
from enum import Enum

class TokenAbstract:
    def __init__(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")
    
    def match(self, text: str) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    def generate_value(self, text: str) -> Union[str, int]:
        raise NotImplementedError("Subclasses must implement this method")
    
    def to_tokens(self) -> List[Any]:
        raise NotImplementedError("Subclasses must implement this method")

    def ast(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")
    
    def node_type(self) -> str:
        return self.__class__.__name__

class GeneratedASTObject:
    def __init__(self, name: str, value: Any) -> None:
        self.name: str = name
        self.value: Any = value

    def ast(self) -> Dict[str, Any]:
        if hasattr(self.value, 'ast'):
            return {
                "name": self.name,
                "value": self.value.ast()
            }
        return {
            "name": self.name,
            "value": self.value
        }

class Grammar:
    def __init__(self, name: str) -> None:
        self.name: str = name
        
    def ignore(self) -> Tuple[Any, ...]:
        return tuple()

    def content(self, tokens: GeneratedASTObject) -> Dict[str, Any]:
        return tokens.ast()

class Literal(TokenAbstract):
    def __init__(self, value: str) -> None:
        self.value: str = value
        self.name: str = "Literal"
    
    def match(self, text: str) -> bool:
        return text == self.value

    def to_tokens(self) -> List[str]:
        return [self.value]
    
    def ast(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "value": self.value
        }

class Number(TokenAbstract):
    def __init__(self) -> None:
        self.name: str = "Number"
    
    def match(self, text: str) -> bool:
        return text.isdigit()

    def generate_value(self, text: str) -> int:
        return int(text)

    def to_tokens(self) -> List[str]:
        return [r'\d+']

class String(TokenAbstract):
    def __init__(self) -> None:
        self.name: str = "String"
    
    def match(self, text: str) -> bool:
        return isinstance(text, str)

    def generate_value(self, text: str) -> str:
        return text

    def to_tokens(self) -> List[str]:
        return [r'\".*?\"']

class Dependency(TokenAbstract):
    def __init__(self, decorated_class: TokenAbstract) -> None:
        self.decorated_class: TokenAbstract = decorated_class
        self.name: str = "Dependency"
    
    def match(self, text: str) -> bool:
        return self.decorated_class.match(text)
    
    def generate_value(self, text: str) -> Union[str, int]:
        return self.decorated_class.generate_value(text)

    def to_tokens(self) -> List[Any]:
        return self.decorated_class.to_tokens()

T = TypeVar('T')
def grammar(lexical_rule: TokenAbstract) -> Callable[[Type[T]], Type[T]]:
    """
    Define a grammar for a class.
    """
    def decorator(cls: Type[T]) -> Type[T]:
        cls.lexical_rule_root = lexical_rule
        return cls
    return decorator

class Or(TokenAbstract):
    def __init__(self, *rules: TokenAbstract) -> None:
        self.rules: Tuple[TokenAbstract, ...] = rules

    def match(self, text: str) -> bool:
        return any(rule.match(text) for rule in self.rules)

    def to_tokens(self) -> List[List[Any]]:
        return [rule.to_tokens() for rule in self.rules]
    
    def ast(self) -> Dict[str, Any]:
        return {
            "name": "Or",
            "rules": [rule.ast() for rule in self.rules]
        }
    
class Optional(TokenAbstract):
    def __init__(self, rule: TokenAbstract) -> None:
        self.rule: TokenAbstract = rule

    def match(self, text: str) -> bool:
        return self.rule.match(text) or text == ""

    def to_tokens(self) -> List[List[Any]]:
        return [self.rule.to_tokens()]
    
    def ast(self) -> Dict[str, Any]:
        return {
            "name": "Optional",
            "rule": self.rule.ast()
        }
    
class GenericMinmax(TokenAbstract):
    def __init__(self, rule: TokenAbstract, min_count: int = 0, max_count: int = 0) -> None:
        self.rule: TokenAbstract = rule
        self.min_count: int = min_count
        self.max_count: int = max_count

    def match(self, text: str) -> bool:
        return self.rule.match(text)

    def to_tokens(self) -> List[List[Any]]:
        return [self.rule.to_tokens()]
    
    def ast(self) -> Dict[str, Any]:
        return {
            "name": "Minmax",
            "rule": self.rule.ast(),
            "min_count": self.min_count,
            "max_count": self.max_count
        }

def either(*rules: TokenAbstract) -> Or:
    """
    Matches any of the provided rules.
    """
    return Or(*rules)

def option(rule: TokenAbstract) -> Optional:
    """
    Matches a rule zero or one time.
    """
    return Optional(rule)

def minmax(rule: TokenAbstract, min_count: int = 0, max_count: int = 0) -> GenericMinmax:
    """
    Matches a minimum-to-maximum number of times.
    """
    return GenericMinmax(rule, min_count, max_count)

class RegExp(TokenAbstract):
    def __init__(self, pattern: str) -> None:
        self.pattern: str = pattern
        self.name: str = "RegExp"
    
    def match(self, text: str) -> bool:
        import re
        return bool(re.match(self.pattern, text))

    def generate_value(self, text: str) -> str:
        return text

    def to_tokens(self) -> List[str]:
        return [self.pattern]
    
    def ast(self) -> Dict[str, str]:
        return {
            "name": "RegExp",
            "pattern": self.pattern
        }
    
class Me(TokenAbstract):
    def __init__(self) -> None:
        self.name: str = "Me"
    
    def match(self, text: str) -> bool:
        return False
    
    def generate_value(self, text: str) -> str:
        return text

    def to_tokens(self) -> List[Any]:
        return []
    
    def ast(self) -> Dict[str, str]:
        return {
            "name": "Me"
        }

class Conjoined(TokenAbstract):
    def __init__(self, *rules: TokenAbstract) -> None:
        self.rules: Tuple[TokenAbstract, ...] = rules

    def match(self, text: str) -> bool:
        return all(rule.match(text) for rule in self.rules)
    
    def generate_value(self, text: str) -> str:
        return "".join(rule.generate_value(text) for rule in self.rules)

    def to_tokens(self) -> List[List[Any]]:
        return [rule.to_tokens() for rule in self.rules]
    
    def ast(self) -> Dict[str, Any]:
        return {
            "name": "Conjoined",
            "rules": [rule.ast() for rule in self.rules]
        }
    
def joined(*rules: TokenAbstract) -> Conjoined:
    """
    Matches a sequence of rules.
    """
    return Conjoined(*rules)

class NodeTypeEnum(Enum):
    """
    Abstract class for node types.
    """
    LITERAL: str = "Literal"
    NUMBER: str = "Number"
    STRING: str = "String"
    DEPENDENCY: str = "Dependency"
    OR: str = "Or"
    OPTIONAL: str = "Optional"
    REGEXP: str = "RegExp"
    ME: str = "Me"
    CONJOINED: str = "Conjoined"
    MINMAX: str = "GenericMinmax"