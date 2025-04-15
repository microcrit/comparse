from src.parser import Parser
from src.abstract import Grammar, grammar, minmax, joined, either, Literal, RegExp
from src.parser import Parser, ParseResult
from src.walk import ASTWalker, TypedASTWalker
from typing import Dict, Any, List

class StructuredOutput:
    def __init__(self, elements: List[Dict[str, Dict | List[str] | str]]):
        self.elements = elements

has_handled_root = False
has_handled_node = False
has_handled_regexp = False

class TypedTransformer:
    def __init__(self):
        self.walker = TypedASTWalker(StructuredOutput)
        self.handlers()
    
    def handlers(self):
        @self.walker.for_node("CommandLineParser")
        def handle_command_line_parser(walker, node: Dict[str, Any]) -> StructuredOutput:
            global has_handled_root
            if has_handled_root:
                raise ValueError("CommandLineParser can only be handled once.")
            has_handled_root = True
            print("Handling CommandLineParser")
            return StructuredOutput(elements=node["value"])
        @self.walker.for_node("String")
        def handle_string(walker, node: Dict[str, Any]) -> str:
            global has_handled_node
            has_handled_node = True
            print("Handling String")
            return node["value"]
        @self.walker.for_node("Literal")
        def handle_literal(walker, node: Dict[str, Any]) -> str:
            print("Handling Literal")
            return node["value"]
        @self.walker.for_node("RegExp")
        def handle_regexp(walker, node: Dict[str, Any]) -> str:
            global has_handled_regexp
            has_handled_regexp = True
            print("Handling RegExp")
            return node["value"]
        return [
            handle_command_line_parser,
            handle_string,
            handle_literal,
            handle_regexp
        ]

    def transform(self, parse_result: ParseResult) -> StructuredOutput:
        """Transform a ParseResult into a StructuredOutput object."""
        return self.walker.walk(parse_result)


string = either(
    joined(
        Literal('"'),
        RegExp(r'(?:[^\\"]|\\"|\\\\)*'),
        Literal('"')
    ),
    joined(
        Literal("'"),
        RegExp(r"(?:[^\\']|\\\'|\\\\)*"),
        Literal("'")
    ),
    RegExp(r"[^\s=]+")
)

flag = joined(
    either(Literal("-"), Literal("--")),
    RegExp(r"[a-zA-Z][\w\-]*")
)

option_with_value = joined(
    either(Literal("-"), Literal("--")),
    RegExp(r"[a-zA-Z][\w\-]*"),
    either(
        joined(Literal("="), string),
        joined(Literal(" "), string)
    )
)

@grammar(
    minmax(
        either(
            option_with_value,
            flag,
            string
        ),
        min_count=1
    )
)
class CommandLineParser(Grammar):
    """
    A parser for command line arguments.
    """
    def __init__(self):
        super().__init__("CommandLineParser")
        self.ast = None

    def ignore(self):
        return ()


def test_answer():
    x = Parser(CommandLineParser).parse('python -m src.parser --help').ast()
    assert x
    print(x)

    y = TypedTransformer().transform(x)
    assert y
    print(y)

    assert isinstance(y, StructuredOutput)

    assert has_handled_root
    assert has_handled_node
    assert has_handled_regexp