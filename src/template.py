from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Callable


class TmtFileKind(Enum):
    UNSUPPORTED = 0
    TODO = 1
    TMT = 2


@dataclass
class Hole:
    kind: str
    type_: str
    ref: str | None


@dataclass
class Extension:
    target: Hole
    holes: List[Hole]
    body: str


@dataclass
class Macro:
    name: str
    holes: List[Hole]
    body: str


@dataclass
class Template:
    name: str
    macros: List[str]
    holes: List[Hole]
    body: str


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
class TemplateFile(ProjectFile):
    helper_imports: List[HelperImport]
    extension_imports: List[ExtensionImport]
    local_extensions: List[Extension]
    local_macros: List[Macro]
    templates: List[Template]


@dataclass
class HelperFile(ProjectFile):
    class_: HelperClass | None


@dataclass
class ExtensionFile(ProjectFile):
    extensions: List[Extension]
    macros: List[Macro]


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

    def get_extensions(self, import_: ExtensionImport) -> Tuple[List[Macro], List[Extension]] | None:
        result_macros = []
        result_extensions = []

        def add_by_filter(ext_filter: Callable[[ExtensionFile], bool]):
            for ext_file in self._extension_files:
                if ext_filter(ext_file):
                    result_macros.extend(ext_file.macros)
                    result_extensions.extend(ext_file.extensions)

        if import_.target == "*":
            add_by_filter(lambda ext_file: True)
            return result_macros, result_extensions

        parents_and_name = import_.target.split("/")
        name = parents_and_name[-1]
        parents = parents_and_name[:-1]

        if name == "*":
            add_by_filter(lambda ext_file: ext_file.parents == parents)
            return result_macros, result_extensions

        for f in self._extension_files:
            ext_file_parents_and_name = [x for x in f.parents][::-1]
            ext_file_parents_and_name.append(f.name)
            if ext_file_parents_and_name == parents_and_name:
                return f.macros, f.extensions

        return None

    def get_helper(self, import_: HelperImport) -> List[HelperClass] | None:
        result = []

        def add_by_filter(helper_filter: Callable[[HelperFile], bool]):
            for helper_file in self._helper_files:
                if helper_filter(helper_file):
                    result.append(helper_file.class_)

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
                return [f.class_]

        return None
