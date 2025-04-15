from typing import List, Dict, Tuple, Union, Any, Optional as OptionalType, Type

from .abstract import (
    GeneratedASTObject,
    Number,
    String,
    Literal,
    RegExp,
    Optional,
    Or,
    Conjoined,
    Me,
    Dependency,
    TokenAbstract,
    Grammar,
    GenericMinmax
)

class ASTNode:
    def __init__(self, node_type: str, value: Any = None) -> None:
        self.name: str = node_type
        self.value: Union[List[Any], Any] = value or []
    
    def ast(self) -> Dict[str, Any]:
        """
        Convert the ASTNode to an AST (dictionary) representation, with child ASTNodes being also converted.
        """
        if isinstance(self.value, list):
            return {
                "name": self.name,
                "value": [item.ast() if isinstance(item, ASTNode) else item for item in self.value]
            }
        elif isinstance(self.value, ASTNode):
            return {
                "name": self.name,
                "value": self.value.ast()
            }
        elif isinstance(self.value, dict) and self.value.get('name') and self.value.get('value'):
            values_sub = self.value['value']
            return {
                "name": self.name,
                "value": [x.ast() if isinstance(x, ASTNode) else x for x in values_sub]
            }
        else:
            return {
                "name": self.name,
                "value": self.value
            }

class ParseResult:
    def __init__(self, value: Any, remaining: str = "") -> None:
        self.value: Any = value
        self.remaining: str = remaining
    
    def ast(self) -> Any:
        """
        Convert the ParseResult to an AST (dictionary) representation, with child ASTNodes being also converted.
        """
        if isinstance(self.value, dict):
            return self.value
        if isinstance(self.value, list):
            return [item.ast() if isinstance(item, ASTNode) else item for item in self.value]
        elif isinstance(self.value, ASTNode):
            return self.value.ast()
        elif isinstance(self.value, dict) and self.value.get('name') and self.value.get('value'):
            values_sub = self.value['value']
            return list(map(lambda x: x.ast() if isinstance(x, ASTNode) else x, values_sub))
        else:
            return self.value or None

class Parser:
    def __init__(self, grammar_class: Type[Grammar]) -> None:
        self.grammar_class: Type[Grammar] = grammar_class
        self.grammar_instance: Grammar = grammar_class()
        self.ignore_rules: Tuple[Any, ...] = self.grammar_instance.ignore()
    
    def _parse_optional(self, text: str, rule: Optional) -> OptionalType[ParseResult]:
        result: OptionalType[ParseResult] = self._apply_rule(text, rule.rule)
        if result:
            node: ASTNode = ASTNode("Optional", value=[result.value])
            return ParseResult(node, result.remaining)
        return ParseResult(ASTNode("Optional", value=[None]), text)
    
    def _parse_minmax(self, text: str, rule: GenericMinmax) -> OptionalType[ParseResult]:
        current_text: str = text.strip()  # Strip leading whitespace
        values: List[Any] = []
        
        for _ in range(rule.min_count):
            result: OptionalType[ParseResult] = self._apply_rule(current_text, rule.rule)
            if not result:
                return None
            values.append(result.value)
            current_text = result.remaining.strip()
        
        if rule.max_count == 0:
            while current_text:
                result: OptionalType[ParseResult] = self._apply_rule(current_text, rule.rule)
                if not result:
                    break
                values.append(result.value)
                current_text = result.remaining.strip()
                
                if result.remaining == text:
                    break
        else:
            for _ in range(rule.max_count - rule.min_count):
                result: OptionalType[ParseResult] = self._apply_rule(current_text, rule.rule)
                if not result:
                    break
                values.append(result.value)
                current_text = result.remaining.strip()
        
        return ParseResult(ASTNode("Minmax", value=values), current_text)

    def _parse_conjoined(self, text: str, rule: Conjoined) -> OptionalType[ParseResult]:
        current_text: str = text
        values: List[Any] = []
        
        for sub_rule in rule.rules:
            result: OptionalType[ParseResult] = self._apply_rule(current_text, sub_rule)
            if not result:
                return None
            values.append(result.value)
            current_text = result.remaining
        
        return ParseResult(ASTNode("Conjoined", value=values), current_text)

    def _parse_or(self, text: str, rule: Or) -> OptionalType[ParseResult]:
        for sub_rule in rule.rules:
            result: OptionalType[ParseResult] = self._apply_rule(text, sub_rule)
            if result:
                node: ASTNode = ASTNode("Or", value=[result.value])
                return ParseResult(node, result.remaining)
        return None

    def _apply_rule(self, text: str, rule: TokenAbstract) -> OptionalType[ParseResult]:
        if isinstance(rule, Number):
            return self._parse_number(text)
        elif isinstance(rule, String):
            return self._parse_string(text)
        elif isinstance(rule, Literal):
            return self._parse_literal(text, rule)
        elif isinstance(rule, RegExp):
            return self._parse_regexp(text, rule)
        elif isinstance(rule, Optional):
            return self._parse_optional(text, rule)
        elif isinstance(rule, Or):
            return self._parse_or(text, rule)
        elif isinstance(rule, Conjoined):
            return self._parse_conjoined(text, rule)
        elif isinstance(rule, Me):
            return self._parse_with_rules(text, self.grammar_class.lexical_rule_root)
        elif isinstance(rule, Dependency):
            return self._apply_rule(text, rule.decorated_class)
        elif isinstance(rule, GenericMinmax):
            return self._parse_minmax(text, rule)
        else:
            raise ValueError(f"Unsupported rule type: {type(rule)}")

    def parse(self, text: str) -> ParseResult:
        """
        Parse the input text using the defined grammar rules.
        """
        text = self._clean_text(text)
        
        result: OptionalType[ParseResult] = self._parse_with_rules(text, self.grammar_class.lexical_rule_root)
        if not result:
            raise ValueError(f"Failed to parse: {text}")
            
        if isinstance(result.value, list):
            parsed_values: List[Any] = result.value
        else:
            parsed_values: List[Any] = [result.value]
        
        ast_data: Dict[str, Any] = self.grammar_instance.content(
            GeneratedASTObject(self.grammar_instance.name, parsed_values)
        )
        
        if hasattr(self.grammar_instance, 'transform'):
            transformed_data = self.grammar_instance.transform(parsed_values)
            return ParseResult(transformed_data)
        
        return ParseResult(ast_data)
    
    def _clean_text(self, text: str) -> str:
        for rule in self.ignore_rules:
            if isinstance(rule, Literal):
                text = text.replace(rule.value, '')
        return text
    
    def _parse_with_rules(self, text: str, rule: Any) -> OptionalType[ParseResult]:
        """Parse the input text using the specified rule or rules."""
        if isinstance(rule, list):
            current_text: str = text
            values: List[Any] = []
            
            for r in rule:
                result: OptionalType[ParseResult] = self._apply_rule(current_text, r)
                if not result:
                    return None
                values.append(result.value)
                current_text = result.remaining
            
            return ParseResult(values, current_text)
        else:
            return self._apply_rule(text, rule)
        
    def _parse_number(self, text: str) -> OptionalType[ParseResult]:
        import re
        match = re.match(r'\d+', text)
        if match:
            matched_text: str = match.group(0)
            node: ASTNode = ASTNode("Number", value=int(matched_text))
            return ParseResult(node, text[len(matched_text):])
        return None
    
    def _parse_string(self, text: str) -> OptionalType[ParseResult]:
        import re
        match = re.match(r'\"(.*?)\"', text)
        if match:
            matched_text: str = match.group(1)
            full_match: str = match.group(0)
            node: ASTNode = ASTNode("String", value=matched_text)
            return ParseResult(node, text[len(full_match):])
        return None
    
    def _parse_literal(self, text: str, rule: Literal) -> OptionalType[ParseResult]:
        text = text.strip()
        if text.startswith(rule.value):
            node: ASTNode = ASTNode("Literal", value=rule.value)
            return ParseResult(node, text[len(rule.value):])
        return None

    def _parse_regexp(self, text: str, rule: RegExp) -> OptionalType[ParseResult]:
        import re
        text = text.strip()
        match = re.match(rule.pattern, text)
        if match:
            matched_text: str = match.group(0)
            node: ASTNode = ASTNode("RegExp", value=matched_text)
            return ParseResult(node, text[len(matched_text):])
        return None