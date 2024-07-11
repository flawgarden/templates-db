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
DiagnosticFunc = Callable[[List[LanguageProject]], List[DiagnosticResult]]
LanguageDiagnosticFunc = Callable[[LanguageProject], List[DiagnosticResult]]
TemplateDiagnosticFunc = Callable[[LanguageProject, TemplateFile], List[DiagnosticResult]]
ExtensionDiagnosticFunc = Callable[[LanguageProject, ExtensionFile], List[DiagnosticResult]]


@dataclass(frozen=True)
class Diagnostic:
    name: str
    perform: DiagnosticFunc


class Nerd:

    def __init__(self):
        self._diagnostics = []

    def diagnostic(self, name: str):
        def wrapper(func: DiagnosticFunc) -> DiagnosticFunc:
            self._diagnostics.append(Diagnostic(
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

    def perform_diagnostics(self, projects: List[LanguageProject]) -> bool:
        has_errors = False
        for diagnostic in self._diagnostics:
            Console.info(f"[{diagnostic.name}] Start diagnostic ")
            results = diagnostic.perform(projects)
            for result in results:
                if result.level == DiagnosticResult.DiagnosticLevel.ERROR:
                    has_errors = True
                    Console.err(f"[{diagnostic.name}] ERROR: {result.message}")
                if result.level == DiagnosticResult.DiagnosticLevel.WARNING:
                    Console.warn(f"[{diagnostic.name}] WARNING: {result.message}")
            Console.info(f"[{diagnostic.name}] Finished diagnostic")

        return has_errors


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


@nerd.diagnostic("Language structural equality")
def language_structural_equality_diagnostic(projects: List[LanguageProject]) -> List[DiagnosticResult]:
    result = []

    def find_same(files: List[ProjectFile], target: ProjectFile) -> ProjectFile | None:
        for file in files:
            if target.name == file.name and target.parents == file.parents:
                return file
        return None

    def compare_template_file(fst: TemplateFile, snd: TemplateFile):
        if fst.kind == TmtFileKind.TODO:
            result.append(DiagnosticResult.warning(f"TODO file {fst.path}"))
            return
        if snd.kind == TmtFileKind.TODO:
            result.append(DiagnosticResult.warning(f"TODO file {snd.path}"))
            return
        if fst.kind != TmtFileKind.TMT or snd.kind != TmtFileKind.TMT:
            return
        fst_template_names = [x.name for x in fst.templates]
        snd_template_names = [x.name for x in snd.templates]

        template_diff = diff(fst_template_names, snd_template_names)

        for name in template_diff:
            result.append(DiagnosticResult.error(f"Can't find same template [{fst.path}, {name}] in file [{snd.path}]"))

    def compare_helper_file(fst: HelperFile, snd: HelperFile):
        return

    def compare_extension_file(fst: ExtensionFile, snd: ExtensionFile):
        return

    def compare(fst: LanguageProject, snd: LanguageProject):
        second_files = snd.files
        for proj_file in fst.files:
            same_file = find_same(second_files, proj_file)
            if same_file is None:
                result.append(DiagnosticResult.error(f"Can't find same file [{proj_file.path}] for [{snd.name}]"))
            elif isinstance(same_file, TemplateFile):
                assert isinstance(proj_file, TemplateFile)
                compare_template_file(proj_file, same_file)
            elif isinstance(same_file, HelperFile):
                assert isinstance(proj_file, HelperFile)
                compare_helper_file(proj_file, same_file)
            elif isinstance(same_file, ExtensionFile):
                assert isinstance(proj_file, ExtensionFile)
                compare_extension_file(proj_file, same_file)
            else:
                assert False

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


@nerd.template_diagnostic("Undefined macro")
def undefined_macro_diagnostic(project: LanguageProject, template_file: TemplateFile) -> List[DiagnosticResult]:
    result = []

    available_macros = []
    for extension_import in template_file.extension_imports:
        extensions = project.get_extensions(extension_import)
        if extensions is None:
            continue
        macros, _ = extensions
        available_macros.extend(macros)
    available_macros.extend(template_file.local_macros)

    available_macro_names = [macro.name for macro in available_macros]
    for template in template_file.templates:
        for macro_name in template.macros:
            if macro_name not in available_macro_names:
                result.append(DiagnosticResult.error(f"Undefined macro [{macro_name}] in [{template_file.path}]"))

    return result


@nerd.template_diagnostic("Unused local macro")
def unused_local_macro_diagnostic(project: LanguageProject, template_file: TemplateFile) -> List[DiagnosticResult]:
    result = []

    used_macro_names = []
    for template in template_file.templates:
        used_macro_names.extend(template.macros)

    for macro in template_file.local_macros:
        if macro.name not in used_macro_names:
            result.append(
                DiagnosticResult.warning(f"Local macro [{macro.name}] in [{template_file.path}] defined but not used"))

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
def dangling_ling_diagnostic(project: LanguageProject) -> List[DiagnosticResult]:
    result = []

    def get_dangling_refs(holes: List[Hole]) -> List[str]:
        dangling_refs = []
        refs = list(map(lambda x: x.ref, holes))
        for ref in refs:
            if ref is None:
                continue
            if refs.count(ref) < 2:
                dangling_refs.append(ref)
        return dangling_refs

    def check_extension(path: Path, e: Extension):
        for ref in get_dangling_refs(e.holes):
            result.append(
                DiagnosticResult.warning(f"Dangling ref [{ref}] inside extensions in file [{path}]")
            )

    def check_template(path: Path, t: Template):
        for ref in get_dangling_refs(t.holes):
            result.append(
                DiagnosticResult.warning(f"Dangling ref [{ref}] inside template [{t.name}] in file [{path}]")
            )

    for template_file in project.template_files:
        for extension in template_file.local_extensions:
            check_extension(template_file.path, extension)
        for template in template_file.templates:
            check_template(template_file.path, template)

    for extension_file in project.extension_files:
        for extension in extension_file.extensions:
            check_extension(extension_file.path, extension)

    return result
