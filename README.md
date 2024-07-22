# templates-db

[![Build Status](https://github.com/flawgarden/templates-db/actions/workflows/push.yml/badge.svg)](https://github.com/flawgarden/templates-db/actions)

**templates-db** is a repository for [template](docs/template-language.md) collections.
The provided templates are used to generate SAST benchmarks for mutation-based generation.
This repository allows you to check your templates for correctness 
(in formal language terms) and perform some functional diagnostics.

## Diagnostics list

1. Language structural equality
2. Invalid imports
3. Undefined macro usage
4. Unused locally defined macro
5. Invalid extensions
6. Dangling hole reference

## Diagnostics usage

For diagnostic usage, follow steps:

1. Install Java (version >= 17)
2. Install Python dependencies `pip install -r requirments.txt`
3. Generate parser `./antlr.sh --generate`

Repeat step 3 on any grammar (.g4 extension) file change.

4. Run diagnostics `python3 src/main.py`

## Template contribution

If you add a new template file, you **should** add a similar file to all
other languages. In template file case, it means a file with the same relative path 
and the same(by name) templates inside. Otherwise, it requires only the same relative path. 

Sometimes, implemented features may only apply to some languages. In that case, you should add a file with the same relative path and `.unsupported` extension.
Also, you can use `.todo` extension to delay implementation. In both cases, you may add
some additional information in the file content.

After making new templates, run diagnostics and fix corresponding issues.

## Diagnostic contribution

If you add a new diagnostic, consider adding corresponding tests. 

After getting a new diagnostic implemented:
1. Ensure flake8 hasn't issues `flake8 src/*.py` 
2. Ensure all test passes `pytest --no-header -v`
