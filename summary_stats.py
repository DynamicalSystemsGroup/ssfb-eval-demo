#!/usr/bin/env python3
"""Print summary statistics for a completed experiment directory.

Usage:
    .venv/bin/python summary_stats.py trajectories/batch_25
"""

import argparse
import json
import sys
from pathlib import Path

from apollo_eval.ontology_loader import OntologyLoader
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import Question
from apollo_eval.question_loader import build_question_bank
from apollo_eval.evaluation import EvaluationLayer


def main():
    parser = argparse.ArgumentParser(description="Summary statistics for an experiment")
    parser.add_argument("experiment_dir", type=str,
                        help="Path to directory containing trajectory JSON files")
    parser.add_argument("--owl-path", type=str, default=None,
                        help="Path or URL to OWL ontology (default: auto-detect from trajectories or OBO PURL)")
    parser.add_argument("--similarity-threshold", type=float, default=None,
                        help="Similarity threshold (default: auto-detect from trajectories or 1.0)")
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    if not experiment_dir.is_dir():
        print(f"Error: {experiment_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    json_files = sorted(experiment_dir.glob("*.json"))
    if not json_files:
        print(f"Error: no JSON files found in {experiment_dir}", file=sys.stderr)
        sys.exit(1)

    # Try to read metadata from the first trajectory
    with open(json_files[0]) as f:
        sample = json.load(f)

    owl_path = args.owl_path or sample.get("ontology_source")
    similarity_threshold = args.similarity_threshold
    if similarity_threshold is None:
        similarity_threshold = sample.get("similarity_threshold", 1.0)

    meta_fields = ["model", "ontology_source", "similarity_threshold", "exit_criteria"]
    has_meta = any(k in sample for k in meta_fields)

    # Load ontology and build questions
    print("Loading ontology...", end=" ", flush=True)
    loader = OntologyLoader(owl_path) if owl_path else OntologyLoader()
    graph = loader.load_graph()
    graph = loader.apply_reasoning(graph)
    ontology = OntologyVocabularyBuilder(graph).build(
        similarity_threshold=similarity_threshold,
    )
    Question.ontology = ontology
    questions = build_question_bank(ontology)
    print("done.")

    # Evaluate
    evaluator = EvaluationLayer(str(experiment_dir), questions)
    df = evaluator.build_dataframe()
    exp = evaluator.experiment_summary(df)

    # Build report
    lines = []

    if has_meta:
        lines.append(f"{'=' * 60}")
        lines.append("EXPERIMENT METADATA")
        lines.append(f"{'=' * 60}")
        for k in meta_fields:
            if k in sample:
                lines.append(f"  {k}: {sample[k]}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    lines.append("EXPERIMENT SUMMARY")
    lines.append(f"{'=' * 60}")
    lines.append(f"Directory: {experiment_dir}")
    lines.append(f"Total turns: {exp['total_turns']}")
    lines.append(f"Runs: {exp['n_runs']}  |  Questions: {exp['n_questions']}")
    lines.append(f"Parse rate: {exp['parse_rate']:.1%}")
    lines.append(f"Overall consistency: {exp['consistency_rate']:.1%}")
    for qt in ("CM", "PR", "DJ"):
        cr = exp[f"{qt}_consistency_rate"]
        pfr = exp[f"{qt}_parse_failure_rate"]
        cr_str = f"{cr:.1%}" if cr == cr else "N/A"
        lines.append(f"  {qt}: consistency={cr_str}  parse_failure={pfr:.1%}")

    lines.append(f"\n{'=' * 60}")
    lines.append("CONSISTENCY BY QUESTION TYPE")
    lines.append(f"{'=' * 60}")
    lines.append(evaluator.summary_by_question_type(df).to_string())

    lines.append(f"\n{'=' * 60}")
    lines.append("CONSISTENCY BY QUESTION")
    lines.append(f"{'=' * 60}")
    lines.append(evaluator.summary_by_question(df).to_string())

    lines.append(f"\n{'=' * 60}")
    lines.append("CONSISTENCY BY POSITION")
    lines.append(f"{'=' * 60}")
    lines.append(evaluator.summary_by_position(df).to_string())

    lines.append(f"\n{'=' * 60}")
    lines.append("CONSISTENCY BY RUN")
    lines.append(f"{'=' * 60}")
    lines.append(evaluator.summary_by_run(df).to_string())

    report = "\n".join(lines)
    print(report)

    # Save to experiment directory
    report_path = experiment_dir / "summary_stats.txt"
    report_path.write_text(report + "\n")
    print(f"\nSaved to {report_path}")


if __name__ == "__main__":
    main()
