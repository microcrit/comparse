# Comparse, Parsing to Scale

Comparse (Compliant Parser) is a research project library to build parsing infrastructure. It was outlined in a section (1) of my research paper "Reducing the Gap Between 'Computer Science' Logic and 'Mathematical' Logic."   
The design is intended to be fully fluent with Python and understandable to an average user (or even non-Python familiar mathematician). As long as you know some level of Python, you can quite simply build projects that require a parser.   
   
Though the design is fully there, the implementation is not 100% complete. Overall, parsing works "okay" in some cases, however with more complex grammars, it may fail and will not parse. 
   
Grammars (a set of rules to match and extract features from text) are defined through decorators attached to classes. The `Parser` class may specify a root grammar, which is the "parent" of all other grammars (those can be specified as dependencies of the root grammar).   
AST walkers (which transform the parsed tree into a more usable form) are also defined through decorators- those decorators being custom methods of a defined class.   

Comparse requires no external dependencies, and is optimized for minimal resource usage.

## Advantages
- *Type-safe* - The parser is optionally type-safe and strongly-typed (for AST walkers/transformers), and can be trusted for correctness.
- *Fluent* - The parser is designed to be idiomatic and fluent with Python, and is easy to use.
- *No external dependencies* - The parser is designed to be self-contained and does not require any external dependencies.
- *Dual-parsing* - The infrastructure can both parse code at runtime and generate a standalone parser from the grammar. This is useful if you aim to get a significant boost from startup performance, as decorators are not required. This is also useful if you plan to compile your code, E.G. through Nuitka.
   
## Simple Example
*I cannot trust that this works in the current state of the project.*
```python
from comparse.parser import Parser
from src.abstract import Grammar, grammar, joined, Literal

@grammar(
    joined(
        Literal("Hello"),
        Literal("World")
    )
)
class HelloWorldParser(Grammar):
    name = "HelloWorldParser"

    def ignore(self):
        return (Literal(" "))

x = Parser(HelloWorldParser).parse("Hello World").ast()
assert x
print(x)
```
   
As you can see, parsers are relatively simple to define compared to more "commercial" solutions, a la ANTLR. However, this design comes at a tradeoff of not being as powerful and not generating parsers for other languages.   
Some of these solutions are solved by compiling with Nuitka, however that's not perfect either, as decorators will be compiled as functions that must be applied to a class type (How? Not sure).   
   
This project is a dependency of the [Bass](https://github.com/microcrit/bass) algorithm-expression language which is outlined in the second section of the paper.

## Todo
### Complete
- [x] AST Walkers
- [x] Type-safety
- [x] Grammar decorators
- [x] Parser generation

### Incomplete
- [ ] Type-safe testing
- [ ] Parallel-focused, Erlang processing backend (as according to the paper)