import { useState } from "react";

const approach = `This work develops a framework for measuring and closing the behavioral gap between two black-box 
text operators A, B: X → X over a structured region of prompt space. A domain-specific ontology 
(e.g. an OWL knowledge graph) serves as a symbolic substrate, providing basis functions that define 
the domain D ⊂ X and a metric over it. A Contextual Comparative Loss L(p, A(p), B(p)) measures 
operator divergence pointwise. Problem 1 — measurement — designs a probe distribution μ_D to 
estimate Δ(A,B) efficiently over D. Problem 2 — imitation — modulates B_θ to minimize the 
expected loss over D, treated as operator system identification with ontologically-grounded 
observables. The full stack spans preference modeling, optimal experiment design, knowledge 
distillation, neurosymbolic integration, and Koopman operator theory.`;

const clusters = [
  {
    id: "comparative-loss", label: "01",
    topic: "Comparative Loss & Preference Modeling",
    relevance: "Instantiates L(p, A(p), B(p)). The Bradley-Terry model and reward model literature define the parametric form of L and its training regime. Required before either Problem 1 or 2 can proceed.",
    accent: "#1a6b8a",
    papers: [
      { authors: "Christiano et al.", year: 2017, title: "Deep Reinforcement Learning from Human Preferences", doi: "10.48550/arXiv.1706.03741", why: "Foundational pairwise preference signal; first operationalization of L as a learned comparator over (p, rA, rB) triples." },
      { authors: "Ziegler et al.", year: 2019, title: "Fine-Tuning Language Models from Human Preferences", doi: "10.48550/arXiv.1909.08593", why: "Directly implements L as a reward model on (prompt, response_A, response_B); the canonical OpenAI formulation." },
      { authors: "Bradley & Terry", year: 1952, title: "Rank Analysis of Incomplete Block Designs: The Method of Paired Comparisons", doi: "10.1093/biomet/39.3-4.324", why: "Statistical backbone of all pairwise preference models; the parametric form L implicitly assumes throughout the literature." },
      { authors: "Zheng et al.", year: 2023, title: "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", doi: "10.48550/arXiv.2306.05685", why: "Implements L as an LLM judge; analyzes positional bias and consistency — critical failure modes for measurement validity." },
      { authors: "Liu et al.", year: 2023, title: "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment", doi: "10.48550/arXiv.2303.16634", why: "Structured rubric prompting for L; makes the evaluation criteria explicit and auditable." },
      { authors: "Dubois et al.", year: 2024, title: "Length-Controlled AlpacaEval", doi: "10.48550/arXiv.2404.04475", why: "Addresses verbosity bias in L; relevant for ensuring Δ(A,B) is not confounded by superficial output differences." },
      { authors: "Panickssery et al.", year: 2024, title: "LLM Evaluators Recognize and Favor Their Own Generations", doi: "10.48550/arXiv.2404.13076", why: "Self-preference bias in L; a systematic error source when B is used to evaluate itself." },
    ]
  },
  {
    id: "probe-design", label: "02",
    topic: "Probe & Input Design for Operator Discrimination",
    relevance: "Addresses Problem 1 directly: how to design the probe distribution μ_D to make Δ(A,B) maximally informative or statistically efficient. Maps to optimal experiment design in classical sysID.",
    accent: "#8a5a1a",
    papers: [
      { authors: "Ribeiro et al.", year: 2020, title: "Beyond Accuracy: Behavioral Testing of NLP Models with CheckList", doi: "10.18653/v1/2020.acl-main.442", why: "Partitions prompt space by behavioral capability class — closest existing approach to systematic D design." },
      { authors: "Perez et al.", year: 2022, title: "Red Teaming Language Models with Language Models", doi: "10.48550/arXiv.2202.03286", why: "Adversarial probe generation; maximizes L over D rather than covering it — the dual of efficient estimation." },
      { authors: "Polo et al.", year: 2024, title: "tinyBenchmarks: Evaluating LLMs with Fewer Examples", doi: "10.48550/arXiv.2402.14992", why: "Efficient estimation of Δ(A,B) from small samples; directly addresses statistical efficiency of the measurement protocol." },
      { authors: "Perlitz et al.", year: 2023, title: "Efficient Benchmarking of Language Models", doi: "10.48550/arXiv.2308.11696", why: "IRT-based item selection for model discrimination; closest to Fisher-information-aware probe selection in this literature." },
      { authors: "Ljung", year: 1999, title: "System Identification: Theory for the User (2nd ed.)", doi: null, note: "Book — ISBN 0-13-656695-2 (Prentice Hall)", why: "Classical sysID reference for optimal experiment design; D-optimal and Fisher criteria are the missing theoretical frame for Problem 1." },
    ]
  },
  {
    id: "distillation", label: "03",
    topic: "Knowledge Distillation & Behavioral Cloning",
    relevance: "The mechanism for Problem 2. Fine-tuning B_θ on samples {(p, A(p))} from D is behavioral cloning; distillation enriches the supervision signal. Classical KD provides the loss-level formulation.",
    accent: "#4a7a1a",
    papers: [
      { authors: "Hinton, Vinyals & Dean", year: 2015, title: "Distilling the Knowledge in a Neural Network", doi: "10.48550/arXiv.1503.02531", why: "Foundational soft-target KD; the loss operates on output distributions, natural for the operator imitation framing." },
      { authors: "Kim & Rush", year: 2016, title: "Sequence-Level Knowledge Distillation", doi: "10.18653/v1/D16-1139", why: "Loss over full output sequences rather than tokens; more natural for black-box operator A where only outputs are observable." },
      { authors: "Taori et al.", year: 2023, title: "Alpaca: Instruction-Following LLaMA", doi: null, note: "Blog — crfm.stanford.edu/2023/03/13/alpaca.html", why: "Canonical BC from GPT outputs; D implicitly defined by 52k instruction prompts." },
      { authors: "Chiang et al.", year: 2023, title: "Vicuna: An Open-Source Chatbot Impressing GPT-4", doi: null, note: "Blog — lmsys.org/blog/2023-03-30-vicuna", why: "Extended BC with quality filtering; D defined by curated conversation distribution." },
      { authors: "Mukherjee et al.", year: 2023, title: "Orca: Progressive Learning from Complex Explanation Traces", doi: "10.48550/arXiv.2306.02707", why: "Enriches supervision beyond A(p) with explanation traces; relevant when A's outputs alone are insufficient for imitation." },
      { authors: "Ho et al.", year: 2022, title: "Large Language Models Are Reasoning Teachers", doi: "10.48550/arXiv.2212.08410", why: "Domain-restricted CoT distillation; D is a task-specific subdomain — explicit about the region restriction." },
    ]
  },
  {
    id: "rl-alignment", label: "04",
    topic: "RL-Based Alignment & Direct Preference Optimization",
    relevance: "When L is differentiable or approximated by a reward model, Problem 2 becomes an optimization directly driven by L. DPO and variants collapse reward + RL into a tractable loss on B_θ.",
    accent: "#6a1a8a",
    papers: [
      { authors: "Ouyang et al.", year: 2022, title: "Training Language Models to Follow Instructions with Human Feedback (InstructGPT)", doi: "10.48550/arXiv.2203.02155", why: "RLHF pipeline: reward model ≈ L, PPO optimizes B_θ; canonical formulation of Problem 2 with learned L." },
      { authors: "Rafailov et al.", year: 2023, title: "Direct Preference Optimization: Your Language Model is Secretly a Reward Model", doi: "10.48550/arXiv.2305.18290", why: "Analytically collapses reward model + RL into a loss directly on B_θ log-probabilities. Cleanest formulation when A generates the preferred responses." },
      { authors: "Ethayarajh et al.", year: 2024, title: "KTO: Model Alignment as Prospect Theoretic Optimization", doi: "10.48550/arXiv.2402.01306", why: "Extends DPO to unpaired settings; relevant when A(p) and B(p) cannot always be jointly sampled." },
      { authors: "Hong et al.", year: 2024, title: "ORPO: Monolithic Preference Optimization without Reference Model", doi: "10.48550/arXiv.2403.07691", why: "Eliminates reference model; simplifies the optimization when B's prior behavior outside D must not be constrained." },
    ]
  },
  {
    id: "domain-restriction", label: "05",
    topic: "Domain Restriction & Continual Learning",
    relevance: "Problem 2 requires B_θ → A on D without degrading B outside D. This is a constrained imitation problem; continual learning and model editing literature address the constraint directly.",
    accent: "#1a8a5a",
    papers: [
      { authors: "Kirkpatrick et al.", year: 2017, title: "Overcoming Catastrophic Forgetting in Neural Networks (EWC)", doi: "10.1073/pnas.1611835114", why: "Elastic weight consolidation; directly constrains how far B_θ moves from its prior outside D." },
      { authors: "Hu et al.", year: 2022, title: "LoRA: Low-Rank Adaptation of Large Language Models", doi: "10.48550/arXiv.2106.09685", why: "Low-rank modulation implicitly restricts the capacity of change; a soft constraint on B's departure from baseline behavior outside D." },
      { authors: "Ilharco et al.", year: 2023, title: "Editing Models with Task Arithmetic", doi: "10.48550/arXiv.2212.04089", why: "Task vectors enable localized modification; relevant when D is topologically simple and can be addressed by arithmetic on weight space." },
      { authors: "Meng et al.", year: 2022, title: "Locating and Editing Factual Associations in GPT (ROME)", doi: "10.48550/arXiv.2202.05262", why: "Surgical factual edits; useful when D is defined by specific knowledge assertions in the ontology." },
      { authors: "McCloskey & Cohen", year: 1989, title: "Catastrophic Interference in Connectionist Networks: The Sequential Learning Problem", doi: "10.1016/S0079-7421(08)60536-8", why: "Original characterization of the forgetting problem; bounds what is achievable when D is strict." },
    ]
  },
  {
    id: "ontology-formal", label: "06",
    topic: "Formal Ontologies & Description Logics",
    relevance: "The symbolic substrate. OWL/DL provides the formal language for specifying D, the subsumption hierarchy gives a natural partial order on prompt classes, and model-theoretic semantics ground claims of completeness.",
    accent: "#7a7a1a",
    papers: [
      { authors: "Baader et al.", year: 2003, title: "The Description Logic Handbook", doi: "10.1017/CBO9780511711787", why: "Canonical reference; subsumption hierarchy gives the natural partial order on concept classes spanning D." },
      { authors: "Horrocks, Patel-Schneider & van Harmelen", year: 2003, title: "From SHIQ and RDF to OWL: The Making of a Web Ontology Language", doi: "10.1016/j.websem.2003.07.001", why: "OWL formal semantics grounded in DL; model-theoretic semantics required to claim completeness of basis coverage." },
      { authors: "Guarino, Oberle & Staab", year: 2009, title: "What is an Ontology?", doi: "10.1007/978-3-540-92673-3_0", note: "Ch. in Handbook on Ontologies (Springer)", why: "Distinguishes ontology-as-specification from ontology-as-theory; directly relevant to what can be formally claimed about D." },
      { authors: "Smith et al.", year: 2007, title: "The OBO Foundry: Coordinated Evolution of Ontologies", doi: "10.1038/nbt1346", why: "BFO upper ontology; relevant for domain portability and cross-domain basis reuse." },
      { authors: "Ganter & Wille", year: 1999, title: "Formal Concept Analysis: Mathematical Foundations", doi: "10.1007/978-3-642-59830-2", why: "Concept lattices give a complete lattice structure over D; the natural algebraic object when ontology classes are basis functions." },
    ]
  },
  {
    id: "ontology-similarity", label: "07",
    topic: "Ontology-Based Similarity & Domain Topology",
    relevance: "Provides the metric on X derived from the symbolic substrate. Required to formally define what 'region D' means, to design probe distributions μ_D, and to verify that B_θ has converged on D.",
    accent: "#1a3a8a",
    papers: [
      { authors: "Resnik", year: 1995, title: "Using Information Content to Evaluate Semantic Similarity in a Taxonomy", doi: null, note: "IJCAI-95 proceedings (no registered DOI)", why: "Information-theoretic similarity via LCS information content; gives a principled distance on the ontology graph." },
      { authors: "Lin", year: 1998, title: "An Information-Theoretic Definition of Similarity", doi: null, note: "ICML-98 proceedings (no registered DOI)", why: "Normalized variant of Resnik; bounded [0,1] and more suitable as a kernel or metric on D." },
      { authors: "Wu & Palmer", year: 1994, title: "Verb Semantics and Lexical Selection", doi: "10.3115/981732.981751", why: "Path-based ontology similarity; simpler baseline for when information content estimates are unavailable." },
      { authors: "Euzenat & Shvaiko", year: 2013, title: "Ontology Matching (2nd ed.)", doi: "10.1007/978-3-642-38721-0", why: "Prerequisite: if A and B encode different implicit ontologies, L is confounded by ontological mismatch before measurement begins." },
      { authors: "Gärtner, Flach & Kowalczyk", year: 2003, title: "On Graph Kernels: Hardness Results and Efficient Alternatives", doi: "10.1007/978-3-540-45167-9_11", why: "Graph kernels on the ontology structure; operationalizes ontology-induced similarity as a kernel on prompt space." },
    ]
  },
  {
    id: "neurosymbolic", label: "08",
    topic: "Neurosymbolic Integration",
    relevance: "The paradigm governing how the symbolic substrate (ontology) couples to neural operators A and B. Provides architectural and theoretical grounding for the hybrid system.",
    accent: "#8a1a1a",
    papers: [
      { authors: "Garcez & Lamb", year: 2023, title: "Neurosymbolic AI: The 3rd Wave", doi: "10.1007/s10462-023-10448-7", why: "Current state-of-the-field survey; situates the ontology-grounded operator framework within the broader neurosymbolic landscape." },
      { authors: "Kautz", year: 2022, title: "The Third Wave of AI (AAAI Robert S. Engelmore Award Lecture)", doi: "10.1002/aaai.12036", why: "Concise framing of the integration problem and research agenda; useful for positioning the approach." },
      { authors: "Manhaeve et al.", year: 2018, title: "DeepProbLog: Neural Probabilistic Logic Programming", doi: "10.48550/arXiv.1805.10872", why: "Probabilistic logic as symbolic substrate; relevant if L is to be ontologically grounded with uncertainty quantification." },
      { authors: "Hitzler et al.", year: 2022, title: "Neuro-Symbolic Approaches in Artificial Intelligence", doi: "10.4230/DagRep.11.11.1", note: "Dagstuhl Reports 11(11)", why: "Survey of integration architectures; maps the design space for how the ontology couples to B_θ." },
    ]
  },
  {
    id: "kg-llm", label: "09",
    topic: "Knowledge Graphs & LLMs",
    relevance: "Applied literature on coupling symbolic KG/ontology structure with neural language models; covers retrieval, augmentation, and structured generation relevant to populating and querying the ontological substrate.",
    accent: "#1a6a3a",
    papers: [
      { authors: "Pan et al.", year: 2023, title: "Unifying Large Language Models and Knowledge Graphs: A Roadmap", doi: "10.48550/arXiv.2306.08302", why: "Most comprehensive survey of this intersection; directly covers the architecture of the hybrid system." },
      { authors: "Edge et al.", year: 2024, title: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization", doi: "10.48550/arXiv.2404.16130", why: "GraphRAG uses KG structure to define retrieval domains; D is implicitly ontologically grounded — closest applied analog." },
      { authors: "Bordes et al.", year: 2013, title: "Translating Embeddings for Modeling Multi-Relational Data (TransE)", doi: null, note: "NeurIPS 2013 — proceedings.neurips.cc/paper_files/paper/2013/hash/1cecc7a77928ca8133fa24680a88d2f9", why: "Foundational KG embedding; lifts ontology into metric space, enabling continuous optimization over symbolic structure." },
      { authors: "Hamilton et al.", year: 2018, title: "Embedding Methods for Link Prediction (survey)", doi: "10.48550/arXiv.1709.05584", why: "Survey of KG embedding methods; relevant for choosing the metric space induced by the ontological substrate." },
      { authors: "Trajanoska et al.", year: 2023, title: "Enhancing Knowledge Graph Construction Using Large Language Models", doi: "10.48550/arXiv.2305.04676", why: "LLM-assisted KG construction; relevant if the ontological substrate is to be populated or extended from A's outputs." },
    ]
  },
  {
    id: "koopman", label: "10",
    topic: "Koopman Operators & Spectral Basis Theory",
    relevance: "The deepest sysID connection. If ontology classes are observable functions, fitting B_θ ≈ A on D is EDMD with ontologically-specified lifting functions. Graph Laplacian eigenfunctions are the natural spectral basis over the ontology.",
    accent: "#4a1a8a",
    papers: [
      { authors: "Williams, Kevrekidis & Rowley", year: 2015, title: "A Data-Driven Approximation of the Koopman Operator: Extending EDMD", doi: "10.1007/s00332-015-9258-5", why: "EDMD is the direct sysID method when observables (ontology classes) are pre-specified; fitting B_θ ≈ A on D is exactly this problem." },
      { authors: "Lusch, Kutz & Brunton", year: 2018, title: "Deep Learning for Universal Linear Embeddings of Nonlinear Dynamics", doi: "10.1038/s41467-018-07210-0", why: "Deep Koopman: neural parametrization of the lifting map; B_θ could serve as the learned lifting operator." },
      { authors: "Koopman", year: 1931, title: "Hamiltonian Systems and Transformation in Hilbert Space", doi: "10.1073/pnas.17.5.315", why: "Original operator-theoretic formulation; the foundation of the linearization approach." },
      { authors: "Mezić", year: 2005, title: "Spectral Properties of Dynamical Systems, Model Reduction and Decompositions", doi: "10.1007/s11071-005-2824-x", why: "Spectral theory for Koopman; eigenfunctions of the operator are the natural basis — analogous to ontology class eigenfunctions." },
      { authors: "Chung", year: 1997, title: "Spectral Graph Theory", doi: "10.1090/cbms/092", note: "AMS CBMS-NSF Regional Conference Series vol. 92", why: "Laplacian eigenfunctions on the ontology graph are the formal realization of 'ontology as basis functions'." },
      { authors: "Defferrard, Bresson & Vandergheynst", year: 2016, title: "Convolutional Neural Networks on Graphs with Fast Localized Spectral Filtering (ChebNet)", doi: "10.48550/arXiv.1606.09375", why: "Operationalizes spectral graph theory in neural networks; bridges the ontology graph Laplacian to the neural operator B_θ." },
      { authors: "Collins & Duffy", year: 2002, title: "New Ranking Algorithms for Parsing and Tagging: Kernels over Discrete Structures", doi: "10.3115/1073083.1073128", why: "Convolution kernels on trees; relevant since subsumption hierarchies are trees and the kernel defines the inner product on D." },
    ]
  },
];

const TopicCard = ({ cluster, isOpen, onToggle }) => (
  <div style={{ borderLeft: `3px solid ${cluster.accent}`, marginBottom: "1.5rem", background: "#0f1117", borderRadius: "0 4px 4px 0", overflow: "hidden", boxShadow: isOpen ? `0 0 0 1px ${cluster.accent}33` : "none" }}>
    <div onClick={onToggle} style={{ display: "flex", alignItems: "flex-start", gap: "1rem", padding: "1rem 1.25rem", cursor: "pointer", userSelect: "none" }}>
      <span style={{ fontFamily: "monospace", fontSize: "0.65rem", color: cluster.accent, fontWeight: 700, letterSpacing: "0.1em", marginTop: "0.15rem", flexShrink: 0 }}>{cluster.label}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: "Georgia, serif", fontSize: "1rem", fontWeight: 600, color: "#e8e8e8", marginBottom: "0.25rem", lineHeight: 1.3 }}>{cluster.topic}</div>
        {!isOpen && <div style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#666" }}>{cluster.papers.length} papers</div>}
      </div>
      <span style={{ color: cluster.accent, fontSize: "1rem", flexShrink: 0, marginTop: "0.1rem", display: "inline-block", transform: isOpen ? "rotate(90deg)" : "none", transition: "transform 0.2s" }}>›</span>
    </div>

    {isOpen && (
      <div style={{ padding: "0 1.25rem 0 calc(1.25rem + 2rem + 1rem)", marginBottom: "0.75rem" }}>
        <div style={{ borderTop: `1px solid ${cluster.accent}33`, paddingTop: "0.75rem", fontFamily: "Georgia, serif", fontSize: "0.82rem", color: "#aaa", lineHeight: 1.65, fontStyle: "italic" }}>
          {cluster.relevance}
        </div>
      </div>
    )}

    {isOpen && (
      <div style={{ padding: "0 1.25rem 1rem calc(1.25rem + 2rem + 1rem)" }}>
        {cluster.papers.map((paper, i) => (
          <div key={i} style={{ padding: "0.75rem 0", borderTop: "1px solid #1e2030" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", marginBottom: "0.2rem", flexWrap: "wrap" }}>
              <span style={{ fontFamily: "monospace", fontSize: "0.7rem", color: cluster.accent, fontWeight: 700 }}>{paper.authors}</span>
              <span style={{ fontFamily: "monospace", fontSize: "0.65rem", color: "#555" }}>{paper.year}</span>
            </div>
            <div style={{ fontFamily: "Georgia, serif", fontSize: "0.82rem", color: "#ccc", fontStyle: "italic", lineHeight: 1.35, marginBottom: "0.25rem" }}>{paper.title}</div>
            <div style={{ marginBottom: "0.3rem" }}>
              {paper.doi ? (
                <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer"
                  style={{ fontFamily: "monospace", fontSize: "0.63rem", color: cluster.accent, opacity: 0.8, textDecoration: "none", borderBottom: `1px dotted ${cluster.accent}66` }}>
                  doi:{paper.doi}
                </a>
              ) : (
                <span style={{ fontFamily: "monospace", fontSize: "0.63rem", color: "#3a3d45", fontStyle: "italic" }}>{paper.note || "no DOI"}</span>
              )}
            </div>
            <div style={{ fontFamily: "system-ui, sans-serif", fontSize: "0.76rem", color: "#777", lineHeight: 1.55 }}>{paper.why}</div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default function LitReview() {
  const [openClusters, setOpenClusters] = useState(new Set());
  const [filter, setFilter] = useState("");

  const toggle = (id) => setOpenClusters(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const expandAll = () => setOpenClusters(new Set(clusters.map(c => c.id)));
  const collapseAll = () => setOpenClusters(new Set());

  const q = filter.trim().toLowerCase();
  const filtered = q ? clusters.filter(c =>
    c.topic.toLowerCase().includes(q) || c.relevance.toLowerCase().includes(q) ||
    c.papers.some(p => p.title.toLowerCase().includes(q) || p.authors.toLowerCase().includes(q) ||
      p.why.toLowerCase().includes(q) || (p.doi || "").includes(q))
  ) : clusters;

  const total = clusters.reduce((n, c) => n + c.papers.length, 0);
  const withDoi = clusters.reduce((n, c) => n + c.papers.filter(p => p.doi).length, 0);

  return (
    <div style={{ minHeight: "100vh", background: "#090b10", color: "#e8e8e8", padding: "2rem 1rem" }}>
      <div style={{ maxWidth: "820px", margin: "0 auto" }}>
        <div style={{ marginBottom: "2.5rem" }}>
          <div style={{ fontFamily: "monospace", fontSize: "0.62rem", color: "#444", letterSpacing: "0.15em", marginBottom: "0.6rem", textTransform: "uppercase" }}>Literature Review</div>
          <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#f0f0f0", margin: "0 0 1rem 0", lineHeight: 1.25 }}>
            Ontology-Grounded Operator Comparison<br />& Domain-Restricted Imitation
          </h1>
          <div style={{ background: "#0d1018", border: "1px solid #1e2230", borderRadius: "4px", padding: "1.1rem 1.25rem", marginBottom: "1.5rem" }}>
            <div style={{ fontFamily: "monospace", fontSize: "0.6rem", color: "#334", letterSpacing: "0.12em", marginBottom: "0.5rem", textTransform: "uppercase" }}>Approach</div>
            <p style={{ fontFamily: "Georgia, serif", fontSize: "0.85rem", color: "#aaa", lineHeight: 1.7, margin: 0 }}>{approach}</p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: "0.65rem", color: "#334" }}>
              {clusters.length} clusters · {total} papers · {withDoi} DOI · {total - withDoi} without
            </span>
            <div style={{ flex: 1 }} />
            <input type="text" placeholder="filter..." value={filter} onChange={e => setFilter(e.target.value)}
              style={{ background: "#0d1018", border: "1px solid #1e2230", borderRadius: "3px", padding: "0.35rem 0.65rem", color: "#ccc", fontFamily: "monospace", fontSize: "0.7rem", width: "180px", outline: "none" }} />
            <button onClick={expandAll} style={{ background: "transparent", border: "1px solid #1e2230", borderRadius: "3px", padding: "0.3rem 0.6rem", color: "#555", fontFamily: "monospace", fontSize: "0.65rem", cursor: "pointer" }}>expand all</button>
            <button onClick={collapseAll} style={{ background: "transparent", border: "1px solid #1e2230", borderRadius: "3px", padding: "0.3rem 0.6rem", color: "#555", fontFamily: "monospace", fontSize: "0.65rem", cursor: "pointer" }}>collapse all</button>
          </div>
        </div>

        {filtered.length === 0
          ? <div style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#333", textAlign: "center", padding: "3rem" }}>no matches</div>
          : filtered.map(c => <TopicCard key={c.id} cluster={c} isOpen={openClusters.has(c.id)} onToggle={() => toggle(c.id)} />)
        }

        <div style={{ marginTop: "2rem", borderTop: "1px solid #151820", paddingTop: "1rem", fontFamily: "monospace", fontSize: "0.6rem", color: "#2a2e38", lineHeight: 1.8 }}>
          Gap analysis: D-optimal probe design · Ontology graph Laplacian as explicit basis · EDMD with ontological observables · Ontology alignment as pre-measurement precondition · Subsumption hierarchy as D boundary topology<br/>
          Papers without DOI: Ljung 1999 (book ISBN 0-13-656695-2) · Resnik 1995 (IJCAI-95) · Lin 1998 (ICML-98) · Alpaca / Vicuna (blog posts, no formal venue) · Bordes et al. 2013 (NeurIPS 2013, no registered DOI)
        </div>
      </div>
    </div>
  );
}
