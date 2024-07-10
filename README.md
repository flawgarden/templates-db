# templates-db

[![Build Status](https://github.com/flawgarden/templates-db/actions/workflows/push.yml/badge.svg)](https://github.com/flawgarden/templates-db/actions)

**templates-db** is a repository for [template](docs/template-language.md) collections.
Provided templates are used for mutation-based generation SAST benchmarks.
This repository allows you to check your templates for correctness 
(in formal language terms) and perform some useful diagnostics.

## Diagnostics list

1. Language structural equality
2. Invalid imports
3. Undefined macro usage
4. Unused local defined macro
5. Invalid extensions
6. Dangling hole reference

## Diagnostics usage

For diagnostic usage follow steps:

1. Install Java (version >= 17)
2. Install Python dependencies `pip install -r requirments.txt`
3. Generate parser `./antlr.sh --generate`

Repeat step 3 on any grammar (.g4 extension) files change.

4. Run diagnostics `python3 src/main.py`

## Template contribution

If you add new template file you **should** add the similar file to all
others languages. In template file case it means file with same relative path 
and the same(by names) templates inside, otherwise required only the same relative path. 

Sometimes implemented features may be not applicable to other languages, 
in that case you should add file with same relative path and .unsupported extension.
Also, you can use .todo extension to delay implementation. In both cases you may add
some additional information in file content.

After implementation completed, run diagnostics and fix corresponding issues.

## Diagnostic contribution

If you add new diagnostic, consider adding corresponding tests. 

After implementation completed:
1. Ensure flake8 hasn't issues `flake8 src/*.py` 
2. Ensure all test passes `pytest --no-header -v`