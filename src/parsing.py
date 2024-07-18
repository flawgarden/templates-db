from pathlib import Path
from typing import List, Tuple, Callable, TypeVar

import template
from template import TmtFileKind
from console import Console

try:
    import antlr4
    from antlr4 import Token, ParserRuleContext
    from antlr4.error.ErrorListener import ErrorListener
except ImportError:
    print("antlr4 not found, use 'pip install -r requirements.txt'")
    exit(1)

try:
    from generated.TemplateParser import TemplateParser
    from generated.TemplateLexer import TemplateLexer
except ImportError:
    print("Generated code not found, use './antlr.sh --generate'")
    exit(1)

T = TypeVar("T")
V = TypeVar("V")


class ParsingException(Exception):

    def __init__(self, msg, line: int = -1, pos: int = -1):
        super().__init__(msg)
        self.line = line
        self.pos = pos
        self.msg = msg


def get_kind(path: Path) -> TmtFileKind | None:
    assert path.is_file()
    match path.suffix:
        case ".unsupported":
            return TmtFileKind.UNSUPPORTED
        case ".todo":
            return TmtFileKind.TODO
        case ".tmt":
            return TmtFileKind.TMT
        case _:
            return None


class ExceptionErrorListener(ErrorListener):

    def __init__(self):
        super(ExceptionErrorListener, self).__init__()

    def syntaxError(self, recognizer, offending_symbol, line, column, msg, e):
        raise ParsingException(f"Syntax error at line {line}:{column}: {msg}", line, column)

    def reportAmbiguity(self, recognizer, dfa, start_index, stop_index, exact, alts, configs):
        pass

    def reportAttemptingFullContext(self, recognizer, dfa, start_index, stop_index, alts, configs):
        pass

    def reportContextSensitivity(self, recognizer, dfa, start_index, stop_index, prediction, configs):
        pass


class TemplateTracingLexer(TemplateLexer):

    def pushMode(self, m: int):
        super().pushMode(m)
        self.mode_stack.append(self.modeNames[m])
        Console.warn(f"PUSH: {self.mode_stack}")

    def popMode(self):
        result = super().popMode()
        self.mode_stack.pop()
        Console.warn(f"POP: {self.mode_stack}")
        return result

    def trace(self):
        self.mode_stack = []
        t = self.nextToken()
        while t.type != Token.EOF:
            t = self.nextToken()
            token_type = t.type
            token_text = t.text
            Console.warn(f"Type: {self.symbolicNames[token_type]} Token: {token_text}")


def print_tokens(text: str):
    Console.warn("------------TOKENS START-------------")
    input_stream = antlr4.InputStream(text)
    lexer = TemplateTracingLexer(input_stream)
    lexer.trace()
    Console.warn("------------TOKENS END-------------")


class Parser:

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._deleted_lines = []
        self._current_file = None

    def _get_origin_line_n(self, line: int) -> int:
        shift = 0
        for deleted_line in sorted(self._deleted_lines):
            if deleted_line <= line + shift:
                shift += 1
        return line + shift

    def _contains_error(self, ctx: ParserRuleContext) -> bool:
        start_line = self._get_origin_line_n(ctx.start.line)
        end_line = self._get_origin_line_n(ctx.stop.line)
        for deleted_line in self._deleted_lines:
            if start_line <= deleted_line <= end_line:
                return True
        return False

    def _delete_line(self, t: str, n: int) -> str:
        self._deleted_lines.append(self._get_origin_line_n(n))
        lines = t.split("\n")
        lines.pop(n - 1)
        return "\n".join(lines)

    @staticmethod
    def _map_option(f: Callable[[T], V | None], lst: List[T], ) -> List[V]:
        result = []
        for t in lst:
            r = f(t)
            if r is not None:
                result.append(r)
        return result

    @staticmethod
    def with_error_recovery(parse: Callable[["Parser", str, T], T]):
        def wrapper(self: "Parser", text: str, default_value: T) -> T:
            self._deleted_lines = []
            current_text = text
            finished = False
            result = None

            while not finished:
                try:
                    if current_text != "":
                        result = parse(self, current_text, default_value)
                    finished = True
                except ParsingException as e:
                    if len(self._deleted_lines) == 0:
                        Console.err(f"ERROR: {e.msg}, [{self._current_file}]")
                    if self.debug:
                        Console.warn(f"[TRACE] delete line {e.line}")
                    current_text = self._delete_line(current_text, e.line)

            if current_text == "":
                return default_value

            return result

        return wrapper

    def _parse_hole_body(self, ctx: TemplateParser.HoleBodyContext) -> template.Hole:
        hole_ref_ctx = ctx.holeRef()
        hole_ref = None if hole_ref_ctx is None else hole_ref_ctx.getText()
        return template.Hole(
            kind=ctx.holeKind().getText(),
            type_=ctx.holeType().getText(),
            ref=hole_ref,
        )

    def _parse_hole(self, ctx: TemplateParser.HoleContext) -> template.Hole:
        body_ctx = ctx.holeBody()
        return self._parse_hole_body(body_ctx)

    def _parse_macro_name(self, ctx: TemplateParser.MacroContext) -> str:
        return ctx.IDENTIFIER().getText()

    def _parse_code_string(self, ctx: TemplateParser.CodeStringContext) -> Tuple[str, List[str], List[template.Hole]]:
        body = ctx.getText()
        macros = Parser._map_option(self._parse_macro_name, ctx.macro())
        holes = Parser._map_option(self._parse_hole, ctx.hole())
        return body, macros, holes

    def _parse_code(self, ctx: TemplateParser.CodeContext) -> Tuple[str, List[str], List[template.Hole]]:
        body = ctx.getText()
        macros = []
        holes = []
        for code_string in ctx.codeString():
            _, s_macros, s_holes = self._parse_code_string(code_string)
            macros.extend(s_macros)
            holes.extend(s_holes)
        return body, macros, holes

    def _parse_template(self, ctx: TemplateParser.TemplateContext) -> template.Template | None:
        if self._contains_error(ctx):
            return None
        name = ctx.templateStart().IDENTIFIER().getText()
        body, macros, holes = self._parse_code(ctx.code())
        return template.Template(name, macros, holes, body)

    def _parse_extension_definition(self, ctx: TemplateParser.ExtensionDefinitionContext) -> template.Extension:
        hole = self._parse_hole_body(ctx.holeArrow().holeBody())
        body, macros, holes = self._parse_code_string(ctx.codeString())
        return template.Extension(hole, holes, body)

    def _parse_macro_definition(self, ctx: TemplateParser.MacroDefinitionContext) -> template.Macro:
        name = ctx.macroArrow().IDENTIFIER().getText()
        body, macros, holes = self._parse_code_string(ctx.codeString())
        return template.Macro(name, holes, body)

    def _parse_extension_import(self, ctx: TemplateParser.ExtensionImportContext) -> template.ExtensionImport:
        return template.ExtensionImport(ctx.IDENTIFIER().getText())

    def _parse_helper_import(self, ctx: TemplateParser.HelperImportContext) -> template.HelperImport:
        return template.HelperImport(ctx.IDENTIFIER().getText())

    def _parse_helper_class(self, ctx: TemplateParser.HelperClassContext) -> template.HelperClass:
        name = ctx.helperClassStart().IDENTIFIER().getText()
        body, macros, holes = self._parse_code(ctx.code())
        return template.HelperClass(name, body)

    def _get_parser(self, text: str) -> TemplateParser:
        if self.debug:
            print_tokens(text)
        input_stream = antlr4.InputStream(text)

        lexer = TemplateLexer(input_stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(ExceptionErrorListener())

        token_stream = antlr4.CommonTokenStream(lexer)

        parser = TemplateParser(token_stream)
        if self.debug:
            parser.setTrace(True)
        parser.removeErrorListeners()
        parser.addErrorListener(ExceptionErrorListener())

        return parser

    @staticmethod
    def _get_parents(file_path: Path) -> List[str]:
        result = []
        current_path = file_path.parent
        while current_path.parent.stem != "languages":
            result.append(current_path.stem)
            current_path = current_path.parent
        return result

    @with_error_recovery
    def _parse_template_file_text(self, text: str, default_value: template.TemplateFile) -> template.TemplateFile:
        parser = self._get_parser(text)
        template_file_ctx = parser.templateFile()

        extension_block_ctx = template_file_ctx.extensionsBlock()
        extension_imports = []
        local_extensions = []
        local_macros = []
        if extension_block_ctx is not None:
            extensions_ctx = extension_block_ctx.extensions()
            extension_imports = Parser._map_option(
                self._parse_extension_import, extension_block_ctx.extensionImports().extensionImport()
            )
            local_extensions = Parser._map_option(
                self._parse_extension_definition, extensions_ctx.extensionDefinition()
            )
            local_macros = Parser._map_option(
                self._parse_macro_definition, extensions_ctx.macroDefinition()
            )

        main_class_ctx = template_file_ctx.mainClass()
        helper_imports = Parser._map_option(self._parse_helper_import, main_class_ctx.helperImport())
        templates = Parser._map_option(self._parse_template, main_class_ctx.template())

        return template.TemplateFile(
            get_kind(self._current_file),
            self._current_file,
            self._current_file.stem,
            self._get_parents(self._current_file),
            helper_imports,
            extension_imports,
            local_extensions,
            local_macros,
            templates
        )

    def _parse_template_file(self, file_path: Path) -> template.TemplateFile:
        self._current_file = file_path
        kind = get_kind(file_path)
        empty_file = template.TemplateFile(
            kind,
            file_path,
            file_path.stem,
            self._get_parents(file_path),
            [], [], [], [], [],
        )

        if kind != TmtFileKind.TMT:
            return empty_file

        text = file_path.read_text()
        return self._parse_template_file_text(text, empty_file)

    @with_error_recovery
    def _parse_extension_file_text(self, text: str, default_value: template.ExtensionFile) -> template.ExtensionFile:
        parser = self._get_parser(text)
        extensions_ctx = parser.extensions()

        extensions = Parser._map_option(self._parse_extension_definition, extensions_ctx.extensionDefinition())
        macros = Parser._map_option(self._parse_macro_definition, extensions_ctx.macroDefinition())

        return template.ExtensionFile(
            get_kind(self._current_file),
            self._current_file,
            self._current_file.stem,
            self._get_parents(self._current_file),
            extensions,
            macros,
        )

    def _parse_extension_file(self, file_path: Path) -> template.ExtensionFile:
        self._current_file = file_path
        kind = get_kind(file_path)
        empty_file = template.ExtensionFile(
            kind,
            file_path,
            file_path.stem,
            self._get_parents(file_path),
            [], [],
        )

        if kind != TmtFileKind.TMT:
            return empty_file

        text = file_path.read_text()
        return self._parse_extension_file_text(text, empty_file)

    @with_error_recovery
    def _parse_helper_file_text(self, text: str, default_value: template.HelperFile) -> template.HelperFile:
        parser = self._get_parser(text)
        helper_file_ctx = parser.helperFile()
        helper_class = self._parse_helper_class(helper_file_ctx.helperClass())

        return template.HelperFile(
            get_kind(self._current_file),
            self._current_file,
            self._current_file.stem,
            self._get_parents(self._current_file),
            helper_class,
        )

    def _parse_helper_file(self, file_path: Path) -> template.HelperFile:
        self._current_file = file_path
        kind = get_kind(file_path)
        empty_file = template.HelperFile(
                kind,
                file_path,
                file_path.stem,
                self._get_parents(file_path),
                None
            )

        if kind != TmtFileKind.TMT:
            return empty_file

        text = file_path.read_text()
        return self._parse_helper_file_text(text, empty_file)

    @staticmethod
    def _traverse(path: Path, exclude: List[Path] | None = None) -> List[Path]:
        if exclude is not None and path in exclude:
            return []
        elif path.is_dir():
            result = []
            for p in path.iterdir():
                result.extend(Parser._traverse(p, exclude))
            return result
        elif path.is_file():
            if get_kind(path) is None:
                raise ParsingException(f"Unexpected file extension (expected .tmt .todo .unsupported): {path}")
            return [path]
        else:
            assert False

    def parse_project(self, path: Path) -> template.LanguageProject:
        assert path.is_dir()

        helpers_dir_name = "helpers"
        extensions_dir_name = "extensions"

        helpers_path = path.joinpath(helpers_dir_name)
        if not helpers_path.exists():
            raise ParsingException(f"Helpers path doesn't exist {path}")

        extensions_path = path.joinpath(extensions_dir_name)
        if not extensions_path.exists():
            raise ParsingException(f"Extensions path doesn't exist {path}")

        template_files = self._traverse(path, exclude=[helpers_path, extensions_path])
        helper_files = self._traverse(helpers_path)
        extension_files = self._traverse(extensions_path)

        Console.info(f"[{path.stem}] Start project parsing")
        templates: List[template.TemplateFile] = Parser._map_option(self._parse_template_file, template_files)
        helpers: List[template.HelperFile] = Parser._map_option(self._parse_helper_file, helper_files)
        extensions: List[template.ExtensionFile] = Parser._map_option(self._parse_extension_file, extension_files)
        Console.info(f"[{path.stem}] Finished project parsing")
        name = f"{path.stem}"

        return template.LanguageProject(name, templates, helpers, extensions)
