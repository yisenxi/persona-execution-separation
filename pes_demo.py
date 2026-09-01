# -*- coding: utf-8 -*-
"""PES demo — Persona-Execution Separation (arXiv:2608.27427).

Zero-dependency, no LLM calls, no keys. Shows the mechanism of Section 4:
persona drifts freely in one domain; governed execution runs in another;
the bridge is the only crossing (approval + DLP + audit). Changing the
persona does not change execution; changing the SOP definition does.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from decisions import DECISIONS


@dataclass
class Persona:
    """Persona: instructions + tone. Drifts freely; execution never reads it."""

    name: str
    instructions: str
    tone: str = "neutral"

    def edit(self, *, instructions: str | None = None, tone: str | None = None) -> None:
        if instructions is not None:
            self.instructions = instructions
        if tone is not None:
            self.tone = tone


class Step(Enum):
    COLLECT = "collect"
    DRAFT = "draft"
    REVIEW = "review"
    DONE = "done"


@dataclass
class SOP:
    """Governed SOP in the restrictive domain. Faceless."""

    name: str
    steps: list[Step]
    tools: list[str]

    def run(self, inputs: dict) -> dict:
        trace = []
        state = {"inputs": inputs, "artifacts": {}}
        for i, step in enumerate(self.steps):
            tool = self.tools[i] if i < len(self.tools) else "noop"
            if step is Step.COLLECT:
                state["artifacts"]["collected"] = inputs.get("query", "")
            elif step is Step.DRAFT:
                state["artifacts"]["draft"] = f"[{state['artifacts'].get('collected', '')}] -> drafted"
            elif step is Step.REVIEW:
                state["reviewed"] = True
            elif step is Step.DONE:
                state["done"] = True
            trace.append({"step": step.value, "tool": tool})
        return {"state": state, "trace": trace}


class Verdict(Enum):
    APPROVED = "approved"
    DENIED = "denied"


@dataclass
class AuditLedger:
    entries: list[dict] = field(default_factory=list)

    def append(self, entry: dict) -> None:
        prev = self.entries[-1]["hash"] if self.entries else "genesis"
        entry["hash"] = hashlib.sha256(
            f"{prev}|{json.dumps(entry, sort_keys=True, default=str)}".encode()
        ).hexdigest()[:16]
        self.entries.append(entry)

    def summary(self) -> str:
        if not self.entries:
            return "0 entries"
        return f"{len(self.entries)} entries, chain intact: {self.entries[-1]['hash']}"


@dataclass
class ContractBridge:
    """Fail-closed crossing. Validates independently of the persona."""

    approval: dict[tuple[str, str], bool]
    dlp_sensitive: set[str]
    ledger: AuditLedger = field(default_factory=AuditLedger)

    def submit(self, *, user: str, action: str, params: dict, persona_id: str) -> Verdict:
        if not self.approval.get((user, action), False):
            self._log(user, action, params, persona_id, "denied:approval")
            return Verdict.DENIED
        if self.dlp_sensitive.intersection(params):
            self._log(user, action, params, persona_id, "denied:dlp")
            return Verdict.DENIED
        self._log(user, action, params, persona_id, "approved")
        return Verdict.APPROVED

    def _log(self, user, action, params, persona_id, result) -> None:
        self.ledger.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "persona_id": persona_id,
            "params": params,
            "result": result,
        })


def run_sop(sop: SOP, bridge: ContractBridge, inputs: dict) -> tuple[Verdict, dict]:
    """Gate the SOP through the bridge; the persona is only an audit id."""
    verdict = bridge.submit(user="alice", action=f"sop:{sop.name}", params=inputs, persona_id="employee-42")
    if verdict is Verdict.DENIED:
        return verdict, {}
    return verdict, sop.run(inputs)


def main() -> None:
    print("=" * 60)
    print("PES demo — Persona-Execution Separation (arXiv:2608.27427)")
    print("=" * 60)

    print("\nThe five ADRs behind the pattern (paper §5.2):")
    for adr in DECISIONS:
        print(f"  {adr.id} [{adr.date}] {adr.decision}")
        for r in adr.rejected:
            print(f"      rejected: {r}")

    persona = Persona("employee-42", "Write the weekly report.", "professional")
    sop = SOP(
        "weekly_report",
        [Step.COLLECT, Step.DRAFT, Step.REVIEW, Step.DONE],
        ["kb_search", "doc_generate", "submit_review", "finish"],
    )
    bridge = ContractBridge(
        approval={("alice", "sop:weekly_report"): True},
        dlp_sensitive={"sensitive_body"},
    )
    inputs = {"query": "Q3 portfolio performance"}

    v1, r1 = run_sop(sop, bridge, inputs)
    print(f"\n[1] baseline                verdict={v1.value} trace={[t['step'] for t in r1['trace']]}")

    persona.edit(instructions="Write the weekly report with humor and emojis.", tone="playful")
    v2, r2 = run_sop(sop, bridge, inputs)
    same = [t["step"] for t in r1["trace"]] == [t["step"] for t in r2["trace"]]
    print(f"[2] persona drift            verdict={v2.value} trace={[t['step'] for t in r2['trace']]} same={same} (V1: R=0)")

    v3 = bridge.submit(user="alice", action="sop:weekly_report", params={"sensitive_body": "client-data"}, persona_id="employee-42")
    print(f"[3] DLP blocks body          verdict={v3.value}")

    sop2 = SOP(
        "weekly_report",
        [Step.COLLECT, Step.DRAFT, Step.REVIEW, Step.DONE],
        ["doc_generate", "kb_search", "submit_review", "finish"],
    )
    v4, r4 = run_sop(sop2, bridge, inputs)
    changed = r1["trace"] != r4["trace"]
    print(f"[4] SOP def changed          verdict={v4.value} tools_changed={changed} (P2: definitions penetrate)")

    v5 = bridge.submit(user="bob", action="sop:weekly_report", params={}, persona_id="employee-42")
    print(f"[5] unauthorized user        verdict={v5.value}")

    print("\n" + "=" * 60)
    print("Persona drift -> execution unchanged; SOP change -> execution changes.")
    print("The boundary is architectural, not a prompt rule.")
    print("=" * 60)


if __name__ == "__main__":
    main()
