from ..parser import Parser
from ..abstract import Grammar, grammar, minmax, joined, either, Literal, RegExp
from ..parser import Parser, ParseResult
from ..walk import TypedASTWalker, WalkContext
from typing import Dict, Any, List

class StructuredOutput:
    def __init__(self, elements: List[Dict[str, Dict | List[str] | str]]):
        self.elements = elements

class TypedTransformer:
    def __init__(self):
        self.walker = TypedASTWalker(StructuredOutput)
        self.handlers()
    
    def handlers(self):
        @self.walker.for_node("CommandLineParser")
        def handle_command_line_parser(walker, node: Dict[str, Any], ctx: WalkContext) -> StructuredOutput:
            print("CommandLineParser (PARENT)")
            processed_values = node.get("processed_value", [])
            return StructuredOutput(elements=processed_values)
        
        @self.walker.for_node("Minmax")
        def handle_minmax(walker, node: Dict[str, Any], ctx: WalkContext) -> List[Any]:
            print(" " * ctx.level, "Minmax", node)
            return node.get("processed_value", [])
        
        @self.walker.for_node("Or")
        def handle_or(walker, node: Dict[str, Any], ctx: WalkContext) -> Any:
            print(" " * ctx.level, "Or", node)
            return node.get("processed_value", [])
            
        @self.walker.for_node("Conjoined")
        def handle_conjoined(walker, node: Dict[str, Any], ctx: WalkContext) -> Any:
            print(" " * ctx.level, "Conjoined", node)
            return node.get("processed_value", [])
            
        @self.walker.for_node("Literal")
        def handle_literal(walker, node: Dict[str, Any], ctx: WalkContext) -> str:
            print(" " * ctx.level, "Literal", node)
            return node["value"]
            
        @self.walker.for_node("RegExp")
        def handle_regexp(walker, node: Dict[str, Any], ctx: WalkContext) -> str:
            print(" " * ctx.level, "RegExp", node)

            return node["value"]
            
        return [
            handle_command_line_parser,
            handle_minmax,
            handle_or,
            handle_conjoined,
            handle_literal,
            handle_regexp
        ]

    def transform(self, parse_result: ParseResult) -> StructuredOutput:
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
    minmax(1)(
        either(
            option_with_value,
            flag,
            string
        )
    )
)
class CommandLineParser(Grammar):
    name = "CommandLineParser"

    def ignore(self):
        return ()


def test_answer():
    strings = [
        "python -m src.parser --help",
        "python -m src.parser --help --verbose",
        "echo 'Hello, World!' --flag",
        "python -m src.parser --help --verbose --flag --option=value --another-option 'arg1' 'arg2'",
    ]

    parser = Parser(CommandLineParser)
    transformer = TypedTransformer()

    asts = []

    for string in strings:
        print(f"Parsing: {string}")
        result = parser.parse(string)
        assert result
        print(result)

        transformed_result = transformer.transform(result)
        print("Transformed Result:", transformed_result)

        assert isinstance(transformed_result, StructuredOutput)

        asts.append(transformed_result)

    return asts