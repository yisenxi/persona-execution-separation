# -*- coding: utf-8 -*-
"""The five ADRs behind PES (paper Section 5.2, Table 3), as data.

Each decision records what was chosen and what was rejected. The demo prints
this chain so the mechanism in pes_demo.py is anchored to the real case.
"""

from dataclasses import dataclass


@dataclass
class ADR:
    """One architectural decision with its rejected alternatives."""

    id: str            # P1..P5
    date: str          # ISO date of the decision
    record: str        # ADR number or spec reference
    role: str          # seed / binding / contract / channel / crystallization
    decision: str
    rejected: list[str]  # alternatives considered and rejected


DECISIONS: list[ADR] = [
    ADR(
        id="P1",
        date="2026-07-19",
        record="ADR-005",
        role="seed",
        decision="Persona gets a dedicated home, separate from execution.",
        rejected=["(none recorded)"],
    ),
    ADR(
        id="P2",
        date="2026-07-19",
        record="ADR-005",
        role="binding",
        decision="Employees bind to shared capabilities by reference, not by copy.",
        rejected=["Copying skills per employee (copies drift)"],
    ),
    ADR(
        id="P3",
        date="2026-07-19",
        record="Spec",
        role="contract",
        decision="One-way valve: personal→org via approval; reverse forbidden.",
        rejected=["Unconstrained bidirectional flow"],
    ),
    ADR(
        id="P4",
        date="2026-08-12",
        record="ADR-014",
        role="channel",
        decision="Promotion is a dedicated, approval-mandatory work order.",
        rejected=["Reusing the ordinary delegation path"],
    ),
    ADR(
        id="P5",
        date="2026-08-17",
        record="ADR-030",
        role="crystallization",
        decision="Dual-face crystallized: persona singly-homed, execution faceless, binding not projection.",
        rejected=[
            "Read-only persona mirror in the restrictive domain",
            "Projecting the persona into the restrictive domain",
            "Exposing the restrictive domain's full API directly",
            "Free-form inter-agent channel",
        ],
    ),
]
