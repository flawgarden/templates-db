import json
from dataclasses import dataclass
from typing import List
from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class CodeRegion:
    start_line: int | None
    end_line: int | None
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


@dataclass(unsafe_hash=True)
class TemplateMetadata:
    template_file: str
    template_name: str


@dataclass
class MutatedFileMetadata:
    used_templates: List[TemplateMetadata]
    used_extensions: List[str]
    region: CodeRegion | None


@dataclass
class Metadata(DataClassJSONMixin):
    original_file_metadata: OriginalFileMetadata
    mutated_file_metadata: MutatedFileMetadata
    tool_results: List[ToolResult]

def _prettify_json(text: str) -> str:
    return json.dumps(json.loads(text), indent=4)

def metadata_to_json(metadata: Metadata) -> str:
    return _prettify_json(metadata.to_json())

def metadata_from_json(text: str) -> Metadata:
    return Metadata.from_json(text)

def copy(metadata: Metadata) -> Metadata:
    return metadata_from_json(metadata_to_json(metadata))

if __name__ == "__main__":
    obj = Metadata(
        original_file_metadata=OriginalFileMetadata(
            file_name="src/kek.cs",
            CWEs=[100, 200, 300],
            kind="fail",
            region=CodeRegion(10, 20, None, None)
        ),
        mutated_file_metadata=MutatedFileMetadata(
            used_templates=[TemplateMetadata("sensitivity/if", "if_simple_negative")],
            used_extensions=["~[EXPR_int]~ -> 42", "~[EXPR_bool]~ -> true"],
            region=CodeRegion(15, 25, None, None)
        ),
        tool_results=[
            ToolResult(tool_name="Semgrep", original_found_CWEs=[100, 200, 300], mutated_found_CWEs=[100]),
            ToolResult(tool_name="CodeQL", original_found_CWEs=[100, 200, 300], mutated_found_CWEs=[100, 200])
        ]
    )
    s = metadata_to_json(obj)
    print(s)
    print(obj)
    print(metadata_from_json(s))
