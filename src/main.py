from pathlib import Path
from console import Console
import diagnostic
import parsing

if __name__ == '__main__':
    try:
        projects = []
        for path in Path("./languages").iterdir():
            projects.append(parsing.parse_project(path))

        has_errors = diagnostic.nerd.perform_diagnostics(projects)
        if has_errors:
            exit(1)
    except parsing.ParsingException as e:
        Console.err(e.msg)
