#!/usr/bin/env python3
from pathlib import Path
from typing import List

import diagnostic
import parsing
import argparse
import metadata_extraction
import metadata_migration
import metadata
import coverage

from console import Console
from template import LanguageProject

languages_path = Path(__file__).resolve().parent.parent / 'languages'
supported_languages = ["cs", "py", "go", "java"]

# add metadata prefix
def get_args_parser():
    arg_parser = argparse.ArgumentParser()
    subparsers = arg_parser.add_subparsers(dest="command_name")

    _ = subparsers.add_parser(
        "perform-diagnostics",
        help="perform template language diagnostics"
    )

    collect_coverage_parser = subparsers.add_parser(
        "collect-coverage",
        help="collect template coverage by provided fuzzing results"
    )
    collect_coverage_parser.add_argument(
        "language",
        choices=supported_languages,
        help="target language extension",
    )
    collect_coverage_parser.add_argument(
        "path",
        help="path to fuzzing results",
    )
    collect_coverage_parser.add_argument(
        "--show-file-coverage",
        help="print coverage per each file",
        action="store_true"
    )
    collect_coverage_parser.add_argument(
        "--show-uncovered-templates",
        help="print uncovered templates names",
        action="store_true"
    )
    collect_coverage_parser.add_argument(
        "--show-covered-templates",
        help="print covered templates names and corresponding files",
        action="store_true"
    )
    collect_coverage_parser.add_argument(
        "--exclude-objects",
        help="exclude objects templates from coverage",
        action="store_true"
    )

    extract_metadata_parser = subparsers.add_parser(
        "extract-metadata",
        help="extract metadata from provided fuzzing results"
    )
    extract_metadata_parser.add_argument(
        "language",
        choices=supported_languages,
        help="target language extension",
    )
    extract_metadata_parser.add_argument(
        "path",
        help="path to fuzzing results",
    )
    extract_metadata_parser.add_argument(
        "--remove-inline-metadata",
        help="replace metadata in fuzzing results with empty lines",
        action="store_true"
    )
    extract_metadata_parser.add_argument(
        "--file-prefix",
        help="filter file without specified prefix"
    )
    extract_metadata_parser.add_argument(
        "--no-warn-on-existed",
        help="doesn't display warning for existed metadata",
        action="store_true"
    )

    migrate_metadata_parser = subparsers.add_parser(
        "migrate-metadata",
        help="migrate template location in metadata corresponding to actual locations in language project"
    )
    migrate_metadata_parser.add_argument(
        "language",
        choices=supported_languages,
        help="target language extension",
    )
    migrate_metadata_parser.add_argument(
        "path",
        help="path to fuzzing results",
    )
    migrate_metadata_parser.add_argument(
        "--apply",
        help="apply created migration, just print migration otherwise",
        action="store_true"
    )

    return arg_parser

def get_metadata_path(p: Path) -> Path:
    return p.with_suffix(".metadata.json")

def get_metadata_from_directory(path: Path):
    return list(path.rglob(f"*.metadata.json"))

def get_language_files_from_directory(common_args):
    files_path = Path(common_args.path)
    if not files_path.is_dir():
        Console.err(f"ERROR: Specified invalid path: {files_path}")
        exit(1)

    prefix = common_args.file_prefix if common_args.file_prefix is not None else ""
    file_extension = common_args.language
    return list(files_path.rglob(f"{prefix}*.{file_extension}"))


def get_language_project_by_extension(file_extension: str) -> LanguageProject:
    if file_extension == "cs":
        project_dir = "csharp"
    elif file_extension == "java":
        project_dir = "java"
    elif file_extension == "py":
        project_dir = "python"
    elif file_extension == "go":
        project_dir = "go"
    else:
        assert False

    project_path = languages_path / project_dir
    parser = parsing.Parser()
    has_parsing_errors, project = parser.parse_project(project_path)
    if has_parsing_errors:
        Console.err(f"ERROR: Parsing error")
        exit(1)

    return project


def perform_diagnostics():
    has_errors = False

    tmt_files = list(languages_path.rglob('*.tmt'))
    has_errors = has_errors | diagnostic.nerd.perform_pre_parsing_diagnostics(tmt_files)

    parser = parsing.Parser()
    projects = []
    for path in languages_path.iterdir():
        has_parsing_errors, project = parser.parse_project(path)
        projects.append(project)
        has_errors = has_errors or has_parsing_errors

    has_errors = has_errors | diagnostic.nerd.perform_diagnostics(projects)

    if has_errors:
        exit(1)


def extract_metadata(extract_metadata_args):
    files = get_language_files_from_directory(extract_metadata_args)

    # tmp code start
    # for file in files:
    #
    #     new_text = ""
    #     text = file.read_text()
    #
    #     skip_other = False
    #     for index, line in enumerate(text.splitlines()):
    #
    #         if skip_other:
    #             new_text += f"{line}\n"
    #             continue
    #
    #         if line.count("//") == 0:
    #             skip_other = True
    #             new_text += f"\n{line}\n"
    #             continue
    #
    #         if (not line.count("Original") > 0 and
    #                 not line.count("Mutation info") > 0 and
    #                 not line.count("Used") > 0 and
    #                 not line.count("Program") > 0 and
    #                 line.count("//") > 0 and
    #                 not skip_other):
    #             assert False
    #             # new_text += line[2:]
    #         # else:
    #         #     new_text += f"\n{line}"
    #
    #
    #     # new_text = new_text[1:]
    #     # file.write_text(new_text)
    #
    # return
    # tmp code end
    remove_inline_metadata = extract_metadata_args.remove_inline_metadata

    for file in files:

        metadata_file = get_metadata_path(file)

        if metadata_file.exists():
            if not extract_metadata_args.no_warn_on_existed:
                Console.warn(f"WARNING: metadata for file [{file}] already exist")
            continue

        content = file.read_text()

        missed_data, file_metadata, lines_to_delete = metadata_extraction.extract_metadata(content)
        if len(missed_data) > 0:
            Console.warn(f"WARNING: Missed metadata in file[{file}]")
            for data in missed_data:
                Console.warn(f"  - {data}")
            continue

        if remove_inline_metadata:

            new_text = ""
            for index, line in enumerate(content.splitlines()):
                if index not in lines_to_delete:
                    new_text += f"{line}\n"

            if file_metadata.mutated_file_metadata.region is not None:
                new_start_line = file_metadata.mutated_file_metadata.region.start_line
                new_end_line = file_metadata.mutated_file_metadata.region.end_line
                saved_start_line = new_start_line
                saved_end_line = new_end_line
                for line in lines_to_delete:
                    if line <= saved_start_line:
                        if new_start_line is not None:
                            new_start_line -= 1
                        if new_end_line is not None:
                            new_end_line -= 1
                    elif saved_end_line > line >= saved_start_line:
                        if new_end_line is not None:
                            new_end_line -= 1
                file_metadata.mutated_file_metadata.region.start_line = new_start_line
                file_metadata.mutated_file_metadata.region.end_line = new_end_line

            file.write_text(new_text)

        metadata_file.write_text(metadata.metadata_to_json(file_metadata))

def collect_coverage(collect_coverage_args):
    file_extension = collect_coverage_args.language

    show_covered_templates = collect_coverage_args.show_covered_templates
    show_uncovered_templates = collect_coverage_args.show_uncovered_templates
    show_file_coverage = collect_coverage_args.show_uncovered_templates | show_covered_templates | show_uncovered_templates

    metadata_files = get_metadata_from_directory(Path(collect_coverage_args.path))
    metadata_contents = [ metadata.metadata_from_json(path.read_text()) for path in metadata_files]

    project = get_language_project_by_extension(file_extension)
    total_coverage, template_coverage = coverage.calculate_coverage(project, metadata_contents, collect_coverage_args.exclude_objects)

    Console.info(f"Total coverage: {total_coverage:.2f}%")
    for template_file_name in template_coverage:
        template_file_coverage, templates_results = template_coverage[template_file_name]
        if show_file_coverage:
            Console.info(f"{template_file_name}: {template_file_coverage:.2f}%")
        for template_name in templates_results:
            if show_covered_templates and templates_results[template_name]:
                Console.ok(f"\t{template_name} covered")
            if show_uncovered_templates and not templates_results[template_name]:
                Console.err(f"\t{template_name} uncovered")




def migrate_metadata(migrate_metadata_args):
    # # tmp code start
    # metadata_files = get_metadata_from_directory(Path(migrate_metadata_args.path))
    # metadata_contents = [metadata.metadata_from_json(path.read_text()) for path in metadata_files]
    # metadata_content_with_file = list(zip(metadata_files, metadata_contents))
    #
    # for metadata_path, metadata_content in metadata_content_with_file:
    #     source_file = metadata_path.with_suffix("").with_suffix(f".{migrate_metadata_args.language}")
    #
    #     lines = list(source_file.read_text().splitlines())
    #
    #     start = metadata_content.mutated_file_metadata.region.start_line
    #     end = metadata_content.mutated_file_metadata.region.end_line
    #     print("--------------------")
    #     print(f"{lines[start + 1]}")
    #     print(f"{lines[end + 1]}")
    # return
    # # tmp code end

    if not migrate_metadata_args.apply:
        Console.warn("Migration will not be applied, to apply it specify the --apply option")
    file_extension = migrate_metadata_args.language

    metadata_files = get_metadata_from_directory(Path(migrate_metadata_args.path))
    metadata_contents = [metadata.metadata_from_json(path.read_text()) for path in metadata_files]
    metadata_content_with_file = list(zip(metadata_files, metadata_contents))
    project = get_language_project_by_extension(file_extension)

    migration = metadata_migration.get_migration(metadata_content_with_file, project)

    Console.info("Template migrations list:")
    for old_location in migration:
        new_location = migration[old_location]
        if new_location is None:
            Console.err(
                f"Can't find [{old_location.template_file}:{old_location.template_name}] in actual language project, required manual resolution"
            )
            exit(1)
        else:
            Console.info(f"\t{old_location.template_name}: {old_location.template_file} -> {new_location}")

    Console.info("Affected files list:")
    for metadata_path, metadata_content in metadata_content_with_file:
        new_used_templates = []
        has_changes = False

        for template_metadata in metadata_content.mutated_file_metadata.used_templates:
            if template_metadata in migration:
                has_changes = True
                new_used_templates.append(
                    metadata.TemplateMetadata(migration[template_metadata], template_metadata.template_name)
                )
            else:
                new_used_templates.append(template_metadata)

        if has_changes:
            Console.info(f"\t{metadata_path}")
            if migrate_metadata_args.apply:
                new_metadata = metadata.copy(metadata_content)
                new_metadata.mutated_file_metadata.used_templates = new_used_templates

                metadata_path.write_text(metadata.metadata_to_json(new_metadata))

import csv

if __name__ == '__main__':
    print("template_name,filename,verdict")
    with open("sast_diffs.csv") as f:
        csvreader = csv.reader(f)
        for [a, b] in csvreader:
             for x in b.splitlines():
                 print(f"{a},{x},")

    # parser = get_args_parser()
    # args = parser.parse_args()
    # if args.command_name == "perform-diagnostics":
    #     perform_diagnostics()
    # elif args.command_name == "extract-metadata":
    #     extract_metadata(args)
    # elif args.command_name == "collect-coverage":
    #     collect_coverage(args)
    # elif args.command_name == "migrate-metadata":
    #     migrate_metadata(args)
    # else:
    #     exit(1)
