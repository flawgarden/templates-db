from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


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
        parents_and_name = import_.target.split("/")
        result = None

        for f in self._extension_files:
            f_parents_and_name = [x for x in f.parents]
            f_parents_and_name.append(f.name)
            if f_parents_and_name == parents_and_name:
                result = f.macros, f.extensions
                break

        return result

    def get_helper(self, import_: HelperImport) -> HelperClass | None:
        parents_and_name = import_.target.split("/")
        result = None

        for f in self._helper_files:
            f_parents_and_name = [x for x in f.parents]
            f_parents_and_name.append(f.name)
            if f_parents_and_name == parents_and_name:
                result = f.class_
                break

        return result
