import re
from typing import Tuple

import metadata
from metadata import OriginalFileMetadata, MutatedFileMetadata, ToolResult, Metadata


def extract_metadata(text: str) -> Tuple[Metadata, str]:

    def parse_list(t: str, sep: str, f):
        if t == "":
            return []
        elif sep in t:
            return [f(x) for x in t.split(sep)]
        else:
            return [f(t)]

    def parse_template_metadata(t: str):
        m = re.search(r'Insert template from (?P<template_file>.+) with name (?P<template_name>.+)', t)
        return m.group("template_file"), m.group("template_name")

    file_name = ""
    file_name_regexp = re.compile(r'Original file name: (?P<file_name>.+)')
    original_CWEs = []
    original_CWEs_regexp = re.compile(r'Original file CWE\'s: \[(?P<int_list>.*)]')
    kind = ""
    kind_regexp = re.compile(r'Original file kind: (?P<kind>pass|fail)')

    tool_results = []
    original_found_CWEs = {}
    original_found_CWEs_regex = re.compile(r'(?P<tool_name>\w+) original results: \[(?P<int_list>.*)]')
    mutated_found_CWEs = {}
    mutated_found_CWEs_regex = re.compile(r'(?P<tool_name>\w+) analysis results: \[(?P<int_list>.*)]')

    used_templates = []
    used_templates_regex = re.compile(r'Mutation info: (?P<templates_list>.+)', re.DOTALL)
    used_extensions = []
    used_extensions_regex = re.compile(r'Used extensions:(?P<extensions_list>.*)', re.DOTALL)

    lines_to_delete = []
    for line in text.splitlines():

        lines_to_delete.append(line)

        if (match := file_name_regexp.search(line)) is not None:
            file_name = match.group("file_name")
        elif (match := original_CWEs_regexp.search(line)) is not None:
            original_CWEs = parse_list(match.group("int_list"), ",", int)
        elif (match := kind_regexp.search(line)) is not None:
            kind = match.group("kind")
        elif (match := original_found_CWEs_regex.search(line)) is not None:
            original_found_CWEs[match.group("tool_name")] = parse_list(match.group("int_list"), ",", int)
        elif (match := mutated_found_CWEs_regex.search(line)) is not None:
            mutated_found_CWEs[match.group("tool_name")] = parse_list(match.group("int_list"), ",", int)
        elif (match := used_templates_regex.search(line)) is not None:
            used_templates = parse_list(match.group("templates_list"), ",", parse_template_metadata)
        elif (match := used_extensions_regex.search(line)) is not None:
            used_extensions = parse_list(match.group("extensions_list"), " | ", str)
        elif line.count("Program") > 0:
            pass
        elif line.count("-------------") > 0:
            pass
        else:
            lines_to_delete.pop()

    for tool_name in original_found_CWEs.keys():
        tool_results.append(ToolResult(
            tool_name=tool_name,
            original_found_CWEs=original_found_CWEs[tool_name],
            mutated_found_CWEs=mutated_found_CWEs[tool_name]
        ))

    original_file_metadata = OriginalFileMetadata(
        file_name=file_name,
        CWEs=original_CWEs,
        kind=kind,
        region=None
    )

    mutated_file_metadata = MutatedFileMetadata(
        used_templates=used_templates,
        used_extensions=used_extensions,
        region=None
    )

    new_text = text
    for line in lines_to_delete:
        new_text = new_text.replace(line, "")

    return Metadata(
        original_file_metadata=original_file_metadata,
        mutated_file_metadata=mutated_file_metadata,
        tool_results=tool_results
    ), new_text


test_text = """
//Snyk original results: [601]
//CodeQL original results: [601]
//Insider original results: []
//Semgrep original results: []
//-------------
//Insider analysis results: []
//Semgrep analysis results: []
//Snyk analysis results: []
//CodeQL analysis results: [835, 601, 563]
//Original file name: src/testcases/CWE601_Open_Redirect/CWE601_Open_Redirect__Web_QueryString_Web_05.cs
//Original file CWE's: [601]
//Original file kind: fail
//Program:
// Mutation info: Insert template from sensitivity/virtuality/interface with name base_binary_op_interface_positive
// Used extensions: 123 | 234

class Test {

}
"""

if __name__ == "__main__":
    parsed_data, new_text = extract_metadata(test_text)
    print(metadata.metadata_to_json(parsed_data))
    print("**********************************************************")
    print(new_text.count("\n"), test_text.count("\n"))