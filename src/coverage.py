from typing import List, Tuple

import metadata
import template
import console

def calculate_coverage(project: template.LanguageProject, metadata_list: List[metadata.Metadata]) -> Tuple[float, dict[str, Tuple[float, dict[str, bool]]]]:
    covered = {}
    for tf in project.template_files:
        template_canonical_name = "/".join(tf.parents[::-1]) + "/" + tf.name
        covered[template_canonical_name] = {}
        for t in tf.templates:
            covered[template_canonical_name][t.name] = False

    for m in metadata_list:
        used_templates = m.mutated_file_metadata.used_templates
        for tf, t in used_templates:
            if tf not in covered:
                console.Console.warn(f"WARNING: project doesn't contain template [{tf} {t}] from metadata")
                continue
            if t not in covered[tf]:
                console.Console.warn(f"WARNING: project doesn't contain template [{tf} {t}] from metadata")
                continue
            covered[tf][t] = True

    uncovered_count = 0
    covered_count = 0
    result = {}
    for tf_name in covered:
        result[tf_name] = {}
        covered_by_group = 0
        uncovered_by_group = 0
        for t_name in covered[tf_name]:
            if covered[tf_name][t_name]:
                covered_by_group += 1
                covered_count += 1
            else:
                uncovered_by_group += 1
                uncovered_count += 1
        total_count = covered_by_group + uncovered_by_group
        if total_count == 0:
            group_coverage = 100
        else:
            group_coverage = (covered_by_group / total_count) * 100
        result[tf_name] = group_coverage, covered[tf_name]

    coverage = 100 * (covered_count / (covered_count + uncovered_count))
    return coverage, result
