from ..parser import Parser
from ..abstract import Grammar, grammar, minmax, joined, either, Literal, RegExp, option

@grammar(
    joined(
        minmax(1)(
            joined(
                either(
                    joined(
                        RegExp(r"[A-Z]"),
                        RegExp(r"[a-z]+"),
                    ).with_name("Formal"),
                    RegExp(r"[a-z]+").with_name("Word")
                ),
                option(
                    Literal(",")
                ).with_name("Punctuation"),
                option(
                    Literal(" ")
                ).with_name("Whitespace"),
            )
        ),
        either(
            Literal("."),
            Literal("!"),
            Literal("?")
        ).with_name("EndPunctuation"),
    )
)
class EnglishSentenceParser(Grammar):
    name = "EnglishSentenceParser"

    def ignore(self):
        return ()
    

def test_answer():
    strings = [
        "Hello, world!",
        "This is a test.",
        "How are you?",
        "I am fine.",
        "What about you?",
        "This is a test sentence.",
        "This is another test sentence.",
        "This is yet another test sentence.",
        "This is the last test sentence.",
        "This! Should not, !parse."
    ]

    parser = Parser(EnglishSentenceParser)

    asts = []

    for string in strings:
        print(f"Parsing: {string}")
        result = parser.parse(string)
        assert result

        ast = result.ast()
        assert isinstance(ast, dict)
        print(f"AST: {ast}")
        
        asts.append(ast)