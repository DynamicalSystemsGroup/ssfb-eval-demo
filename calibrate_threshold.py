#!/usr/bin/env python3
"""Calibration tool for tuning the similarity_threshold parameter.

Computes cosine similarity between ontology labels and candidate synonyms
using en_core_web_md vectors. Helps determine the threshold value that
accepts desired synonyms while rejecting unrelated terms.

Usage:
    # Run with built-in synonym pairs
    .venv/bin/python calibrate_threshold.py

    # Test custom pairs interactively
    .venv/bin/python calibrate_threshold.py --interactive

    # Sweep a threshold and show accept/reject for each pair
    .venv/bin/python calibrate_threshold.py --threshold 0.65

    # Add custom pairs via CLI
    .venv/bin/python calibrate_threshold.py --pairs "epidemic:outbreak" "pathogen:germ"
"""

import argparse
import sys

import spacy


# Built-in synonym pairs: (ontology_label, candidate_synonym)
# These are the pairs validated during Stage 3d development.
BUILTIN_PAIRS = [
    # High similarity (>= 0.9)
    ("epidemic", "outbreak"),
    ("vaccination", "immunization"),
    ("disease", "illness"),
    ("infection", "contagion"),
    # Medium similarity (0.65–0.9)
    ("pathogen", "microbe"),
    ("pathogen", "germ"),
    ("pathogenic disposition", "virulence"),
    ("infection in ecosystem", "contagion in environment"),
    ("infectious disease", "communicable illness"),
    ("drug treatment", "pharmaceutical therapy"),
    ("treatment", "therapy"),
    ("organism", "living thing"),
    ("disorder", "ailment"),
    ("host", "recipient"),
    ("ecosystem", "environment"),
    # Expected low similarity (should be rejected)
    ("epidemic", "weather"),
    ("pathogen", "furniture"),
    ("vaccination", "astronomy"),
]


def compute_similarity(nlp, label: str, synonym: str) -> dict:
    """Compute similarity between an ontology label and a candidate synonym.

    Uses the same logic as Question._similarity_fallback():
    - Single-word vs single-word: token-to-token cosine similarity
    - Multi-word: Doc-to-Doc similarity (averaged word vectors)
    """
    label_doc = nlp(label)
    synonym_doc = nlp(synonym)

    label_has_vector = label_doc.has_vector
    synonym_has_vector = synonym_doc.has_vector

    if not label_has_vector or not synonym_has_vector:
        return {
            "label": label,
            "synonym": synonym,
            "similarity": 0.0,
            "method": "no_vector",
            "label_has_vector": label_has_vector,
            "synonym_has_vector": synonym_has_vector,
        }

    sim = label_doc.similarity(synonym_doc)

    if len(label_doc) == 1 and len(synonym_doc) == 1:
        method = "token-token"
    else:
        method = "doc-doc"

    return {
        "label": label,
        "synonym": synonym,
        "similarity": round(sim, 4),
        "method": method,
        "label_has_vector": label_has_vector,
        "synonym_has_vector": synonym_has_vector,
    }


def print_results(results: list[dict], threshold: float | None = None):
    """Print similarity results as a formatted table."""
    # Column widths
    w_label = max(len(r["label"]) for r in results)
    w_syn = max(len(r["synonym"]) for r in results)
    w_label = max(w_label, 15)
    w_syn = max(w_syn, 15)

    # Header
    header = f"{'Ontology Label':<{w_label}}  {'Candidate':<{w_syn}}  {'Sim':>6}  {'Method':<12}"
    if threshold is not None:
        header += f"  {'Decision':<8}"
    print(header)
    print("-" * len(header))

    for r in results:
        line = (
            f"{r['label']:<{w_label}}  "
            f"{r['synonym']:<{w_syn}}  "
            f"{r['similarity']:>6.4f}  "
            f"{r['method']:<12}"
        )
        if threshold is not None:
            accepted = r["similarity"] >= threshold
            decision = "ACCEPT" if accepted else "reject"
            line += f"  {decision:<8}"

        if not r["label_has_vector"] or not r["synonym_has_vector"]:
            missing = []
            if not r["label_has_vector"]:
                missing.append("label")
            if not r["synonym_has_vector"]:
                missing.append("synonym")
            line += f"  (no vector: {', '.join(missing)})"

        print(line)


def sweep_thresholds(results: list[dict]):
    """Show how many pairs are accepted at various threshold levels."""
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
    total = len(results)

    print(f"\nThreshold sweep ({total} pairs):")
    print(f"{'Threshold':>10}  {'Accepted':>8}  {'Rejected':>8}  {'Accept %':>8}")
    print("-" * 42)
    for t in thresholds:
        accepted = sum(1 for r in results if r["similarity"] >= t)
        rejected = total - accepted
        pct = 100 * accepted / total if total > 0 else 0
        print(f"{t:>10.2f}  {accepted:>8}  {rejected:>8}  {pct:>7.1f}%")


def interactive_mode(nlp):
    """Interactive REPL for testing arbitrary pairs."""
    print("\nInteractive mode — enter pairs as 'label : synonym' (Ctrl-C to quit)")
    print("Example: epidemic : outbreak\n")
    while True:
        try:
            line = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not line:
            continue
        if ":" not in line:
            print("  Format: label : synonym")
            continue
        parts = line.split(":", 1)
        label = parts[0].strip()
        synonym = parts[1].strip()
        if not label or not synonym:
            print("  Both label and synonym must be non-empty")
            continue
        result = compute_similarity(nlp, label, synonym)
        print(f"  {result['similarity']:.4f}  ({result['method']})", end="")
        if not result["label_has_vector"] or not result["synonym_has_vector"]:
            print("  [missing vectors]", end="")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate the similarity_threshold for fuzzy ontology term matching."
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=None,
        help="Show accept/reject decisions at this threshold (e.g. 0.65)",
    )
    parser.add_argument(
        "--pairs", "-p", nargs="*", default=None,
        help='Custom pairs as "label:synonym" (e.g. "epidemic:outbreak")',
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Enter interactive mode to test arbitrary pairs",
    )
    parser.add_argument(
        "--sweep", "-s", action="store_true",
        help="Show acceptance counts across a range of thresholds",
    )
    args = parser.parse_args()

    print("Loading en_core_web_md...", end=" ", flush=True)
    nlp = spacy.load("en_core_web_md")
    print(f"done ({nlp.meta['vectors']['width']}D vectors, "
          f"{nlp.meta['vectors']['keys']} keys)")

    if args.interactive:
        interactive_mode(nlp)
        return

    # Build pair list
    pairs = list(BUILTIN_PAIRS)
    if args.pairs:
        for p in args.pairs:
            if ":" not in p:
                print(f"Skipping invalid pair (use label:synonym): {p}", file=sys.stderr)
                continue
            label, synonym = p.split(":", 1)
            pairs.append((label.strip(), synonym.strip()))

    # Compute similarities
    results = [compute_similarity(nlp, label, synonym) for label, synonym in pairs]
    results.sort(key=lambda r: r["similarity"], reverse=True)

    print()
    print_results(results, threshold=args.threshold)

    if args.sweep or args.threshold is None:
        sweep_thresholds(results)

    # Summary recommendation
    sims = [r["similarity"] for r in results if r["similarity"] > 0]
    if sims:
        print(f"\nRange: {min(sims):.4f} – {max(sims):.4f}")
        print(f"Current recommended threshold: 0.65")


if __name__ == "__main__":
    main()
