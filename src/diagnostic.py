from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Callable, TypeVar
from console import Console
from template import LanguageProject, ProjectFile, TemplateFile, HelperFile, ExtensionFile, Extension, Hole, Template, \
    TmtFileKind


@dataclass(frozen=True)
class DiagnosticResult:
    class DiagnosticLevel(Enum):
        WARNING = 0
        ERROR = 1

    level: DiagnosticLevel
    message: str

    @staticmethod
    def warning(message: str) -> "DiagnosticResult":
        return DiagnosticResult(DiagnosticResult.DiagnosticLevel.WARNING, message)

    @staticmethod
    def error(message: str) -> "DiagnosticResult":
        return DiagnosticResult(DiagnosticResult.DiagnosticLevel.ERROR, message)


T = TypeVar("T")
TextDiagnosticFunc = Callable[[Path], List[DiagnosticResult]]
DiagnosticFunc = Callable[[List[LanguageProject]], List[DiagnosticResult]]
LanguageDiagnosticFunc = Callable[[LanguageProject], List[DiagnosticResult]]
TemplateDiagnosticFunc = Callable[[LanguageProject, TemplateFile], List[DiagnosticResult]]
ExtensionDiagnosticFunc = Callable[[LanguageProject, ExtensionFile], List[DiagnosticResult]]


@dataclass(frozen=True)
class Diagnostic:
    name: str
    perform: DiagnosticFunc


@dataclass(frozen=True)
class TextDiagnostic:
    name: str
    perform: TextDiagnosticFunc


class Nerd:

    def __init__(self):
        self._diagnostics = []
        self._pre_parsing_diagnostics = []

    def diagnostic(self, name: str):
        def wrapper(func: DiagnosticFunc) -> DiagnosticFunc:
            self._diagnostics.append(Diagnostic(
                name=name,
                perform=func
            ))
            return func

        return wrapper

    def pre_parsing_diagnostic(self, name: str):
        def wrapper(func: TextDiagnosticFunc) -> TextDiagnosticFunc:
            self._pre_parsing_diagnostics.append(TextDiagnostic(
                name=name,
                perform=func
            ))
            return func

        return wrapper

    def language_diagnostic(self, name: str):
        def wrapper(func: LanguageDiagnosticFunc) -> LanguageDiagnosticFunc:
            def perform(projects: List[LanguageProject]) -> List[DiagnosticResult]:
                result = []
                for proj in projects:
                    result.extend(func(proj))
                return result

            self._diagnostics.append(Diagnostic(
                name=name,
                perform=perform
            ))
            return func

        return wrapper

    def _file_wrapper(self, name: str, files_getter: Callable[[LanguageProject], T]):
        def wrapper(func):
            def perform(projects: List[LanguageProject]) -> List[DiagnosticResult]:
                result = []
                for proj in projects:
                    for f in files_getter(proj):
                        result.extend(func(proj, f))
                return result

            self._diagnostics.append(Diagnostic(
                name=name,
                perform=perform
            ))
            return func

        return wrapper

    def template_diagnostic(self, name: str):
        return self._file_wrapper(name, lambda proj: proj.template_files)

    def extension_diagnostic(self, name: str):
        return self._file_wrapper(name, lambda proj: proj.extension_files)

    @staticmethod
    def _print_diagnostic_result(diagnostic, result: DiagnosticResult):
        if result.level == DiagnosticResult.DiagnosticLevel.ERROR:
            Console.err(f"[{diagnostic.name}] ERROR: {result.message}")
        if result.level == DiagnosticResult.DiagnosticLevel.WARNING:
            Console.warn(f"[{diagnostic.name}] WARNING: {result.message}")

    @staticmethod
    def _has_errors(results: List[DiagnosticResult]) -> bool:
        for result in results:
            if result.level == DiagnosticResult.DiagnosticLevel.ERROR:
                return True
        return False

    @staticmethod
    def _perform(diagnostics, args) -> bool:
        all_results = []
        for diagnostic in diagnostics:
            Console.info(f"[{diagnostic.name}] Start diagnostic")
            results = diagnostic.perform(args)
            all_results.extend(results)
            for result in results:
                Nerd._print_diagnostic_result(diagnostic, result)
            Console.info(f"[{diagnostic.name}] Finished diagnostic")
        return Nerd._has_errors(all_results)

    def perform_diagnostics(self, projects: List[LanguageProject]) -> bool:
        return Nerd._perform(self._diagnostics, projects)

    def perform_pre_parsing_diagnostics(self, paths: List[Path]) -> bool:
        return Nerd._perform(self._pre_parsing_diagnostics, paths)


nerd = Nerd()


def diff(fst: List[T], snd: List[T]) -> List[T]:
    result = []
    for fst_e in fst:
        if fst_e not in snd:
            result.append(fst_e)
    for snd_e in snd:
        if snd_e not in fst:
            result.append(snd_e)
    return result


def supported(templates: List[Template]) -> List[Template]:
    result = []
    for template in templates:
        if template.code is not None:
            result.append(template)
    return result


@nerd.pre_parsing_diagnostic("Unescaped tilda")
def unescaped_tilda_diagnostic(paths: List[Path]) -> List[DiagnosticResult]:
    results = []

    def find_all(target_str, sub_str):
        start = 0
        while True:
            start = target_str.find(sub_str, start)
            if start == -1:
                return
            yield start
            start += len(sub_str)

    def is_valid_tilda(line_text: str, pos: int) -> bool:
        assert line_text.count("\n") == 0
        assert line_text[pos] == "~"
        if pos == 0 or pos == len(line_text) - 1:
            return True
        if line_text[pos - 1] == "\\":
            return True
        if line_text[pos - 1] == "]":
            return True
        if line_text[pos + 1] == "[":
            return True
        return False

    for path in paths:
        text = path.read_text()
        lines = text.split("\n")
        for line_n, line in enumerate(lines):
            tilda_positions = find_all(line, "~")
            for position in tilda_positions:
                if not is_valid_tilda(line, position):
                    results.append(DiagnosticResult.error(f"Unescaped tilda at {line_n}:{position} [{path}]"))

    return results


@nerd.diagnostic("Language structural equality")
def language_structural_equality_diagnostic(projects: List[LanguageProject]) -> List[DiagnosticResult]:
    result = []

    def find_same(files: List[ProjectFile], target: ProjectFile) -> ProjectFile | None:
        for file in files:
            if target.name == file.name and target.parents == file.parents:
                return file
        return None

    def compare_template_file(fst: TemplateFile, snd: TemplateFile):
        if fst.kind != TmtFileKind.TMT or snd.kind != TmtFileKind.TMT:
            return
        fst_template_names = [x.name for x in fst.templates]
        snd_template_names = [x.name for x in snd.templates]

        template_diff = diff(fst_template_names, snd_template_names)

        for name in template_diff:
            result.append(
                DiagnosticResult.error(f"Can't find the same template [{fst.path}, {name}] in the file [{snd.path}]")
            )

    def compare_helper_file(fst: HelperFile, snd: HelperFile):
        return

    def compare_extension_file(fst: ExtensionFile, snd: ExtensionFile):
        return

    def compare(fst: LanguageProject, snd: LanguageProject):
        second_files = snd.files
        for proj_file in fst.files:
            same_file = find_same(second_files, proj_file)
            if not isinstance(proj_file, TemplateFile):
                continue

            if same_file is None:
                result.append(DiagnosticResult.warning(f"TODO[{snd.name}]: Add the same file [{proj_file.path}]"))
            else:
                assert isinstance(same_file, TemplateFile)
                compare_template_file(proj_file, same_file)

    for first_lang_proj in projects:
        for second_lang_proj in projects:

            if first_lang_proj.name != second_lang_proj.name:
                compare(first_lang_proj, second_lang_proj)
                compare(second_lang_proj, first_lang_proj)

    return result


@nerd.template_diagnostic("Invalid imports")
def invalid_import_diagnostic(project: LanguageProject, template_file: TemplateFile) -> List[DiagnosticResult]:
    result = []

    for helper_import in template_file.helper_imports:
        helper = project.get_helper(helper_import)
        if helper is None:
            result.append(
                DiagnosticResult.error(f"Invalid import [{helper_import.target}] in file [{template_file.path}]")
            )

    for extension_import in template_file.extension_imports:
        extensions = project.get_extensions(extension_import)
        if extensions is None:
            result.append(
                DiagnosticResult.error(f"Invalid import [{extension_import.target}] in file [{template_file.path}]")
            )

    return result


@nerd.template_diagnostic("Undefined macro or define")
def undefined_macro_diagnostic(project: LanguageProject, template_file: TemplateFile) -> List[DiagnosticResult]:
    result = []

    available_macros = []
    available_defines = []
    for extension_import in template_file.extension_imports:
        extensions = project.get_extensions(extension_import)
        if extensions is None:
            continue
        macros, _, defines = extensions
        available_macros.extend(macros)
        available_defines.extend(defines)
    available_macros.extend(template_file.local_macros)
    available_defines.extend(template_file.local_defines)

    available_macro_names = [macro.name for macro in available_macros]
    available_define_names = [define.name for define in available_defines]
    for template in supported(template_file.templates):
        for macro_usage in template.code.macros:
            if macro_usage.name not in available_macro_names:
                result.append(DiagnosticResult.error(
                    f"Undefined macro [{macro_usage.name}] in [{template_file.path}]")
                )
        for define_usage in template.code.defines:
            if define_usage.name not in available_define_names:
                result.append(DiagnosticResult.error(
                    f"Undefined define [{define_usage.name}] in [{template_file.path}]")
                )

    return result


@nerd.template_diagnostic("Unused local macro or define")
def unused_local_macro_diagnostic(project: LanguageProject, template_file: TemplateFile) -> List[DiagnosticResult]:
    result = []

    visited_macros = set()
    visited_defines = set()

    local_macro_names = set([m.name for m in template_file.local_macros])
    local_define_names = set([d.name for d in template_file.local_defines])

    def get_codes(name, collection):
        codes = []
        for v in collection:
            if v.name == name:
                codes.append(v.code)
        return codes

    def traverse_code(codes, n):
        for code in codes:
            for macro in code.macros:
                if macro.name not in visited_macros and macro.name in local_macro_names:
                    visited_macros.add(macro.name)
                    traverse_code(get_codes(macro.name, template_file.local_macros), n + 1)
            for define in code.defines:
                if define.name not in visited_defines and define.name in local_define_names:
                    visited_defines.add(define.name)
                    traverse_code(get_codes(define.name, template_file.local_defines), n + 1)

    traverse_code([template.code for template in supported(template_file.templates)], 0)

    for m in local_macro_names.difference(visited_macros):
        result.append(
            DiagnosticResult.warning(f"Local macro [{m}] in [{template_file.path}] defined but not used")
        )

    for d in local_define_names.difference(visited_defines):
        result.append(
            DiagnosticResult.warning(f"Local define [{d}] in [{template_file.path}] defined but not used")
        )
    return result


@nerd.language_diagnostic("Invalid extensions")
def invalid_extensions_diagnostic(project: LanguageProject) -> List[DiagnosticResult]:
    result = []

    def check_extension(path: Path, e: Extension):
        if e.target.kind != "EXPR":
            result.append(DiagnosticResult.error(f"Invalid hole kind [{e.target.kind}] for extension in file [{path}]"))

    for template_file in project.template_files:
        for extension in template_file.local_extensions:
            check_extension(template_file.path, extension)

    for extension_file in project.extension_files:
        for extension in extension_file.extensions:
            check_extension(extension_file.path, extension)

    return result


@nerd.language_diagnostic("Dangling ref")
def dangling_ref_diagnostic(project: LanguageProject) -> List[DiagnosticResult]:
    result = []

    def get_dangling_refs(holes: List[Hole]) -> List[Hole]:
        dangling_refs = []
        for hole in holes:
            if hole.ref is None:
                continue
            if holes.count(hole) < 2:
                dangling_refs.append(hole)

        return dangling_refs

    def traverse_holes(holes: List[Hole]) -> List[Hole]:
        result_holes = []
        for hole in holes:
            result_holes.append(hole)
            if hole.type_ is not None:
                result_holes.extend(hole.type_.types)
        return result_holes

    def check_extension(path: Path, e: Extension):
        if e.target.kind == "DEFINE":
            return
        for ref in get_dangling_refs(traverse_holes([*e.target.type_.types, *e.code.holes])):
            result.append(
                DiagnosticResult.warning(f"Dangling ref [{ref}] inside extensions in file [{path}]")
            )

    def check_template(path: Path, t: Template):
        if t.code.defines != [] or t.code.macros != []:
            return
        for ref in get_dangling_refs(traverse_holes(t.code.holes)):
            result.append(
                DiagnosticResult.warning(f"Dangling ref [{ref}] inside template [{t.name}] in file [{path}]")
            )

    for template_file in project.template_files:
        for extension in template_file.local_extensions:
            check_extension(template_file.path, extension)
        for template in supported(template_file.templates):
            check_template(template_file.path, template)

    for extension_file in project.extension_files:
        for extension in extension_file.extensions:
            check_extension(extension_file.path, extension)

    return result


@nerd.language_diagnostic("Duplicated template names (globally)")
def duplicated_names_globally(project: LanguageProject) -> List[DiagnosticResult]:
    result = []

    templates_to_files = {}
    for template_file in project.template_files:
        for template in template_file.templates:
            if template.name not in templates_to_files:
                templates_to_files[template.name] = [template_file.path]
            else:
                templates_to_files[template.name].append(template_file.path)

    for template_name in templates_to_files:
        files = templates_to_files[template_name]
        if len(files) > 1:
            result.append(DiagnosticResult.error(f"Duplicated template name [{template_name}] in files [{files}]"))

    return result


@nerd.language_diagnostic("Duplicated names")
def duplicated_names(project: LanguageProject) -> List[DiagnosticResult]:
    result = []

    def check_names(
        files: List[ProjectFile],
        get_named_objects: Callable[[ProjectFile], T],
        get_name: Callable[[T], str],
        object_name: str
    ):
        name_to_file = {}
        names = set()
        for f in files:
            named_objects = get_named_objects(f)
            if named_objects is None:
                continue
            for named_object in named_objects:
                name = get_name(named_object)
                if name in names:
                    result.append(DiagnosticResult.error(
                        f"Duplicated {object_name} name [{named_object.name}] in "
                        f"[{f.path}]"
                        f" and "
                        f"[{name_to_file[name].path}]")
                    )
                else:
                    names.add(name)
                    name_to_file[name] = f

    check_names(
        project.template_files,
        lambda template_file: template_file.templates,
        lambda template: template.name,
        "template"
    )

    check_names(
        project.helper_files,
        lambda helper_file: helper_file.classes,
        lambda helper_class: helper_class.name,
        "helper class"
    )

    check_names(
        project.template_files,
        lambda template_file: template_file.helper_functions,
        lambda helper_function: helper_function.name,
        "helper function"
    )

    return result
