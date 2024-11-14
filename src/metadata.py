import dataclasses
from dataclasses import dataclass
from typing import List
import json

@dataclass
class CodeRegion:
    start_line: int
    end_line: int
    start_column: int | None
    end_column: int | None

@dataclass
class OriginalFileMetadata:
    file_name: str
    CWEs: List[int]
    kind: str
    region: CodeRegion | None

@dataclass
class ToolResult:
    tool_name: str
    original_found_CWEs: List[int]
    mutated_found_CWEs: List[int]

@dataclass
class MutatedFileMetadata:
    used_templates: List[List[str]] # Actually tuple inside, but its ruin (serialize . deserialize = id)
    used_extensions: List[str]
    region: CodeRegion | None

@dataclass
class Metadata:
    original_file_metadata: OriginalFileMetadata
    mutated_file_metadata: MutatedFileMetadata
    tool_results: List[ToolResult]


def _dataclass_from_dict(klass, d):
    try:
        field_types = {f.name:f.type for f in dataclasses.fields(klass)}
        return klass(**{f:_dataclass_from_dict(field_types[f], d[f]) for f in d})
    except TypeError:
        return d

def metadata_to_json(metadata: Metadata) -> str:
    return json.dumps(dataclasses.asdict(metadata), indent=4)

def metadata_from_json(text: str) -> Metadata:
    return _dataclass_from_dict(Metadata, json.loads(text))

if __name__ == "__main__":
    obj = Metadata(
        original_file_metadata=OriginalFileMetadata(
            file_name="src/kek.cs",
            CWEs=[100, 200, 300],
            kind="fail",
            region=CodeRegion(10, 20, None, None)
        ),
        mutated_file_metadata=MutatedFileMetadata(
            used_templates=[("sensitivity/if", "if_simple_negative")],
            used_extensions=["~[EXPR_int]~ -> 42", "~[EXPR_bool]~ -> true"],
            region = CodeRegion(15, 25, None, None)
        ),
        tool_results=[
            ToolResult(tool_name="Semgrep", original_found_CWEs=[100, 200, 300], mutated_found_CWEs=[100]),
            ToolResult(tool_name="CodeQL", original_found_CWEs=[100, 200, 300], mutated_found_CWEs=[100, 200])
        ]
    )
    s = metadata_to_json(obj)
    print(s)
    print(metadata_from_json(s))