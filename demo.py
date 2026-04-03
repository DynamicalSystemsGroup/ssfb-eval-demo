#!/usr/bin/env python3
"""End-to-end SSFB evaluation demo.

Loads the APOLLO-SV ontology, builds the question bank, runs N independent
trajectory runs against a local Ollama instance, and prints evaluation summaries.

Usage:
    .venv/bin/python demo.py --runs 5
    .venv/bin/python demo.py --runs 10 --output-dir ./my_trajectories --seed 42
"""

import argparse
import os

from apollo_eval.ontology_loader import OntologyLoader
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import Question
from apollo_eval.question_loader import build_question_bank
from apollo_eval.model_client import OllamaClient
from apollo_eval.policy import PolicyEngine
from apollo_eval.evaluation import EvaluationLayer

SCENARIO_IRI = "http://example.org/scenario/measles_epidemic/"


def main():
    parser = argparse.ArgumentParser(description="SSFB Evaluation Demo")
    parser.add_argument("--runs", type=int, default=5,
                        help="Number of independent trajectory runs (default: 5)")
    parser.add_argument("--output-dir", type=str, default="trajectories",
                        help="Directory for trajectory JSON output (default: trajectories)")
    parser.add_argument("--owl-path", type=str, default=None,
                        help="Path or URL to OWL ontology file (default: OBO PURL)")
    parser.add_argument("--similarity-threshold", type=float, default=1.0,
                        help="Similarity threshold for fuzzy matching (default: 1.0 = exact only)")
    parser.add_argument("--seed", type=int, default=0,
                        help="Base random seed; each run uses seed+i (default: 0)")
    parser.add_argument("--model", type=str, default=None,
                        help="Ollama model name (default: OLLAMA_MODEL or llama3.2:1b)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each question and response as it happens")
    args = parser.parse_args()

    # 1. Load ontology → reason → build vocabulary
    print("Loading ontology...", end=" ", flush=True)
    loader = OntologyLoader(args.owl_path) if args.owl_path else OntologyLoader()
    graph = loader.load_graph()
    graph = loader.apply_reasoning(graph)
    ontology = OntologyVocabularyBuilder(graph).build(
        similarity_threshold=args.similarity_threshold,
    )
    print("done.")

    # 2. Set class-level ontology
    Question.ontology = ontology

    # 3. Build question bank
    print("Building question bank...", end=" ", flush=True)
    questions = build_question_bank(ontology)
    print(f"{len(questions)} questions ready.")

    # 4. Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # 5. Run N trajectories
    def print_turn(turn):
        score_str = f"{turn['score']:.1f}" if turn["parse_success"] else "N/A"
        print(f"\n    [{turn['position_index'] + 1}] Q: {turn['u']}")
        print(f"        A: {turn['y'][:200]}{'...' if len(turn['y']) > 200 else ''}")
        print(f"        parse={turn['parse_success']}  score={score_str}")

    print(f"\nRunning {args.runs} trajectory run(s)...")
    for i in range(args.runs):
        client = OllamaClient(model=args.model)  # fresh per run
        engine = PolicyEngine(
            questions=questions,
            client=client,
            seed=args.seed + i,
            scenario_iri=SCENARIO_IRI,
            on_turn=print_turn if args.verbose else None,
        )
        if args.verbose:
            print(f"\n--- Run {i + 1}/{args.runs} (seed={args.seed + i}) ---")
        engine.run()
        path = engine.save(args.output_dir)
        print(f"  Run {i + 1}/{args.runs}: {engine.run_id} → {path}")

    # 6. Evaluate
    print("\nScoring trajectories...")
    evaluator = EvaluationLayer(args.output_dir, questions)
    df = evaluator.build_dataframe()

    # 7. Print summaries
    print(f"\n{'=' * 60}")
    print("CONSISTENCY RATE BY QUESTION")
    print('=' * 60)
    print(evaluator.summary_by_question(df).to_string())

    print(f"\n{'=' * 60}")
    print("CONSISTENCY RATE BY POSITION")
    print('=' * 60)
    print(evaluator.summary_by_position(df).to_string())

    print(f"\n{'=' * 60}")
    print("CONSISTENCY RATE BY RUN")
    print('=' * 60)
    print(evaluator.summary_by_run(df).to_string())

    # Overall stats
    n_turns = len(df)
    n_parsed = df["parse_success"].sum()
    n_consistent = (df["score"] == 1.0).sum()
    print(f"\n{'=' * 60}")
    print(f"Total turns: {n_turns}")
    print(f"Parse success: {n_parsed}/{n_turns} ({100 * n_parsed / n_turns:.1f}%)")
    if n_parsed > 0:
        print(f"Consistency (of parsed): {n_consistent}/{n_parsed} ({100 * n_consistent / n_parsed:.1f}%)")


if __name__ == "__main__":
    main()
