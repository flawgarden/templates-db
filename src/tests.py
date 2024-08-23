from pathlib import Path
from typing import List

import diagnostic

from diagnostic import DiagnosticResult
from template import TemplateFile, HelperFile, ExtensionFile, LanguageProject, TmtFileKind, HoleType, Code, Template, \
    MacroDefinition, DefineDefinition, Extension, Hole, HelperImport, HelperClass, ExtensionImport, MacroUsage, \
    DefineUsage, HelperFunction


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


class DefaultValues:

    @staticmethod
    def get_template_file():
        return TemplateFile(
            kind=TmtFileKind.TMT,
            name="name",
            path=Path(),
            parents=[],
            extension_imports=[],
            helper_imports=[],
            local_extensions=[],
            local_macros=[],
            local_defines=[],
            templates=[],
            helper_functions=[],
        )

    @staticmethod
    def get_helper_file():
        return HelperFile(
            kind=TmtFileKind.TMT,
            name="name",
            path=Path(),
            parents=[],
            classes=None
        )

    @staticmethod
    def get_extension_file():
        return ExtensionFile(
            kind=TmtFileKind.TMT,
            name="name",
            path=Path(),
            parents=[],
            extensions=[],
            macros=[],
            defines=[]
        )

    @staticmethod
    def get_code():
        return Code(
            macros=[],
            defines=[],
            holes=[],
            body="",
        )

    @staticmethod
    def get_template():
        return Template(
            name="name",
            code=DefaultValues.get_code(),
        )

    @staticmethod
    def get_macro():
        return MacroDefinition(
            name="name",
            code=DefaultValues.get_code(),
        )

    @staticmethod
    def get_define():
        return DefineDefinition(
            name="name",
            code=DefaultValues.get_code(),
        )

    @staticmethod
    def get_extension():
        return Extension(
            target=Hole(kind="EXPR", type_=HoleType(body="", types=[]), ref=None),
            code=DefaultValues.get_code(),
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

        @staticmethod
        def test_missed_template_file_cause_error():
            template_file = DefaultValues.get_template_file()
            first_project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_missed_helper_file_cause_error():
            helper_file = DefaultValues.get_helper_file()
            first_project = ProjectBuilder() \
                .with_helper_file(helper_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_missed_extension_file_cause_error():
            extension_file = DefaultValues.get_extension_file()
            first_project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_same_todo_file_cause_warning():
            template_file = DefaultValues.get_template_file()
            template_file.name = "some_file"
            todo_template_file = DefaultValues.get_template_file()
            todo_template_file.name = "some_file"
            todo_template_file.kind = TmtFileKind.TODO
            first_project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .with_template_file(todo_template_file) \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_same_unsupported_file_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.name = "some_file"
            unsupported_template_file = DefaultValues.get_template_file()
            unsupported_template_file.name = "some_file"
            unsupported_template_file.kind = TmtFileKind.UNSUPPORTED
            first_project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .with_template_file(unsupported_template_file) \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_same_template_file_with_different_templates_cause_error():
            template_file = DefaultValues.get_template_file()
            template_file.name = "some_file"
            template = DefaultValues.get_template()
            template.name = "SomeTemplate1"
            template_file.templates = [template]
            other_template_file = DefaultValues.get_template_file()
            other_template_file.name = "some_file"
            other_template = DefaultValues.get_template()
            other_template.name = "SomeTemplate2"
            other_template_file.templates = [other_template]
            first_project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("first_lang")
            second_project = ProjectBuilder() \
                .with_template_file(other_template_file) \
                .get_project("second_lang")

            diagnostics = diagnostic.language_structural_equality_diagnostic([first_project, second_project])

            assert has_error(diagnostics) and not has_warning(diagnostics)

    class InvalidImportsTest:

        @staticmethod
        def test_invalid_helper_import_cause_error():
            template_file = DefaultValues.get_template_file()
            template_file.helper_imports = [HelperImport("helpers/SomeHelper")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_valid_helper_import_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.helper_imports = [HelperImport("helpers/SomeHelper")]
            helper_file = DefaultValues.get_helper_file()
            helper_file.parents = ["helpers"]
            helper_file.name = "SomeHelper"
            helper_file.classes = HelperClass(name="SomeHelper", body="")
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_helper_file(helper_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_invalid_extension_import_cause_error():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.invalid_import_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_valid_extension_import_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            extension_file = DefaultValues.get_extension_file()
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
            template_file = DefaultValues.get_template_file()
            template = DefaultValues.get_template()
            template.code.macros = [MacroUsage("SomeMacro", ref=None)]
            template_file.templates = [template]
            macro = DefaultValues.get_macro()
            macro.name = "SomeMacro"
            template_file.local_macros = [macro]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_local_defined_define_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template = DefaultValues.get_template()
            template.code.defines = [DefineUsage("SomeDefine", ref=None)]
            template_file.templates = [template]
            define = DefaultValues.get_define()
            define.name = "SomeDefine"
            template_file.local_defines = [define]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_macro_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template = DefaultValues.get_template()
            template.code.macros = [MacroUsage("SomeMacro", ref=None)]
            template_file.templates = [template]
            extension_file = DefaultValues.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            macro = DefaultValues.get_macro()
            macro.name = "SomeMacro"
            extension_file.macros = [macro]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_define_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template = DefaultValues.get_template()
            template.code.defines = [DefineUsage("SomeDefine", ref=None)]
            template_file.templates = [template]
            extension_file = DefaultValues.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            define = DefaultValues.get_macro()
            define.name = "SomeDefine"
            extension_file.defines = [define]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_undefined_macro_cause_error():
            template_file = DefaultValues.get_template_file()
            template = DefaultValues.get_template()
            template.code.macros = [MacroUsage("SomeMacro", ref=None)]
            template_file.templates = [template]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_undefined_define_cause_error():
            template_file = DefaultValues.get_template_file()
            template = DefaultValues.get_template()
            template.code.defines = [DefineUsage("SomeDefine", ref=None)]
            template_file.templates = [template]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.undefined_macro_diagnostic(project, template_file)

            assert has_error(diagnostics) and not has_warning(diagnostics)

    class UnusedLocalMacroTest:

        @staticmethod
        def test_local_defined_and_used_macro_doesnt_cause_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template = DefaultValues.get_template()
            template.code.macros = [MacroUsage("SomeMacro", ref=None)]
            template_file.templates = [template]
            macro = DefaultValues.get_macro()
            macro.name = "SomeMacro"
            template_file.local_macros = [macro]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_local_defined_and_used_define_doesnt_cause_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            template = DefaultValues.get_template()
            template.code.defines = [DefineUsage("SomeDefine", ref=None)]
            template_file.templates = [template]
            define = DefaultValues.get_define()
            define.name = "SomeDefine"
            template_file.local_defines = [define]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_macro_and_unused_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            extension_file = DefaultValues.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            macro = DefaultValues.get_macro()
            macro.name = "SomeMacro"
            extension_file.macros = [macro]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_imported_define_and_unused_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            template_file.extension_imports = [ExtensionImport("extensions/SomeExtension")]
            extension_file = DefaultValues.get_extension_file()
            extension_file.parents = ["extensions"]
            extension_file.name = "SomeExtension"
            define = DefaultValues.get_define()
            define.name = "SomeMacro"
            extension_file.defines = [define]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_local_defined_and_unused_macro_cause_warning():
            template_file = DefaultValues.get_template_file()
            macro = DefaultValues.get_macro()
            macro.name = "SomeMacro"
            template_file.local_macros = [macro]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_local_defined_and_unused_define_cause_warning():
            template_file = DefaultValues.get_template_file()
            define = DefaultValues.get_define()
            define.name = "SomeMacro"
            template_file.local_macros = [define]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.unused_local_macro_diagnostic(project, template_file)

            assert not has_error(diagnostics) and has_warning(diagnostics)

    class DanglingRefTest:

        @staticmethod
        def test_dangling_ref_in_local_extension_cause_warning():
            template_file = DefaultValues.get_template_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[]))]
            template_file.local_extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_in_template_cause_warning():
            template_file = DefaultValues.get_template_file()
            code = DefaultValues.get_code()
            code.holes = [Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[]))]
            template_file.templates = [Template("", code)]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_in_extension_file_cause_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[]))]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_with_same_ref_but_different_types_cause_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Boolean", types=[]))
            ]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_with_same_ref_but_different_kind_cause_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
                Hole(kind="VAR", ref="@1", type_=HoleType(body="Integer", types=[]))
            ]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_dangling_type_ref_cause_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [
                Hole(
                    kind="EXPR",
                    ref="@1",
                    type_=HoleType(
                        body="TYPE@1",
                        types=[Hole(kind="TYPE", ref="@1", type_=None)]
                    )
                ),
            ]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and has_warning(diagnostics)

        @staticmethod
        def test_type_refs_doesnt_cause_error_or_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [
                Hole(
                    kind="EXPR",
                    ref=None,
                    type_=HoleType(
                        body="TYPE@1",
                        types=[Hole(kind="TYPE", ref="@1", type_=None)]
                    )
                ),
                Hole(
                    kind="VAR",
                    ref=None,
                    type_=HoleType(
                        body="TYPE@1",
                        types=[Hole(kind="TYPE", ref="@1", type_=None)])
                ),
            ]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_refs_doesnt_cause_error_or_warning():
            extension_file = DefaultValues.get_extension_file()
            target = Hole(kind="EXPR", ref=None, type_=HoleType(body="Integer", types=[]))
            code = DefaultValues.get_code()
            code.holes = [
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
            ]
            extension_file.extensions = [Extension(target, code)]
            project = ProjectBuilder() \
                .with_extension_file(extension_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_with_macro_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            code = DefaultValues.get_code()
            code.holes = [
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
            ]
            code.macros = [
                MacroUsage("", ref=None)
            ]
            template = DefaultValues.get_template()
            template.code = code
            template_file.templates = [template]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_dangling_ref_with_define_doesnt_cause_error_or_warning():
            template_file = DefaultValues.get_template_file()
            code = DefaultValues.get_code()
            code.holes = [
                Hole(kind="EXPR", ref="@1", type_=HoleType(body="Integer", types=[])),
            ]
            code.defines = [
                DefineUsage("", ref=None)
            ]
            template = DefaultValues.get_template()
            template.code = code
            template_file.templates = [template]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.dangling_ref_diagnostic(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

    class DuplicatedNamesTest:

        @staticmethod
        def test_duplicated_template_names_in_same_file_cause_error():
            template_file = DefaultValues.get_template_file()
            template_file.templates = [
                DefaultValues.get_template(),
                DefaultValues.get_template()
            ]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_duplicated_template_names_in_different_files_cause_error():
            first_template_file = DefaultValues.get_template_file()
            first_template_file.templates = [
                DefaultValues.get_template()
            ]
            second_template_file = DefaultValues.get_template_file()
            second_template_file.templates = [
                DefaultValues.get_template()
            ]
            project = ProjectBuilder() \
                .with_template_file(first_template_file) \
                .with_template_file(second_template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_different_template_names_doesnt_cause_error_or_warning():
            first_template_file = DefaultValues.get_template_file()
            first_template_file.templates = [
                Template(name="name1", code=DefaultValues.get_code()),
                Template(name="name2", code=DefaultValues.get_code())
            ]
            second_template_file = DefaultValues.get_template_file()
            second_template_file.templates = [
                Template(name="name3", code=DefaultValues.get_code()),
                Template(name="name4", code=DefaultValues.get_code())
            ]
            project = ProjectBuilder() \
                .with_template_file(first_template_file) \
                .with_template_file(second_template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_duplicated_helper_function_names_in_same_file_cause_error():
            template_file = DefaultValues.get_template_file()
            template_file.helper_functions = [
                HelperFunction(name="name", body=""),
                HelperFunction(name="name", body="")
            ]
            project = ProjectBuilder() \
                .with_template_file(template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_duplicated_helper_function_names_in_different_files_cause_error():
            first_template_file = DefaultValues.get_template_file()
            first_template_file.helper_functions = [
                HelperFunction(name="name", body=""),
            ]
            second_template_file = DefaultValues.get_template_file()
            second_template_file.helper_functions = [
                HelperFunction(name="name", body=""),
            ]
            project = ProjectBuilder() \
                .with_template_file(first_template_file) \
                .with_template_file(second_template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_different_helper_function_names_doesnt_cause_error_or_warning():
            first_template_file = DefaultValues.get_template_file()
            first_template_file.helper_functions = [
                HelperFunction(name="name1", body=""),
                HelperFunction(name="name2", body="")
            ]
            second_template_file = DefaultValues.get_template_file()
            second_template_file.helper_functions = [
                HelperFunction(name="name3", body=""),
                HelperFunction(name="name4", body="")
            ]
            project = ProjectBuilder() \
                .with_template_file(first_template_file) \
                .with_template_file(second_template_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_duplicated_helper_class_names_in_same_file_cause_error():
            helper_file = DefaultValues.get_helper_file()
            helper_file.classes = [
                HelperClass(name="name", body=""),
                HelperClass(name="name", body="")
            ]
            project = ProjectBuilder() \
                .with_helper_file(helper_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_duplicated_helper_class_names_in_different_files_cause_error():
            first_helper_file = DefaultValues.get_helper_file()
            first_helper_file.classes = [
                HelperClass(name="name", body="")
            ]
            second_helper_file = DefaultValues.get_helper_file()
            second_helper_file.classes = [
                HelperClass(name="name", body="")
            ]
            project = ProjectBuilder() \
                .with_helper_file(first_helper_file) \
                .with_helper_file(second_helper_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert has_error(diagnostics) and not has_warning(diagnostics)

        @staticmethod
        def test_different_helper_class_names_doesnt_cause_error_or_warning():
            first_helper_file = DefaultValues.get_helper_file()
            first_helper_file.classes = [
                HelperClass(name="name1", body=""),
                HelperClass(name="name2", body="")
            ]
            second_helper_file = DefaultValues.get_helper_file()
            second_helper_file.classes = [
                HelperClass(name="name3", body=""),
                HelperClass(name="name4", body="")
            ]
            project = ProjectBuilder() \
                .with_helper_file(first_helper_file) \
                .with_helper_file(second_helper_file) \
                .get_project("lang")

            diagnostics = diagnostic.duplicated_names(project)

            assert not has_error(diagnostics) and not has_warning(diagnostics)
