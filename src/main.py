#!/usr/bin/env python
from pathlib import Path
from console import Console
import diagnostic
import parsing

if __name__ == '__main__':
    try:
        has_errors = False

        tmt_files = list(Path('./languages').rglob('*.tmt'))
        has_errors = has_errors or diagnostic.nerd.perform_pre_parsing_diagnostics(tmt_files)

        projects = []
        for path in Path("./languages").iterdir():
            projects.append(parsing.parse_project(path))

        has_errors = has_errors or diagnostic.nerd.perform_diagnostics(projects)
        if has_errors:
            exit(1)
    except parsing.ParsingException as e:
        Console.err(e.msg)
