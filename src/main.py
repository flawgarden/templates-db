#!/usr/bin/env python
import dataclasses
from pathlib import Path
import diagnostic
import parsing
import argparse
import metadata_extraction
import metadata_migration
import metadata
import coverage
import difflib

from console import Console
from metadata import Metadata, MutatedFileMetadata
from template import LanguageProject

languages_path = Path(__file__).resolve().parent.parent / 'languages'
supported_languages = ["cs", "py", "go", "java"]

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

def get_metadata(files):
    all_metadata = []
    for file in files:
        metadata_file = file.with_suffix(".json")
        if not metadata_file.exists():
            Console.err(f"ERROR: metadata for file [{file}] doesn't exist")
            exit(1)
        metadata_text = metadata_file.read_text()
        file_metadata = metadata.metadata_from_json(metadata_text)
        all_metadata.append((metadata_file, file_metadata))
    return all_metadata

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

    files_path = Path(extract_metadata_args.path)
    if not files_path.is_dir():
        Console.err(f"ERROR: Specified invalid path: {files_path}")
        exit(1)

    file_extension = extract_metadata_args.language
    files = list(files_path.rglob(f"*.{file_extension}"))

    remove_inline_metadata = extract_metadata_args.remove_inline_metadata

    for file in files:

        metadata_file = file.with_suffix(".json")
        if metadata_file.exists():
            Console.warn(f"WARNING: metadata for file [{file}] already exist")
            continue

        content = file.read_text()
        file_metadata, new_content = metadata_extraction.extract_metadata(content)

        metadata_file.write_text(metadata.metadata_to_json(file_metadata))

        if remove_inline_metadata:
            file.write_text(new_content)


def collect_coverage(collect_coverage_args):

    files_path = Path(collect_coverage_args.path)
    if not files_path.is_dir():
        Console.err(f"ERROR: Specified invalid path: {files_path}")
        exit(1)

    file_extension = collect_coverage_args.language
    files = list(files_path.rglob(f"*.{file_extension}"))

    show_covered_templates = collect_coverage_args.show_covered_templates
    show_uncovered_templates = collect_coverage_args.show_uncovered_templates
    show_file_coverage = collect_coverage_args.show_uncovered_templates | show_covered_templates | show_uncovered_templates

    all_metadata = list(map(lambda x: x[1], get_metadata(files)))

    project = get_language_project_by_extension(file_extension)
    total_coverage, template_coverage = coverage.calculate_coverage(project, all_metadata)

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
    files_path = Path(migrate_metadata_args.path)
    if not files_path.is_dir():
        Console.err(f"ERROR: Specified invalid path: {files_path}")
        exit(1)

    file_extension = migrate_metadata_args.language
    files = list(files_path.rglob(f"*.{file_extension}"))

    all_metadata = get_metadata(files)
    project = get_language_project_by_extension(file_extension)

    migration = metadata_migration.get_migration(all_metadata, project)

    Console.info("Migrations list:")
    for old_location in migration:
        template_file, template_name = old_location
        new_location = migration[old_location]
        if new_location is None:
            Console.err(f"Can't find [{template_file}:{template_name}] in actual language project, required manual resolution")
            exit(1)
        else:
            Console.warn(f"{template_name}: {template_file} -> {new_location}")

    if not migrate_metadata_args.apply:
        return

    for metadata_path, metadata_content in all_metadata:
        new_used_templates = []

        for (template_file_path, template_name) in metadata_content.mutated_file_metadata.used_templates:
            location = template_file_path, template_name
            if location in migration:
                new_used_templates.append([migration[location], template_name])
            else:
                new_used_templates.append([template_file_path, template_name])

        new_metadata = Metadata(
            original_file_metadata=metadata_content.original_file_metadata,
            mutated_file_metadata=MutatedFileMetadata(
                used_templates=new_used_templates,
                used_extensions=metadata_content.mutated_file_metadata.used_extensions,
                region=metadata_content.mutated_file_metadata.region
            ),
            tool_results=metadata_content.tool_results
        )

        if metadata_content != new_metadata:
            Console.warn(f"Applying migration for file[{metadata_path}]")
            metadata_path.write_text(metadata.metadata_to_json(new_metadata))


if __name__ == '__main__':
    parser = get_args_parser()
    args = parser.parse_args()
    if args.command_name == "perform-diagnostics":
        perform_diagnostics()
    elif args.command_name == "extract-metadata":
        extract_metadata(args)
    elif args.command_name == "collect-coverage":
        collect_coverage(args)
    elif args.command_name == "migrate-metadata":
        migrate_metadata(args)
    else:
        exit(1)