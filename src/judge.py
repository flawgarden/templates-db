#!/usr/bin/env python3
import csv

from console import Console
from pathlib import Path

import metadata
import os
import random
import template
import parsing


class Judge:

    def __init__(
        self,
        language_project: template.LanguageProject,
        verdicts_path: Path,
        fuzzing_results_path: Path
    ):
        self.language_project = language_project
        self.verdicts_path = verdicts_path
        self.fuzzing_results_path = fuzzing_results_path

    @staticmethod
    def _exec(command: str) -> bool:
        exit_code = os.system(command)
        if exit_code != 0:
            Console.err(f"Command[{command}] returns unexpected exit code[{exit_code}]")
            return False
        return True

    @staticmethod
    def _show_file(path: Path):
        return Judge._exec(f"batcat --paging=never {path.absolute()}")

    @staticmethod
    def _show_text(text: str):
        return Judge._exec(f"echo '''{text}''' | batcat --paging=never")

    @staticmethod
    def _clear():
        return Judge._exec(f"clear")

    def _import_verdicts(self):
        verdicts_path = self.verdicts_path
        if not verdicts_path.is_file():
            Console.err(f"Verdicts import path[{verdicts_path}] is not file")
            exit(1)
        text = verdicts_path.read_text()
        csv_reader = csv.DictReader(text.splitlines())
        self.current_results = list(csv_reader)

    def _export_verdicts(self):
        verdicts_path = self.verdicts_path
        if not verdicts_path.is_file():
            Console.err(f"Verdicts export path[{verdicts_path}] is not file")
            exit(1)
        with verdicts_path.open("w") as f:
            writer = csv.DictWriter(f, fieldnames=["template_name", "filename", "verdict"])
            writer.writeheader()
            writer.writerows(self.current_results)

    def _get_fuzzing_result(self, name: str) -> Path | None:
        results = list(self.fuzzing_results_path.rglob(name))
        if len(results) == 1:
            return results[0]
        return None

    def _get_metadata(self, name: str) -> metadata.Metadata | None:
        fuzzing_result_path = self._get_fuzzing_result(name)
        if fuzzing_result_path is None:
            return None
        metadata_path = fuzzing_result_path.with_suffix(".metadata.json")
        if not metadata_path.is_file():
            return None
        return metadata.metadata_from_json(metadata_path.read_text())

    def _choose_case(self) -> dict[str, str]:
        index = random.randrange(0, len(self.current_results))
        while self.current_results[index]["verdict"] != "":
            index = random.randrange(0, len(self.current_results))
        return self.current_results[index]

    def _get_progress(self) -> tuple[int, int]:
        cases_count = len(self.current_results)
        cases_with_verdicts_count = len([case for case in self.current_results if case["verdict"] != ""])
        return cases_count, cases_with_verdicts_count

    def _get_template(self, name: str) -> tuple[template.TemplateFile, template.Template] | None:
        for tf in self.language_project.template_files:
            for t in tf.templates:
                if t.name == name:
                    return tf, t
        return None

    def _get_class(self, name: str) -> str | None:
        for helper in self.language_project.helper_files:
            for cls in helper.classes:
                if cls.name == name:
                    return cls.body
        return None

    def run(self):
        self._import_verdicts()
        process_next = True
        try:
            while process_next:
                case = self._choose_case()

                cases_count, cases_with_verdicts_count = self._get_progress()
                percentage = cases_with_verdicts_count / cases_count * 100
                name = case["filename"]
                template_name = case["template_name"]

                state = "start"
                show_text = None

                fuzzing_result = self._get_fuzzing_result(name)
                fuzzing_metadata = self._get_metadata(name)
                template_data = self._get_template(template_name)

                while state != "finished":
                    Judge._clear()

                    is_valid_files = fuzzing_result is not None and fuzzing_metadata is not None and template_data is not None
                    Console.ok(f"Progress: {cases_with_verdicts_count}/{cases_count} ({percentage:.2f}%)")

                    if is_valid_files:
                        tf, t = template_data
                        Console.ok(f"~~~ Original file metadata ~~~")
                        Console.info(f"File: {fuzzing_metadata.original_file_metadata.file_name}")
                        Console.info(f"CWEs: {fuzzing_metadata.original_file_metadata.CWEs}")
                        Console.info(f"Kind: {fuzzing_metadata.original_file_metadata.kind}")
                        Console.ok(f"~~~ Mutated file metadata ~~~")
                        Console.info(f"File: {name}")
                        for t_metadata in fuzzing_metadata.mutated_file_metadata.used_templates:
                            Console.info(f"Used template: {t_metadata.template_file}:{t_metadata.template_name}")
                        Console.ok(f"~~~ Tool results ~~~")
                        for result in fuzzing_metadata.tool_results:
                            Console.info(f"{result.tool_name}")
                            Console.info(f"\tOriginal: {result.original_found_CWEs}")
                            Console.info(f"\tMutated: {result.mutated_found_CWEs}")

                        if state == "show c":
                            Console.ok(f"~~~ Code file ~~~")
                            Judge._show_file(fuzzing_result)
                        elif state == "show t" or state == "start":
                            Console.ok(f"~~~ Template ~~~")
                            Judge._show_text(t.code.body)
                        elif state == "show tf":
                            Console.ok(f"~~~ Template ~~~")
                            Judge._show_file(tf.path)
                        elif state == "show":
                            Console.ok(f"~~~ Class ~~~")
                            Judge._show_text(show_text)

                    else:
                        Console.err(f"Invalid file[{name}] or template[{template_name}]")

                    response = input("~> ")
                    if is_valid_files and response.startswith("ok"):
                        case["verdict"] = "ok"
                        state = "finished"
                    elif is_valid_files and response.startswith("fail"):
                        case["verdict"] = response
                        state = "finished"
                    elif response == "q":
                        self._export_verdicts()
                        process_next = False
                        state = "finished"
                    elif response == "skip":
                        state = "finished"
                    elif response in ["show t", "show c", "show tf"]:
                        state = response
                    elif response.startswith("show class"):
                        parts = response.split(" ")
                        if len(parts) != 3:
                            Console.err(f"Unexpected input: {response}")
                        else:
                            class_name = parts[2]
                            cls = self._get_class(class_name)
                            if cls is not None:
                                state = "show"
                                show_text = cls
                            else:
                                Console.err(f"Can't find class: {class_name}")
                    elif response == "save":
                        self._export_verdicts()
                    else:
                        Console.err(f"Unexpected input: {response}")

        except Exception as e:
            Judge._clear()
            Console.err(f"Unexpected error: {e}")
            self._export_verdicts()

if __name__ == "__main__":
    parser = parsing.Parser()
    has_parsing_errors, project = parser.parse_project(Path("/home/viktor/Documents/Code/templates-db/languages/csharp"))
    if has_parsing_errors:
        Console.err(f"ERROR: Parsing error")
        exit(1)

    judge = Judge(
        language_project=project,
        verdicts_path=Path("/home/viktor/Documents/Code/templates-db/results.csv"),
        fuzzing_results_path=Path("/home/viktor/Documents/Code/JulietCSharp-mutated/src/testcases")
    )
    judge.run()