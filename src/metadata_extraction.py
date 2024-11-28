import re
from typing import Tuple, List, Any

import metadata
from metadata import OriginalFileMetadata, MutatedFileMetadata, ToolResult, Metadata, TemplateMetadata



def extract_metadata(text: str) -> Tuple[List[str], Metadata, List[int]]:

    def parse_list(t: str, sep: str, f):
        if t == "":
            return []
        elif sep in t:
            return [f(x) for x in t.split(sep)]
        else:
            return [f(t)]

    def parse_template_metadata(t: str):
        m = re.search(r'Insert template from (?P<template_file>.+) with name (?P<template_name>\w+)', t)
        return TemplateMetadata(m.group("template_file"), m.group("template_name"))

    def parse_region(m: re.Match) -> metadata.CodeRegion:
        start_line = m.group("start_line")
        end_line = m.group("end_line")
        start_column = m.group("start_column")
        end_column = m.group("end_column")
        return metadata.CodeRegion(
            start_line=None if start_line == "null" else int(start_line),
            end_line=None if end_line == "null" else int(end_line),
            start_column=None if start_column == "null" else int(start_column),
            end_column=None if end_column == "null" else int(end_column)
        )

    def found_uninitialized_values(values: List[Tuple[str, Any | None]]) -> List[str]:
        result = []
        for name, value in values:
            if value is None:
                result.append(name)
        return result

    file_name = None
    file_name_regexp = re.compile(r'Original file name: (?P<file_name>.+)')
    original_CWEs = None
    original_CWEs_regexp = re.compile(r'Original file CWE\'s: \[(?P<int_list>.*)]')
    kind = None
    kind_regexp = re.compile(r'Original file kind: (?P<kind>pass|fail)')

    original_region = None
    original_region_regex = re.compile(r'Original file region: (?P<start_line>\w+), (?P<end_line>\w+), (?P<start_column>\w+), (?P<end_column>\w+)')
    mutated_region = None
    mutated_region_regex = re.compile(r'Mutated file region: (?P<start_line>\w+), (?P<end_line>\w+), (?P<start_column>\w+), (?P<end_column>\w+)')

    tool_results = []
    original_found_CWEs = {}
    original_found_CWEs_regex = re.compile(r'(?P<tool_name>\w+) original results: \[(?P<int_list>.*)]')
    mutated_found_CWEs = {}
    mutated_found_CWEs_regex = re.compile(r'(?P<tool_name>\w+) analysis results: \[(?P<int_list>.*)]')

    used_templates = None
    used_templates_regex = re.compile(r'Mutation info: (?P<templates_list>.+)', re.DOTALL)
    used_extensions = None
    used_extensions_regex = re.compile(r'Used extensions:(?P<extensions_list>.*)', re.DOTALL)

    lines_to_delete = []
    for index, line in enumerate(text.splitlines()):

        lines_to_delete.append(index)

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
        elif (match := original_region_regex.search(line)) is not None:
            original_region = parse_region(match)
        elif (match := mutated_region_regex.search(line)) is not None:
            mutated_region = parse_region(match)
        elif line.count("Program") > 0:
            pass
        elif line.count("-------------") > 0:
            pass
        else:
            lines_to_delete.pop()

    if len(original_found_CWEs) == 0:
        original_found_CWEs = None
    if len(mutated_found_CWEs) == 0:
        mutated_found_CWEs = None

    uninitialized = found_uninitialized_values([
        ("file name", file_name),
        ("kind", kind),
        ("used templates", used_templates),
        ("original CWEs", original_CWEs)
    ])

    if len(uninitialized) > 0:
        return uninitialized, None, None

    filtered_extensions = []
    if used_extensions is not None:
        for ext in used_extensions:
            if len(ext) == ext.count(" "):
                continue
            filtered_extensions.append(ext)

    if original_found_CWEs is not None:
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
        region=original_region
    )

    mutated_file_metadata = MutatedFileMetadata(
        used_templates=used_templates,
        used_extensions=filtered_extensions,
        region=mutated_region
    )

    return [], Metadata(
        original_file_metadata=original_file_metadata,
        mutated_file_metadata=mutated_file_metadata,
        tool_results=tool_results
    ), lines_to_delete


test_text = """
//Original file region: 31, 60, null, null
//Mutated file region: 50, 85, null, null
//CodeQL original results: [78]
//Snyk original results: [78]
//Semgrep original results: []
//Insider original results: []
//-------------
//Semgrep analysis results: []
//CodeQL analysis results: [78, 88]
//Snyk analysis results: []
//Insider analysis results: []
//Original file name: src/testcases/CWE78_OS_Command_Injection/CWE78_OS_Command_Injection__Params_Get_Web_31.cs
//Original file CWE's: [78]
//Original file kind: fail
//Program:
// Mutation info: Insert template from sensitivity/assignment with name lazy_eval_positive
// Used extensions: 
using System;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
/* TEMPLATE GENERATED TESTCASE FILE
Filename: MutatedCWE78_OS_Command_Injection__Params_Get_Web_31344994.cs
Label Definition File: CWE78_OS_Command_Injection.label.xml
Template File: sources-sink-31.tmpl.cs
*/
/*
 * @description
 * CWE: 78 OS Command Injection
 * BadSource: Params_Get_Web Read data from a querystring using Params.Get()
 * GoodSource: A hardcoded string
 * Sinks: exec
 *    BadSink : dynamic command execution with Runtime.getRuntime().exec()
 * Flow Variant: 31 Data flow: make a copy of data within the same method
 *
 * */

using TestCaseSupport;
using System;

using System.Diagnostics;
using System.Runtime.InteropServices;

using System.Web;


namespace testcases.CWE78_OS_Command_Injection
{

class MutatedCWE78_OS_Command_Injection__Params_Get_Web_31344994 : AbstractTestCaseWeb
{
#if (!OMITBAD)
    /* uses badsource and badsink */
    public override void Bad(HttpRequest req, HttpResponse resp)
    {
        string dataCopy;
        {
            string data;
            /* POTENTIAL FLAW: Read data from a querystring using Params.Get */
            data = req.Params.Get("name");
            dataCopy = data;
        }
        {
            string data = dataCopy;
            String osCommand;
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                /* running on Windows */
                osCommand = "c:\\WINDOWS\\SYSTEM32\\cmd.exe /c dir ";
            }
            else
            {
                /* running on non-Windows */
                osCommand = "/bin/ls ";
            }
            /* POTENTIAL FLAW: command injection */
Func<string> lazyValue;
{
    string uniquePampam = data;
    lazyValue = () => uniquePampam;
}
data = lazyValue();
            Process process = Process.Start(osCommand + data);
            process.WaitForExit();
        }
    }
#endif //omitbad
#if (!OMITGOOD)
    public override void Good(HttpRequest req, HttpResponse resp)
    {
        GoodG2B(req, resp);
    }

    /* goodG2B() - use goodsource and badsink */
    private void GoodG2B(HttpRequest req, HttpResponse resp)
    {
        string dataCopy;
        {
            string data;
            /* FIX: Use a hardcoded string */
            data = "foo";
            dataCopy = data;
        }
        {
            string data = dataCopy;
            String osCommand;
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                /* running on Windows */
                osCommand = "c:\\WINDOWS\\SYSTEM32\\cmd.exe /c dir ";
            }
            else
            {
                /* running on non-Windows */
                osCommand = "/bin/ls ";
            }
            /* POTENTIAL FLAW: command injection */
            Process process = Process.Start(osCommand + data);
            process.WaitForExit();
        }
    }
#endif //omitgood
}
}
"""

if __name__ == "__main__":
    errors, parsed_data, lines = extract_metadata(test_text)
    print(metadata.metadata_to_json(parsed_data))
    print("**********************************************************")
    print(lines)