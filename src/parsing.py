from pathlib import Path
from typing import List, Tuple

import template
from template import TmtFileKind
from console import Console

try:
    import antlr4
    from antlr4 import Token
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

DEBUG_PARSING = False


class ParsingException(Exception):

    def __init__(self, msg):
        super().__init__(msg)
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
        raise ParsingException(f"Syntax error at line {line}:{column}: {msg}")

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
        print(f"PUSH: {self.mode_stack}")

    def popMode(self):
        result = super().popMode()
        self.mode_stack.pop()
        print(f"POP: {self.mode_stack}")
        return result

    def trace(self):
        self.mode_stack = []
        t = self.nextToken()
        while t.type != Token.EOF:
            t = self.nextToken()
            token_type = t.type
            token_text = t.text
            print(f"Type: {self.symbolicNames[token_type]} Token: {token_text}")


def print_tokens(text: str):
    print("------------TOKENS START-------------")
    input_stream = antlr4.InputStream(text)
    lexer = TemplateTracingLexer(input_stream)
    lexer.trace()
    print("------------TOKENS END-------------")


def parse_hole_body(ctx: TemplateParser.HoleBodyContext) -> template.Hole:
    hole_ref_ctx = ctx.holeRef()
    hole_ref = None if hole_ref_ctx is None else hole_ref_ctx.getText()
    return template.Hole(
        kind=ctx.holeKind().getText(),
        type_=ctx.holeType().getText(),
        ref=hole_ref,
    )


def parse_hole(ctx: TemplateParser.HoleContext) -> template.Hole:
    body_ctx = ctx.holeBody()
    return parse_hole_body(body_ctx)


def parse_macro_name(ctx: TemplateParser.MacroContext) -> str:
    return ctx.IDENTIFIER().getText()


def parse_code_string(ctx: TemplateParser.CodeStringContext) -> Tuple[str, List[str], List[template.Hole]]:
    body = ctx.getText()
    macros = list(map(parse_macro_name, ctx.macro()))
    holes = list(map(parse_hole, ctx.hole()))
    return body, macros, holes


def parse_code(ctx: TemplateParser.CodeContext) -> Tuple[str, List[str], List[template.Hole]]:
    body = ctx.getText()
    macros = []
    holes = []
    for code_string in ctx.codeString():
        _, s_macros, s_holes = parse_code_string(code_string)
        macros.extend(s_macros)
        holes.extend(s_holes)
    return body, macros, holes


def parse_template(ctx: TemplateParser.TemplateContext) -> template.Template:
    name = ctx.templateStart().IDENTIFIER().getText()
    body, macros, holes = parse_code(ctx.code())
    return template.Template(name, macros, holes, body)


def parse_extension_definition(ctx: TemplateParser.ExtensionDefinitionContext) -> template.Extension:
    hole = parse_hole_body(ctx.holeArrow().holeBody())
    body, macros, holes = parse_code_string(ctx.codeString())
    return template.Extension(hole, holes, body)


def parse_macro_definition(ctx: TemplateParser.MacroDefinitionContext) -> template.Macro:
    name = ctx.macroArrow().IDENTIFIER().getText()
    body, macros, holes = parse_code_string(ctx.codeString())
    return template.Macro(name, holes, body)


def parse_extension_import(ctx: TemplateParser.ExtensionImportContext) -> template.ExtensionImport:
    return template.ExtensionImport(ctx.IDENTIFIER().getText())


def parse_helper_import(ctx: TemplateParser.HelperImportContext) -> template.HelperImport:
    return template.HelperImport(ctx.IDENTIFIER().getText())


def parse_helper_class(ctx: TemplateParser.HelperClassContext) -> template.HelperClass:
    name = ctx.helperClassStart().IDENTIFIER().getText()
    body, macros, holes = parse_code(ctx.code())
    return template.HelperClass(name, body)


def get_parser(text: str) -> TemplateParser:
    if DEBUG_PARSING:
        print_tokens(text)
    input_stream = antlr4.InputStream(text)

    lexer = TemplateLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(ExceptionErrorListener())

    token_stream = antlr4.CommonTokenStream(lexer)

    parser = TemplateParser(token_stream)
    if DEBUG_PARSING:
        parser.setTrace(True)
    parser.removeErrorListeners()
    parser.addErrorListener(ExceptionErrorListener())

    return parser


def get_parents(file_path: Path) -> List[str]:
    result = []
    current_path = file_path.parent
    while current_path.parent.stem != "languages":
        result.append(current_path.stem)
        current_path = current_path.parent
    return result


def with_wrapping(path: Path, action):
    try:
        return action(())
    except ParsingException as e:
        raise ParsingException(f"{path}, {e.msg}")


def parse_template_file(file_path: Path) -> template.TemplateFile:
    if (kind := get_kind(file_path)) != TmtFileKind.TMT:
        return template.TemplateFile(
            kind,
            file_path,
            file_path.stem,
            get_parents(file_path),
            [], [], [], [], [],
        )

    text = file_path.read_text()
    parser = get_parser(text)
    template_file_ctx = with_wrapping(file_path, lambda _: parser.templateFile())

    extension_block_ctx = template_file_ctx.extensionsBlock()
    extension_imports = []
    local_extensions = []
    local_macros = []
    if extension_block_ctx is not None:
        extensions_ctx = extension_block_ctx.extensions()
        extension_imports = list(map(parse_extension_import, extension_block_ctx.extensionImports().extensionImport()))
        local_extensions = list(map(parse_extension_definition, extensions_ctx.extensionDefinition()))
        local_macros = list(map(parse_macro_definition, extensions_ctx.macroDefinition()))

    main_class_ctx = template_file_ctx.mainClass()
    helper_imports = list(map(parse_helper_import, main_class_ctx.helperImport()))
    templates = list(map(parse_template, main_class_ctx.template()))

    return template.TemplateFile(
        kind,
        file_path,
        file_path.stem,
        get_parents(file_path),
        helper_imports,
        extension_imports,
        local_extensions,
        local_macros,
        templates
    )


def parse_extension_file(file_path: Path) -> template.ExtensionFile:
    if (kind := get_kind(file_path)) != TmtFileKind.TMT:
        return template.ExtensionFile(
            kind,
            file_path,
            file_path.stem,
            get_parents(file_path),
            [], [],
        )

    text = file_path.read_text()
    parser = get_parser(text)
    extensions_ctx = with_wrapping(file_path, lambda _: parser.extensions())

    extensions = list(map(parse_extension_definition, extensions_ctx.extensionDefinition()))
    macros = list(map(parse_macro_definition, extensions_ctx.macroDefinition()))

    return template.ExtensionFile(
        kind,
        file_path,
        file_path.stem,
        get_parents(file_path),
        extensions,
        macros,
    )


def parse_helper_file(file_path: Path) -> template.HelperFile:
    if (kind := get_kind(file_path)) != TmtFileKind.TMT:
        return template.HelperFile(
            kind,
            file_path,
            file_path.stem,
            get_parents(file_path),
            None
        )

    text = file_path.read_text()
    parser = get_parser(text)
    helper_file_ctx = with_wrapping(file_path, lambda _: parser.helperFile())
    helper_class = parse_helper_class(helper_file_ctx.helperClass())

    return template.HelperFile(
        kind,
        file_path,
        file_path.stem,
        get_parents(file_path),
        helper_class,
    )


def traverse(path: Path, exclude: List[Path] | None = None) -> List[Path]:
    if exclude is not None and path in exclude:
        return []
    elif path.is_dir():
        result = []
        for p in path.iterdir():
            result.extend(traverse(p, exclude))
        return result
    elif path.is_file():
        if get_kind(path) is None:
            raise ParsingException(f"Unexpected file extension (expected .tmt .todo .unsupported): {path}")
        return [path]
    else:
        assert False


def parse_project(path: Path) -> template.LanguageProject:
    assert path.is_dir()

    helpers_dir_name = "helpers"
    extensions_dir_name = "extensions"

    helpers_path = path.joinpath(helpers_dir_name)
    if not helpers_path.exists():
        raise ParsingException(f"Helpers path doesn't exist {path}")

    extensions_path = path.joinpath(extensions_dir_name)
    if not extensions_path.exists():
        raise ParsingException(f"Extensions path doesn't exist {path}")

    template_files = traverse(path, exclude=[helpers_path, extensions_path])
    helper_files = traverse(helpers_path)
    extension_files = traverse(extensions_path)

    Console.info(f"[{path.stem}] Start project parsing")
    templates: List[template.TemplateFile] = list(map(parse_template_file, template_files))
    helpers: List[template.HelperFile] = list(map(parse_helper_file, helper_files))
    extensions: List[template.ExtensionFile] = list(map(parse_extension_file, extension_files))
    Console.info(f"[{path.stem}] Finished project parsing")
    name = f"{path.stem}"

    return template.LanguageProject(name, templates, helpers, extensions)
