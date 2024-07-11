import diagnostic

from pathlib import Path
from typing import List
from diagnostic import DiagnosticResult
from template import TemplateFile, HelperFile, ExtensionFile, LanguageProject, HelperImport, ExtensionImport, \
    HelperClass, Macro, Template


class ProjectBuilder:

    def __init__(self):
        self._template_files = []
        self._helper_files = []
        self._extension_files = []

    def with_template_file(self, file: TemplateFile):
        self._template_files.append(file)
        return self

    def with_helper_file(self, file: HelperFile):
        self._helper_files.append(file)
        return self

    def with_extension_file(self, file: ExtensionFile):
        self._extension_files.append(file)
        return self

    def get_project(self, name) -> LanguageProject:
        return LanguageProject(
            name,
            self._template_files,
            self._helper_files,
            self._extension_files,
        )


class DefaultFiles:

    @staticmethod
    def get_template_file():
        return TemplateFile(
            name="name",
            path=Path(),
            parents=[],
            extension_imports=[],
            helper_imports=[],
            local_extensions=[],
            local_macros=[],
            templates=[]
        )

    @staticmethod
    def get_helper_file():
        return HelperFile(
            name="name",
            path=Path(),
            parents=[],
            class_=None
        )

    @staticmethod
    def get_extension_file():
        return ExtensionFile(
            name="name",
            path=Path(),
            parents=[],
            extensions=[],
            macros=[]
        )


def has_error(diagnostics: List[DiagnosticResult]) -> bool:
    for d in diagnostics:
        if d.level == DiagnosticResult.DiagnosticLevel.ERROR:
            return True
    return False


def has_warning(diagnostics: List[DiagnosticResult]) -> bool:
    for d in diagnostics:
        if d.level == DiagnosticResult.DiagnosticLevel.WARNING:
            return True
    return False


class DiagnosticsTest:

    class LanguageStructuralEqualityTest:
        pass

    class InvalidImportsTest:

        @staticmethod
        def test_invalid_helper_import_cause_error():
            template_file = DefaultFiles.get_template_file()
            template_file.helper_imports = [HelperImport("helpers/SomeHelper")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_valid_helper_import_doesnt_cause_error_or_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.helper_imports = [HelperImport("helpers/SomeHelper")]
            helper_file = DefaultFiles.get_helper_file()
            helper_file.parents = ["helpers"]
            helper_file.name = "SomeHelper"
            helper_file.class_ = HelperClass(name="SomeHelper", body="")
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_helper_file(helper_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_invalid_extension_import_cause_error():
            template_file = DefaultFiles.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_valid_extension_import_doesnt_cause_error_or_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            extension_file = DefaultFiles.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

    class UndefinedMacroTest:
        @staticmethod
        def test_local_defined_macro_doesnt_cause_error_or_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.templates = [Template(body="", holes=[], macros=["SomeMacro"], name="SomeTemplate")]
            template_file.local_macros = [Macro(name="SomeMacro", holes=[], body="")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_macro_doesnt_cause_error_or_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template_file.templates = [Template(body="", holes=[], macros=["SomeMacro"], name="SomeTemplate")]
            extension_file = DefaultFiles.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            extension_file.macros = [Macro(name="SomeMacro", holes=[], body="")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_undefined_macro_doesnt_cause_error():
            template_file = DefaultFiles.get_template_file()
            template_file.templates = [Template(body="", holes=[], macros=["SomeMacro"], name="SomeTemplate")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

    class UnusedLocalMacroTest:
        @staticmethod
        def test_local_defined_and_used_macro_doesnt_cause_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template_file.templates = [Template(body="", holes=[], macros=["SomeMacro"], name="SomeTemplate")]
            template_file.local_macros = [Macro(name="SomeMacro", holes=[], body="")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_macro_and_unused_doesnt_cause_error_or_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            extension_file = DefaultFiles.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            extension_file.macros = [Macro(name="SomeMacro", holes=[], body="")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_local_defined_and_unused_macro_cause_warning():
            template_file = DefaultFiles.get_template_file()
            template_file.local_macros = [Macro(name="SomeMacro", holes=[], body="")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and has_warning(diagnostics)

    class DanglingRefTest:
        pass
