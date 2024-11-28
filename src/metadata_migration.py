from typing import Tuple, List

import metadata
from metadata import Metadata
from template import LanguageProject



def _find_template(template_name: str, project: LanguageProject) -> str | None:
    for tf in project.template_files:
        template_canonical_name = "/".join(tf.parents[::-1]) + "/" + tf.name
        for t in tf.templates:
            if t.name == template_name:
                return template_canonical_name


def get_migration(metadata_files: List[Tuple[str, Metadata]], project: LanguageProject) -> dict[
    metadata.TemplateMetadata, str | None]:
    migration = {}

    for path, old_metadata in metadata_files:
        for template_metadata in old_metadata.mutated_file_metadata.used_templates:

            actual_template_location = _find_template(template_metadata.template_name, project)
            if actual_template_location != template_metadata.template_file:
                migration[template_metadata] = actual_template_location

    return migration
