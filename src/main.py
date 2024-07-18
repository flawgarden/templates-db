#!/usr/bin/env python
from pathlib import Path
import diagnostic
import parsing


if __name__ == '__main__':
    has_errors = False

    languages_path = Path(__file__).resolve().parent.parent / 'languages'

    tmt_files = list(languages_path.rglob('*.tmt'))
    has_errors = has_errors | diagnostic.nerd.perform_pre_parsing_diagnostics(tmt_files)

    parser = parsing.Parser()
    projects = []
    for path in languages_path.iterdir():
        projects.append(parser.parse_project(path))

    has_errors = has_errors | diagnostic.nerd.perform_diagnostics(projects)

    if has_errors:
        exit(1)
