from typing import Tuple, List

import metadata
from metadata import OriginalFileMetadata, MutatedFileMetadata, ToolResult, Metadata
from template import LanguageProject
import console


def _find_template(template_name: str, project: LanguageProject) -> str | None:
    for tf in project.template_files:
        template_canonical_name = "/".join(tf.parents[::-1]) + "/" + tf.name
        for t in tf.templates:
            if t.name == template_name:
                return template_canonical_name

def get_migration(metadata_files: List[Tuple[str, Metadata]], project: LanguageProject) -> dict[Tuple[str, str], str | None]:
    migration = {}

    for path, old_metadata in metadata_files:
        for metadata_template_location, template_name in old_metadata.mutated_file_metadata.used_templates:
            actual_template_location = _find_template(template_name, project)
            if actual_template_location != metadata_template_location:
                migration[metadata_template_location, template_name] = actual_template_location

    return migration