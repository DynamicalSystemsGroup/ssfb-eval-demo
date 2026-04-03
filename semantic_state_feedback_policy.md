# Semantic State Feedback Policy

## The System

The LLM under test is treated as a **dynamical system with hidden state**. At each turn $t$:

- $x_t$ — hidden state of the LLM (session state, attention, whatever is internal — **unobservable**)
- $u_t \in \mathcal{U}$ — input prompt (text), the **control input**
- $y_t \in \mathcal{Y}$ — response (text), the **observable output**

The LLM implements some unknown map: given $u_t$ and hidden $x_t$, it produces $y_t$ and transitions to $x_{t+1}$. We never see $x_t$.

---

## The Trajectory

The trajectory is the sequence of observable input-output pairs:

$$h_t = [(u_0, y_0),\ (u_1, y_1),\ \ldots,\ (u_t, y_t)]$$

This grows monotonically. It is our **only window into the system's behavior**. It plays the role that a time series of measurements plays in system identification — it is what we have instead of direct state access.

---

## The Policy

The Policy is a map:

$$\pi_\omega : m_t \mapsto u_{t+1}$$

parameterized by $\omega$ — the ontology (world model). At each step it reads its memory $m_t$ and returns the next prompt. The loop is:

$$u_{t+1} = \pi_\omega(m_t), \quad m_{t+1} = \mathcal{M}(u_{t+1},\ y_{t+1},\ m_t)$$

starting from $m_{-1} = []$ and $u_0$ = first prompt (initial condition).

This is called **semantic state feedback** for three precise reasons:

1. **State feedback** — the policy operates on its **memory** $m_t \in M$, which is derived from the full history via the memory operator $\mathcal{M} : \mathcal{U} \times \mathcal{Y} \times M \to M$. The full history $h_t \in H$ — the **realization** — is maintained separately by the **logging** layer and is always preserved in full regardless of what the policy sees. In control theory, a realization is a specific trajectory produced by a particular initial condition and policy; here it means the full sequence of prompt-response pairs as they actually occurred, without omission. History is a logging concern. Memory is a policy concern. They are distinct even when they coincide.

2. **Semantic** — the state space $\mathcal{U}^* \times \mathcal{Y}^*$ is a space of text sequences, not a numeric vector space. Operations over it are semantic rather than algebraic.

3. **Feedback** — the policy's output at $t+1$ is causally conditioned on the system's output at $t$. It is a closed loop.

The ontology parameter $\omega$ does a specific job: it **grounds the semantic state space**. It provides a reference model of concepts, relations, and constraints against which the policy can interpret $m_t$ and decide what $u_{t+1}$ should probe.

---

## The Simplified Case: Memory as History

In this version we set $\mathcal{M} = \mathcal{A} = \text{concat}$, so $m_t = h_t$ — memory equals history, and the policy sees the full realization:

$$m_{t+1} = \mathcal{M}(u_{t+1},\ y_{t+1},\ m_t) = m_t \mathbin\| (u_{t+1},\ y_{t+1})$$

This is the discrete analogue of full-state integration, and it is a reasonable starting approximation: for conversations that fit within the LLM's context window, the model itself retains the full session history in its state. Setting $m_t = h_t$ mirrors that internal structure, making the policy's view of the conversation consistent with what the model under test is actually conditioning on.

The memory operator $\mathcal{M}$ is a **free parameter of the architecture** — in this version it is instantiated as concat, but any recursive update rule is a valid substitution. Sliding windows, summaries, attention-weighted filters, and memoryless operators that discard $m_t$ entirely are all instances of the same signature. The choice of $\mathcal{M}$ is independent of both the policy $\pi_\omega$ and the logging layer, and varying it produces a distinct family of semantic state feedback systems with different memory–performance tradeoffs. A broader theory of semantic state feedback will require memory operators where $M \subsetneq H$, but that generalization is deferred.

---

## Why This Is a Powerful Construction

By varying $\pi_\omega$ while holding the LLM fixed, you get a family of evaluation and red-teaming instruments from the same loop:

| Policy Design Intent | What $\pi_\omega$ Does | What You Learn |
|---|---|---|
| **Consistency probing** | Queries concepts from $\omega$, checks if $y_t$ respects their relations | Does the LLM maintain a coherent world model? |
| **Adversarial red-teaming** | Steers history toward ontological edge cases or constraint boundaries in $\omega$ | Where does the LLM's model break down? |
| **Scenario stress-testing** | Instantiates a specific scenario from $\omega$, escalates complexity over turns | How does behavior degrade as context complexity grows? |
| **Counterfactual probing** | Switches ontological grounding mid-trajectory | Does the LLM track context changes or persist stale beliefs? |
| **Coverage testing** | Enumerates concept subgraph of $\omega$, ensures each is touched | Are all ontologically relevant behaviors exercised? |

In every case, the ontology $\omega$ is doing double duty: it structures what the policy asks, and it grounds the evaluation criteria used to score what the model answers. **The reference model is the same object as the evaluation criterion** — which is the key property that makes this more principled than ad hoc red-teaming.

---

## The System Identification Analogy

In classical system identification you inject known inputs, measure outputs, and infer properties of the hidden system. This construction does the same thing in semantic space: $\pi_\omega$ is the **excitation signal designer**, $h_t$ is the **measurement record**, and the evaluation layer is the **estimator** that reads off what properties of the hidden $x$ are revealed by the trajectory. The ontology tells you what properties are worth estimating.

---

## Ontology Learning via Closed-Loop System Identification

The framework above treats $\omega$ as a **fixed** parameter — given, trusted, and held constant throughout the trajectory. But the system identification analogy suggests a natural inversion: rather than using a known ontology to probe the LLM, we can treat the ontology itself as an **unknown to be estimated** from observed trajectories.

The goal is to find $\omega^*$ such that an ontology-based model of the LLM's behavior best explains the observed input-output pairs. Formally, we seek:

$$\omega^* = \arg\min_{\omega \in \Omega} \mathcal{L}(h_T, \omega)$$

where $\mathcal{L}$ is a loss that measures the mismatch between what the ontology $\omega$ predicts the LLM should say and what it actually says. In the online setting, $\omega$ is updated incrementally at each turn rather than batch-estimated after the full trajectory is collected:

$$\omega_{t+1} = \omega_t + \Delta\omega(u_t,\ y_t,\ \omega_t)$$

This puts the ontology **in the loop** — $\omega_t$ is now a dynamical variable alongside $m_t$, and the full system state is the pair $(m_t, \omega_t)$. The policy $\pi_{\omega_t}$ now operates on an ontology that is itself evolving, closing a second feedback loop around the outer system.

This construction has a natural interpretation: the LLM's responses are treated as noisy observations of some latent conceptual structure, and the ontology learning procedure is an **estimator** that recovers that structure from the trajectory. Where classical system identification recovers differential equations or transfer functions, this procedure recovers ontological commitments — classes, relations, and constraints that best account for what the model says and does not say.

This is a longer-term direction. It requires specifying the ontology update rule $\Delta\omega$, a representation of $\Omega$ that supports incremental modification, and a loss $\mathcal{L}$ that is meaningful in semantic space. These are non-trivial. But the framing is important to establish now because it shows that the semantic state feedback construction is not only an evaluation instrument — it is a potential **knowledge acquisition** instrument, capable of building a world model of the LLM from interaction rather than requiring one to be supplied in advance.

This matters for a reason that goes beyond evaluation methodology. If the learned ontology $\omega^*$ is interpretable — expressed in a language of classes, relations, and constraints that humans can read — then this procedure produces an **explanation of LLM behavior**. Rather than treating the model as an irreducible black box, we obtain an estimate of the inner ontology that best accounts for what it says. That ontology is then subject to human inspection and judgment: its commitments can be examined, contested, and revised. This connects the dynamical systems framing to the broader project of AI interpretability, grounding it in a principled identification procedure rather than post-hoc rationalization.

---

## Formal Summary

| Symbol | Type | Role |
|---|---|---|
| $x_t$ | Hidden state | LLM internal state — unobservable |
| $u_t \in \mathcal{U}$ | Text | Control input (prompt) |
| $y_t \in \mathcal{Y}$ | Text | Observable output (response) |
| $h_t \in H$ | List of pairs | Full realization — complete trajectory, owned by logging |
| $\mathcal{A}$ | Accumulator | Logging implementation; maintains $h_t$ via concat |
| $m_t \in M$ | List of pairs | Policy memory — what the policy sees |
| $\mathcal{M} : \mathcal{U} \times \mathcal{Y} \times M \to M$ | Memory operator | Recursive update of policy memory; here $\mathcal{M} = \text{concat}$ |
| $\omega$ | Ontology | Policy parameter — world model / reference model |
| $\pi_\omega : M \to \mathcal{U}$ | Policy | Semantic state feedback policy |
| Exit criteria | Predicate on $h_t$ | Termination condition |
| Evaluation | Function of $h_T$ and $\omega$ | Grounded scoring — same object as reference model |
