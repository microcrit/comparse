import os
import logging
from typing import Dict, Type, Any, Set, List
from pathlib import Path

from .abstract import (
    Grammar, Or, TokenAbstract, Literal, RegExp,
    Optional as OptionalToken, Conjoined, GenericMinmax
)
from .parser import Parser

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("parser_generator")

class FileManager:
    """Handles file I/O operations for the parser generator."""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> None:
        """Create directory if it doesn't exist."""
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except PermissionError:
                logger.error(f"Permission denied when creating directory {directory}")
                raise
            except Exception as e:
                logger.error(f"Error creating directory {directory}: {str(e)}")
                raise
    
    @staticmethod
    def write_file(dir_root: str, file_path: str, content: str) -> None:
        """Write content to file with error handling."""
        fl = os.path.join(dir_root, file_path)
        try:
            with open(fl, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Parser successfully written to: {fl}")
        except PermissionError:
            logger.error(f"Permission denied when writing to {fl}")
            raise
        except Exception as e:
            logger.error(f"Error writing to file {fl}: {str(e)}")
            raise

class RuleProcessor:
    """Processes grammar rules to generate rule definitions."""
    
    def __init__(self):
        self.used_rules: Set[str] = set()
    
    def process_rule(self, rule: TokenAbstract, rule_name: str = None) -> Dict[str, Any]:
        """Process a single rule and generate its definition."""
        if rule_name is None:
            rule_name = getattr(rule, '_custom_name', rule.__class__.__name__)
            
        rule_id = f"{rule_name}_{id(rule)}"
        if rule_id in self.used_rules:
            return {"rule_ref": rule_id}
        
        self.used_rules.add(rule_id)
        
        rule_def = {
            "type": rule.__class__.__name__,
            "name": rule_name,
            "id": rule_id,
        }
        
        if isinstance(rule, Literal):
            rule_def["value"] = rule.value
        elif isinstance(rule, RegExp):
            rule_def["pattern"] = rule.pattern
        elif isinstance(rule, OptionalToken):
            rule_def["rule"] = self.process_rule(rule.rule)
        elif isinstance(rule, Or):
            rule_def["rules"] = [self.process_rule(r) for r in rule.rules]
        elif isinstance(rule, Conjoined):
            rule_def["rules"] = [self.process_rule(r) for r in rule.rules]
        elif isinstance(rule, GenericMinmax):
            rule_def["rule"] = self.process_rule(rule.rule)
            rule_def["min"] = rule.min_count
            rule_def["max"] = rule.max_count
            
        return rule_def
    
    def analyze_grammar_rules(self, grammar_class: Type[Grammar]) -> Dict[str, Any]:
        """Analyze the grammar rules and return rule definitions."""
        lexical_rule_root = getattr(grammar_class, 'lexical_rule_root', None)
        if not lexical_rule_root:
            raise ValueError(f"Grammar {grammar_class.__name__} has no lexical_rule_root")
        
        return self.process_rule(lexical_rule_root)

class CodeTemplateManager:
    """Manages code templates for the generated parser."""
    
    @staticmethod
    def generate_rule_methods(rule_defs: Dict[str, Any]) -> str:
        """Generate methods for all rules in the grammar."""
        methods = []
        processed_rules = {}
        
        def process_rule_def(rule_def):
            rule_id = rule_def["id"].replace('-', '_')
            if rule_id in processed_rules:
                return
                
            processed_rules[rule_id] = True
            
            if rule_def["type"] == "Literal":
                methods.append(CodeTemplateManager._generate_literal_method(rule_def))
            elif rule_def["type"] == "RegExp":
                methods.append(CodeTemplateManager._generate_regexp_method(rule_def))
            elif rule_def["type"] == "Optional":
                methods.append(CodeTemplateManager._generate_optional_method(rule_def))
                process_rule_def(rule_def["rule"])
            elif rule_def["type"] == "Or":
                methods.append(CodeTemplateManager._generate_or_method(rule_def))
                for subrule in rule_def["rules"]:
                    if "rule_ref" not in subrule:
                        process_rule_def(subrule)
            elif rule_def["type"] == "Conjoined":
                methods.append(CodeTemplateManager._generate_conjoined_method(rule_def))
                for subrule in rule_def["rules"]:
                    if "rule_ref" not in subrule:
                        process_rule_def(subrule)
            elif rule_def["type"] == "GenericMinmax":
                methods.append(CodeTemplateManager._generate_minmax_method(rule_def))
                process_rule_def(rule_def["rule"])
        
        methods.append(
            "    def _parse_root(self, text: str) -> Optional[ParseResult]:\n"
            f"        return self._parse_{rule_defs['id'].replace('-', '_')}(text)\n\n"
        )
        
        process_rule_def(rule_defs)
        
        return "".join(methods)
    
    @staticmethod
    def _generate_literal_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        value = rule_def["value"]
        name = rule_def["name"]
        
        return (
            f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
            f"        text = text.strip()\n"
            f"        if text.startswith(\"{value}\"):\n"
            f"            node = ASTNode(\"Literal\", value=\"{value}\", custom_name=\"{name}\")\n"
            f"            return ParseResult(node, text[len(\"{value}\"):])\n"
            f"        return None\n\n"
        )
    
    @staticmethod
    def _generate_regexp_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        pattern = rule_def["pattern"].replace("\\", "\\\\")
        name = rule_def["name"]
        
        return (
            f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
            f"        text = text.strip()\n"
            f"        match = re.match(r\"{pattern}\", text)\n"
            f"        if match:\n"
            f"            matched_text = match.group(0)\n"
            f"            node = ASTNode(\"RegExp\", value=matched_text, custom_name=\"{name}\")\n"
            f"            return ParseResult(node, text[len(matched_text):])\n"
            f"        return None\n\n"
        )
    
    @staticmethod
    def _generate_optional_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        subrule_id = rule_def["rule"]["id"].replace('-', '_')
        name = rule_def["name"]
        
        return (
            f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
            f"        result = self._parse_{subrule_id}(text)\n"
            f"        if result:\n"
            f"            node = ASTNode(\"Optional\", value=[result.value], custom_name=\"{name}\")\n"
            f"            return ParseResult(node, result.remaining)\n"
            f"        return ParseResult(ASTNode(\"Optional\", value=[None], custom_name=\"{name}\"), text)\n\n"
        )
    
    @staticmethod
    def _generate_or_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        name = rule_def["name"]
        
        method = f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
        
        for i, subrule in enumerate(rule_def["rules"]):
            subrule_id = subrule.get("rule_ref", subrule["id"]).replace('-', '_')
            method += (
                f"        result{i} = self._parse_{subrule_id}(text)\n"
                f"        if result{i}:\n"
                f"            node = ASTNode(\"Or\", value=[result{i}.value], custom_name=\"{name}\")\n"
                f"            return ParseResult(node, result{i}.remaining)\n"
            )
        
        method += "        return None\n\n"
        return method
    
    @staticmethod
    def _generate_conjoined_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        name = rule_def["name"]
        
        method = (
            f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
            f"        current_text = text.strip()\n"
            f"        values = []\n\n"
        )
        
        for i, subrule in enumerate(rule_def["rules"]):
            subrule_id = subrule.get("rule_ref", subrule["id"]).replace('-', '_')
            method += (
                f"        result{i} = self._parse_{subrule_id}(current_text)\n"
                f"        if not result{i}:\n"
                f"            return None\n"
                f"        values.append(result{i}.value)\n"
                f"        current_text = result{i}.remaining\n\n"
            )
        
        method += (
            f"        node = ASTNode(\"Conjoined\", value=values, custom_name=\"{name}\")\n"
            f"        return ParseResult(node, current_text)\n\n"
        )
        
        return method
    
    @staticmethod
    def _generate_minmax_method(rule_def: Dict[str, Any]) -> str:
        rule_id = rule_def["id"].replace('-', '_')
        subrule_id = rule_def["rule"]["id"].replace('-', '_')
        name = rule_def["name"]
        min_count = rule_def["min"]
        max_count = rule_def["max"]
        
        method = (
            f"    def _parse_{rule_id}(self, text: str) -> Optional[ParseResult]:\n"
            f"        current_text = text.strip()\n"
            f"        values = []\n\n"
            f"        for _ in range({min_count}):\n"
            f"            result = self._parse_{subrule_id}(current_text)\n"
            f"            if not result:\n"
            f"                return None\n"
            f"            values.append(result.value)\n"
            f"            current_text = result.remaining.strip()\n\n"
        )
        
        if max_count == 0:
            method += (
                f"        while current_text:\n"
                f"            result = self._parse_{subrule_id}(current_text)\n"
                f"            if not result:\n"
                f"                break\n"
                f"            values.append(result.value)\n"
                f"            \n"
                f"            if current_text == result.remaining.strip():\n"
                f"                break\n"
                f"                \n"
                f"            current_text = result.remaining.strip()\n"
            )
        else:
            method += (
                f"        for _ in range({max_count} - {min_count}):\n"
                f"            result = self._parse_{subrule_id}(current_text)\n"
                f"            if not result:\n"
                f"                break\n"
                f"            values.append(result.value)\n"
                f"            current_text = result.remaining.strip()\n"
            )
        
        method += (
            f"\n        node = ASTNode(\"Minmax\", value=values, custom_name=\"{name}\")\n"
            f"        return ParseResult(node, current_text)\n\n"
        )
        
        return method
    
    @staticmethod
    def create_parser_template(grammar_name: str, rule_defs: Dict[str, Any], ignore_rules: List) -> str:
        """Create the main parser template."""
        template = (
            f"# Generated from grammar: {grammar_name}\n\n"
            "import re\n"
            "from typing import Dict, List, Any, Optional, Union, Tuple\n\n"
            "class ASTNode:\n"
            "    def __init__(self, node_type: str, value: Any = None, custom_name: str = None) -> None:\n"
            "        self.type: str = node_type\n"
            "        self.name: str = custom_name or node_type\n"
            "        self.value: Union[List[Any], Any] = value or []\n"
            "    \n"
            "    def ast(self) -> Dict[str, Any]:\n"
            "        result = {'type': self.type, 'name': self.name}\n"
            "        \n"
            "        if isinstance(self.value, list):\n"
            "            result['value'] = [item.ast() if isinstance(item, ASTNode) else item for item in self.value]\n"
            "        elif isinstance(self.value, ASTNode):\n"
            "            result['value'] = self.value.ast()\n"
            "        elif isinstance(self.value, dict) and self.value.get('name') and self.value.get('value'):\n"
            "            values_sub = self.value['value']\n"
            "            result['value'] = [x.ast() if isinstance(x, ASTNode) else x for x in values_sub]\n"
            "        else:\n"
            "            result['value'] = self.value\n"
            "        \n"
            "        return result\n\n"
            "class ParseResult:\n"
            "    def __init__(self, value: Any, remaining: str = \"\") -> None:\n"
            "        self.value: Any = value\n"
            "        self.remaining: str = remaining\n"
            "    \n"
            "    def ast(self) -> Any:\n"
            "        if isinstance(self.value, dict):\n"
            "            return self.value\n"
            "        if isinstance(self.value, list):\n"
            "            return [item.ast() if hasattr(item, 'ast') else item for item in self.value]\n"
            "        elif hasattr(self.value, 'ast'):\n"
            "            return self.value.ast()\n"
            "        else:\n"
            "            return self.value or None\n\n"
            f"class {grammar_name}Parser:\n"
            "    def __init__(self) -> None:\n"
            f"        self.ignore_rules = {repr([r.value if isinstance(r, Literal) else r for r in ignore_rules])}\n\n"
            "    def parse(self, text: str) -> ParseResult:\n"
            "        text = self._clean_text(text)\n"
            "        result = self._parse_root(text)\n"
            "        if not result:\n"
            "            raise ValueError(f\"Failed to parse: {text}\")\n"
            "        \n"
            "        if result.remaining.strip():\n"
            "            raise ValueError(f\"Failed to parse entire string. Remaining text: {result.remaining}\")\n"
            "        \n"
            "        return result\n\n"
        )

        template += CodeTemplateManager.generate_rule_methods(rule_defs)
        
        template += (
            "    def _clean_text(self, text: str) -> str:\n"
            "        for rule in self.ignore_rules:\n"
            "            if isinstance(rule, str):\n"
            "                text = text.replace(rule, '')\n"
            "        return text\n\n"
        )
        
        template += (
            "\nif __name__ == \"__main__\":\n"
            f"    parser = {grammar_name}Parser()\n"
            "    import sys\n"
            "    if len(sys.argv) > 1:\n"
            "        text = sys.argv[1]\n"
            "    else:\n"
            "        text = input(\"Enter text to parse: \")\n"
            "    result = parser.parse(text)\n"
            "    print(result.ast())\n"
        )
        
        return template

class ParserGenerator:
    """
    Generates standalone parser implementations from grammar definitions.
    """
    def __init__(self, grammar_class: Type[Grammar], output_dir: str = None) -> None:
        """
        Initialize the parser generator.
        
        Args:
            grammar_class: The grammar class to generate a parser for
            output_dir: Directory to save the generated parser file
        """
        self.grammar_class = grammar_class
        self.output_dir = output_dir or os.path.join(Path(__file__).parent.parent, "generated")
        self.parser_instance = Parser(grammar_class)
        self.ignore_rules = self.parser_instance.ignore_rules
        self.rule_processor = RuleProcessor()
        self.file_manager = FileManager()
        
    def generate(self, output_file: str = None) -> str:
        """
        Generate a standalone parser from the grammar.
        
        Args:
            output_file: Optional file path to write the parser to
            
        Returns:
            The file path where the parser was generated
        """
        try:
            self.file_manager.ensure_directory_exists(self.output_dir)
                    
            if not output_file:
                output_file = os.path.join(self.output_dir, f"{self.grammar_class.__name__}_parser.py")
            else:
                if os.path.isdir(output_file) or output_file.endswith('/'):
                    self.file_manager.ensure_directory_exists(output_file)
                    output_file = os.path.join(output_file, f"{self.grammar_class.__name__}_parser.py")
            
            parser_code = self._generate_parser_code()
            
            self.file_manager.write_file(self.output_dir, output_file, parser_code)
                
            return output_file
        except Exception as e:
            logger.error(f"Failed to generate parser: {str(e)}")
            raise
    
    def _generate_parser_code(self) -> str:
        """Generate the parser code based on the grammar rules."""
        rule_defs = self.rule_processor.analyze_grammar_rules(self.grammar_class)
        
        template = CodeTemplateManager.create_parser_template(
            self.grammar_class.__name__, 
            rule_defs, 
            self.ignore_rules
        )
        
        return template