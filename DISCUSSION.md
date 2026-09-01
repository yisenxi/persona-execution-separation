# Discussion: PES in the Wild

Where the pattern shows up in real agent tooling, and where today's systems
fall short. This is community-facing discussion; the paper's own claims live
in the paper.

---

## Codex CLI

Daniel Vaughan read the paper and mapped PES onto Codex CLI's building blocks
in [Persona-Execution Separation: An Architecture Pattern for LLM Agents in Governed
Environments — and What It Means for Codex CLI](https://codex.danielvaughan.com/2026/08/29/persona-execution-separation-llm-agent-architecture-codex-cli-agents-md-trust-domain-audit/)
(2026-08-29). It is the most accurate independent reading we have seen.

| PES element | Codex CLI analogue (per Vaughan) |
|---|---|
| Single-homed persona (P1/P2) | Layered `AGENTS.md` discovery (repo root → `.codex/` → global), extends not duplicates |
| One-way valve (P3) | `untrusted_project` lockout (v0.150.0): untrusted AGENTS.md cannot modify hooks/requirements |
| Approval matrix (P5) | `approval_policy` in `config.toml` (deny/ask/allow per tool) |
| Audit ledger | `rollout.jsonl` (append-only, but not hash-chained, not consulted at decision time) |

His gap analysis is the valuable part. Three gaps:

1. **Execution can modify the persona.** In a default session the agent can
   `apply_patch` on `AGENTS.md` while doing its job — the execution side
   writes the persona, collapsing the boundary and violating G3. Mitigation:
   `deny_write` on persona files plus a `PreToolUse` hook.
2. **No explicit contract bridge.** Named profiles bind persona to execution
   config statically; there is no approval-gated work-order object.
3. **Audit ledger is not chained.** `rollout.jsonl` can be altered by an agent
   with workspace write access; route `PostToolUse` events to an external
   append-only sink instead.

If you run Codex in a governed setting, fix gap 1 first.

## Claude Code

Claude Code has the same shape, with one difference that matters: permissions
and hooks are first-class and evaluated *outside* the model's context.
`PreToolUse` hooks run before permission rules and can block a tool call with
exit code 2; `PermissionRequest` fires when Claude is about to ask for
permission. That is closer to the PES principle — the gate is not the persona
— than Codex's default posture.

| PES element | Claude Code analogue |
|---|---|
| Single-homed persona | `CLAUDE.md` (project → user → enterprise layers) |
| Approval matrix | Permission modes + deny/ask/allow rules; `/permissions` |
| External gate | `PreToolUse` hooks — exit code 2 blocks the tool call before permission rules |
| Audit | Session transcripts / permission requests (not a chained ledger) |

The gap is the same one: nothing stops the agent from writing `CLAUDE.md`
unless you deny it. A hook like this closes it:

```bash
# PreToolUse: reject edits to persona/policy files from the execution side
TARGET=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // empty')
case "$TARGET" in
  *CLAUDE.md|*.claude/settings.json)
    echo "Blocked: persona/policy files are read-only in the execution domain" >&2
    exit 2
    ;;
esac
```

## DeepSeek Harness

[DeepSeek Harness](https://github.com/deepseek-ai/DeepSeek-Harness) (207k+
stars, MIT) is the most popular open-source harness as of September 2026 —
"everything is a plugin", built on Cordis, with per-action approval prompts
and sandboxing. It is not a PES instance, but it is the most useful
near-neighbour for one reason: it shows that the *execution-gate* half of PES
is now table stakes in the most-adopted harness, while the *identity* half is
still missing.

| Concern | DeepSeek Harness | PES |
|---|---|---|
| Execution gating | Per-action approval prompts, permission controls | Approval matrix at the bridge |
| Sandbox / containment | Sandbox (its own SAFETY.md: "do not rely on it as the sole security control") | Restrictive domain + DLP |
| Persona/execution separation | None — persona and execution share the plugin runtime | Different trust domains |
| Persona drift vs audit stability | No architectural decoupling; audit not protected from drift | Persona singly-homed; drift does not touch the ledger |
| Multi-user governance | Developer-tool oriented, single-user first | Multi-user + approval matrix + DLP |

The plugin that acts is the plugin that reads the persona. There is no
architectural guarantee that a persona edit cannot reach execution, and no
audit record that is structurally protected from drift. That is the
single-domain trade-off in one paragraph. For a single-user developer harness
it is the right trade — most of us would not want a two-domain setup to chat
with a coding agent. The point is not that DeepSeek Harness is wrong; it is
that the moment you add multi-user deployment, audit requirements, and
expected persona churn, the single-domain trade stops paying.

## Dify

[Dify](https://github.com/langgenius/dify) (154k+ stars, Apache-2.0) is the
mainstream low-code agent platform for teams — the B-side tool people in
China actually reach for. It already has the organizational half of PES:
workspaces, tenants, roles (admin vs member), and members only use published
apps. That is a real governance story, and it is why teams pick it.

| PES element | Dify |
|---|---|
| Multi-user governance | Workspaces / tenants / roles; members use only published apps |
| Execution gating | Tool permissions and member roles — no approval matrix at the crossing |
| Persona/execution separation | None — an app bundles its system prompt and its workflow/tools in one artifact |
| Persona drift vs audit stability | Editing the app's prompt re-touches the same artifact that executes |
| Audit | Run logs exist; not a chained, decision-time-consulted ledger |

What it lacks is the architectural half. Edit the prompt and you re-touch the
same bundle that executes. The draft → publish flow is a coarse one-way
valve over the whole app — it gates "this app is visible to members", not
"persona changes cannot touch what the app does". There is no audit anchor
that survives a prompt edit.

If you run Dify in a governed setting, three config-level moves get you most
of the way there: freeze the prompt at publish time and iterate the persona
in a separate draft; keep tool permissions in the workspace role layer rather
than in prompt text; export run logs to an external append-only sink if you
need an audit record that outlives app edits.

## n8n

[n8n](https://github.com/n8n-io/n8n) (203k+ stars, fair-code) is the Western
counterpart — the most-starred B-side workflow platform, with native AI
nodes. Its story is the mirror image of Dify's: the tooling is
workflow-first, execution-native, but governance arrives as an *edition*.

| PES element | n8n |
|---|---|
| Multi-user governance | Edition-gated: RBAC + workflow-level permissions + audit logging are enterprise; community edition has no RBAC (admin sees all) |
| Execution gating | Per-node credentials + enterprise RBAC; no approval matrix at an architectural crossing |
| Persona/execution separation | None — the AI agent node bundles system prompt and tool calls in the workflow graph |
| Persona drift vs audit stability | Editing a workflow's AI node re-touches the same artifact that executes |
| Audit | Enterprise audit logging; not a chained, decision-time-consulted ledger |

n8n has the pieces (RBAC, audit, credentials) but they are administered
around the workflow graph, not enforced by it. "Who may run what" is a
licensing decision layered on top, not a boundary the graph itself enforces.

The retrofit is similar to Dify's: version workflows and manage the system
prompt as a single-homed draft bound into a release; use enterprise RBAC for
who-may-run-what and keep authorization out of prompt text; export execution
data to an external append-only sink if the record has to survive workflow
edits. The community edition's logging is not a PES-grade ledger.

## A general retrofit checklist

Across all of the above — and most agent frameworks — the same four moves
turn a single-domain agent into something close to PES, at config level, no
architecture rewrite:

1. **Persona singly-homed.** One writable location for instructions and
   tone. Execution never reads it for authorization — at most it is an audit
   reference.
2. **Execution cannot write the persona.** `deny_write` or a `PreToolUse`
   hook that blocks edits to persona/policy files. This is the single most
   valuable move; it closes the coupling Vaughan found in Codex.
3. **External gate, not prompt rules.** Approval decisions in a config layer
   (`approval_policy`, permission modes, hooks) — never "please ask before
   deleting" written inside the persona text. The gate has to survive persona
   drift, which means it cannot live in the persona.
4. **Append-only, chained audit.** Route tool-call events to an external
   append-only sink with hash chaining, so a later persona edit cannot
   rewrite what the agent did.

One honest caveat: if the agent is single-user, has no audit requirement, or
its persona rarely changes, all of this is overhead for nothing. Version the
whole bundle instead. PES earns its complexity only when multi-user
deployment, execution audit, and expected persona churn hold jointly — that
is Section 4.7 of the paper, and it is worth re-reading before you retrofit
anything.

## A note on what this page is

The paper makes the claims; this page is interpretation. The Codex mapping is
Daniel Vaughan's analysis, cited above; the rest are our own readings of
public documentation. If you build one of these retrofits, we would be
interested to hear how it holds up.
