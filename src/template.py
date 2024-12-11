from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Callable


class TmtFileKind(Enum):
    UNSUPPORTED = 0
    TMT = 1
    TODO = 2


@dataclass
class HoleType:
    body: str
    types: List["Hole"]


@dataclass
class Hole:
    kind: str
    type_: HoleType | None
    ref: str | None


@dataclass
class MacroUsage:
    name: str
    ref: str | None


@dataclass
class DefineUsage:
    name: str
    ref: str | None


@dataclass
class Code:
    holes: List[Hole]
    macros: List[MacroUsage]
    defines: List[DefineUsage]
    body: str


@dataclass
class Extension:
    target: Hole
    code: Code


@dataclass
class MacroDefinition:
    name: str
    code: Code


@dataclass
class DefineDefinition:
    name: str
    code: Code


@dataclass
class Template:
    name: str
    code: Code | None


@dataclass
class ExtensionImport:
    target: str


@dataclass
class HelperImport:
    target: str


@dataclass
class HelperClass:
    name: str
    body: str


@dataclass
class ProjectFile:
    kind: TmtFileKind
    path: Path
    name: str
    parents: List[str]


@dataclass
class HelperFunction:
    name: str
    body: str


@dataclass
class TemplateFile(ProjectFile):
    helper_imports: List[HelperImport]
    extension_imports: List[ExtensionImport]
    local_extensions: List[Extension]
    local_macros: List[MacroDefinition]
    local_defines: List[DefineDefinition]
    templates: List[Template]
    helper_functions: List[HelperFunction]


@dataclass
class HelperFile(ProjectFile):
    classes: List[HelperClass] | None


@dataclass
class ExtensionFile(ProjectFile):
    extensions: List[Extension]
    macros: List[MacroDefinition]
    defines: List[DefineDefinition]


class LanguageProject:

    def __init__(
            self,
            name: str,
            template_files: List[TemplateFile],
            helper_files: List[HelperFile],
            extension_files: List[ExtensionFile]
    ):
        self._name = name
        self._template_files = template_files
        self._helper_files = helper_files
        self._extension_files = extension_files

    @property
    def name(self) -> str:
        return self._name

    @property
    def files(self) -> List[ProjectFile]:
        return self._template_files + self._helper_files + self._extension_files

    @property
    def template_files(self) -> List[TemplateFile]:
        return self._template_files

    @property
    def helper_files(self) -> List[HelperFile]:
        return self._helper_files

    @property
    def extension_files(self) -> List[ExtensionFile]:
        return self._extension_files

    def get_extensions(self, import_: ExtensionImport) \
            -> Tuple[List[MacroDefinition], List[Extension], List[DefineDefinition]] | None:
        result_macros = []
        result_extensions = []
        result_defines = []

        def add_by_filter(ext_filter: Callable[[ExtensionFile], bool]):
            for ext_file in self._extension_files:
                if ext_filter(ext_file):
                    result_macros.extend(ext_file.macros)
                    result_extensions.extend(ext_file.extensions)

        if import_.target == "*":
            add_by_filter(lambda ext_file: True)
            return result_macros, result_extensions, result_defines

        parents_and_name = import_.target.split("/")
        name = parents_and_name[-1]
        parents = parents_and_name[:-1]

        if name == "*":
            add_by_filter(lambda ext_file: ext_file.parents == parents)
            return result_macros, result_extensions, result_defines

        for f in self._extension_files:
            ext_file_parents_and_name = [x for x in f.parents][::-1]
            ext_file_parents_and_name.append(f.name)
            if ext_file_parents_and_name == parents_and_name:
                return f.macros, f.extensions, f.defines

        return None

    def get_helper(self, import_: HelperImport) -> List[HelperClass] | None:
        result = []

        def add_by_filter(helper_filter: Callable[[HelperFile], bool]):
            for helper_file in self._helper_files:
                if helper_filter(helper_file):
                    result.extend(helper_file.classes)

        if import_.target == "*":
            add_by_filter(lambda helper_file: True)
            return result

        parents_and_name = import_.target.split("/")
        name = parents_and_name[-1]
        parents = parents_and_name[:-1]

        if name == "*":
            add_by_filter(lambda helper_file: helper_file.parents == parents)
            return result

        for f in self._helper_files:
            helper_file_parents_and_name = [x for x in f.parents][::-1]
            helper_file_parents_and_name.append(f.name)
            if helper_file_parents_and_name == parents_and_name:
                return f.classes

        return None
