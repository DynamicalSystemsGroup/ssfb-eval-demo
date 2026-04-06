#!/usr/bin/env python3
"""Operator comparison demo: Model A (LLM) vs Model B (OWL belief graph).

Probes both operators with the same ontology-grounded questions, measures
divergence via L(x, A(x), B(x)), and optionally updates B's belief graph
to imitate A (online learning / system identification).

Usage:
    .venv/bin/python compare_demo.py --epochs 3 --verbose
    .venv/bin/python compare_demo.py --epochs 5 --imitation --sparse --verbose
"""

import argparse
import os

from apollo_eval.ontology_loader import OntologyLoader
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import Question
from apollo_eval.question_loader import build_question_bank
from apollo_eval.model_client import OllamaClient
from apollo_eval.ontology_client import OntologyClient
from apollo_eval.comparison_engine import ComparisonEngine
from apollo_eval.divergence import ProbeResult

SCENARIO_IRI = "http://example.org/scenario/measles_epidemic/"


def main():
    parser = argparse.ArgumentParser(
        description="Operator Comparison: LLM (A) vs OWL Belief Graph (B)"
    )
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of epochs to probe (default: 3)")
    parser.add_argument("--output-dir", type=str, default="trajectories/comparison",
                        help="Directory for trajectory JSON output")
    parser.add_argument("--owl-path", type=str, default=None,
                        help="Path or URL to OWL ontology file (default: OBO PURL)")
    parser.add_argument("--similarity-threshold", type=float, default=1.0,
                        help="Similarity threshold for fuzzy matching (default: 1.0)")
    parser.add_argument("--seed", type=int, default=0,
                        help="Random seed for probe ordering (default: 0)")
    parser.add_argument("--model", type=str, default=None,
                        help="Ollama model name for operator A")
    parser.add_argument("--imitation", action="store_true",
                        help="Enable online imitation: B learns from A's responses")
    parser.add_argument("--sparse", action="store_true",
                        help="Start B with sparse beliefs: TBox + direct types only, "
                             "no property assertions or entailed types")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each probe result as it happens")
    args = parser.parse_args()

    # 1. Load ontology
    print("Loading ontology...", end=" ", flush=True)
    loader = OntologyLoader(args.owl_path) if args.owl_path else OntologyLoader()
    graph = loader.load_graph()
    graph = loader.apply_reasoning(graph)
    ontology = OntologyVocabularyBuilder(graph).build(
        similarity_threshold=args.similarity_threshold,
    )
    print("done.")

    # 2. Set class-level ontology and build question bank
    Question.ontology = ontology
    print("Building question bank...", end=" ", flush=True)
    questions = build_question_bank(ontology)
    print(f"{len(questions)} questions ready.")

    # 3. Create operators
    client_a = OllamaClient(model=args.model)
    client_b = OntologyClient(ontology, questions, sparse=args.sparse)

    b_mode = "sparse (TBox + direct types)" if args.sparse else "full (ground truth copy)"
    print(f"\nOperator A: {client_a.model} (LLM)")
    print(f"Operator B: OWL belief graph ({b_mode})")
    print(f"Epochs: {args.epochs}  |  Imitation: {args.imitation}")
    print(f"Seed: {args.seed}")

    # 4. Verbose callback
    def print_probe(probe: ProbeResult):
        a_str = f"{probe.a_score.score:.0f}" if probe.a_score.parse_success else "N/A"
        b_str = f"{probe.b_score.score:.0f}" if probe.b_score.parse_success else "N/A"
        div = "DIVERGENT" if probe.divergent else "aligned"
        upd = " [belief updated]" if probe.belief_update else ""
        print(f"  [{probe.epoch}:{probe.probe_index:02d}] "
              f"A={a_str} B={b_str} {div}{upd}  {probe.question_id[:8]}...")
        if args.verbose:
            print(f"         A: {probe.a_response[:120]}{'...' if len(probe.a_response) > 120 else ''}")
            print(f"         B: {probe.b_response[:120]}{'...' if len(probe.b_response) > 120 else ''}")

    # 5. Run comparison
    os.makedirs(args.output_dir, exist_ok=True)

    engine = ComparisonEngine(
        questions=questions,
        client_a=client_a,
        client_b=client_b,
        n_epochs=args.epochs,
        seed=args.seed,
        scenario_iri=SCENARIO_IRI,
        imitation=args.imitation,
        on_probe=print_probe if args.verbose else None,
        metadata={
            "model_a": client_a.model,
            "model_b": "owl_belief_graph",
            "model_b_mode": "sparse" if args.sparse else "full",
            "ontology_source": loader.owl_path,
            "similarity_threshold": args.similarity_threshold,
        },
    )

    print(f"\nRunning {args.epochs} epoch(s)...")
    trajectory = engine.run()
    path = engine.save(args.output_dir)
    print(f"\nTrajectory saved: {path}")

    # 6. Print summaries
    s = trajectory.summary()

    print(f"\n{'=' * 60}")
    print("COMPARISON SUMMARY")
    print('=' * 60)
    print(f"Total probes: {s['total_probes']}")
    print(f"Epochs: {s['n_epochs']}  |  Questions: {s['n_questions']}")
    print(f"A parse rate: {s['a_parse_rate']:.1%}")
    print(f"B parse rate: {s['b_parse_rate']:.1%}")
    print(f"A consistency (vs ground truth): {s['a_consistency_rate']:.1%}")
    print(f"B consistency (vs ground truth): {s['b_consistency_rate']:.1%}")
    print(f"Overall divergence rate: {s['overall_divergence_rate']:.1%}")
    if args.imitation:
        print(f"Total belief updates: {s['total_belief_updates']}")

    print(f"\n{'=' * 60}")
    print("DIVERGENCE BY EPOCH (convergence curve)")
    print('=' * 60)
    print(trajectory.divergence_by_epoch().to_string())

    print(f"\n{'=' * 60}")
    print("DIVERGENCE BY QUESTION TYPE")
    print('=' * 60)
    print(trajectory.divergence_by_type().to_string())

    print(f"\n{'=' * 60}")
    print("DIVERGENCE BY QUESTION")
    print('=' * 60)
    print(trajectory.divergence_by_question().to_string())


if __name__ == "__main__":
    main()
