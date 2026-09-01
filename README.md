# Persona-Execution Separation (PES)

An architecture pattern for evolving LLM agents under execution audit.

**Paper:** [arXiv:2608.27427](https://arxiv.org/abs/2608.27427) (cs.SE)

---

## The idea

An LLM agent's operational identity (persona — where it is seen, talked to,
and edited) and its governed execution (where it acts, and is audited) live
in different trust domains, connected by a governed contract bridge. The
persona is singly-homed and may drift freely; execution is faceless and
audited. Status summaries may flow back; data bodies stay in the restrictive
domain except a graded DLP exception; identity stays continuous.

Under LLM representational indistinguishability, any single-domain mechanism
that meets the three goals (free persona drift, execution traceability,
decoupling) has to re-introduce typed change objects, an external gate, and
a stable audit anchor — PES rebuilt at higher coupling cost.

PES pays off when multi-user deployment, execution audit, and expected
persona churn hold jointly (Section 4.7 of the paper). Single-user or
no-audit settings do not need it.

## Run the demo

```bash
python pes_demo.py
```

A zero-dependency, no-LLM illustration of the mechanism:

| Step | What it shows | Paper |
|---|---|---|
| 1 | Baseline governed SOP run | — |
| 2 | Persona drifts (instructions + tone) → execution unchanged | V1: R = 0 |
| 3 | Sensitive body blocked by DLP | §4.4 |
| 4 | SOP definition change → execution changes | Probe P2 |
| 5 | Unauthorized user denied by approval matrix | §4.4 |

Concept illustration, not the reference implementation.

## Validation (paper §7)

- **Mechanism check:** no execution-side re-validation under persona
  perturbation (R = 0/5) across five model configurations.
- **Trace isolation:** fixed-input A/B around an L3 persona change — state
  path, tool set, structural parameters, approval chain identical.
- **Structural checks:** pre/post ADR-030 — single-homing and data-bodies-stay
  flipped FAIL → PASS; binding-not-projection PASS.
- **Single-domain probe:** a recovered pre-separation build was decoupled from
  the persona by omission, not by construction — wiring the persona in changed
  execution 2/2 on two models. PES makes that isolation a rule.

## Discussion

[PES in the wild](DISCUSSION.md) — Codex CLI (Vaughan's mapping), Claude
Code, DeepSeek Harness, Dify, n8n, and a general retrofit checklist.

## Repository

- `pes_demo.py` — the demo above.
- `DISCUSSION.md` — tool-by-tool discussion.

The reference implementation is not publicly released.
