# AI Covenant for LOKF

This covenant sets the norms for responsible AI use in the LOKF project. LOKF is
developed openly and with substantial AI assistance; this document makes the
resulting expectations explicit: AI is a tool that accelerates the work, but
every contribution is owned, understood, and defended by a human.

It applies to this repository:

- <https://github.com/nicholsn/lokf>

It is adapted from the
[LinkML AI Covenant](https://github.com/linkml/linkml/blob/main/AI_COVENANT.md).

## Core principle: you own your contributions

**Everything you contribute is yours — regardless of what tools helped create it.**

When you submit code, schema changes, documentation, issues, or comments with AI
assistance, *you* are the author. You are responsible for:

- Understanding what you are submitting
- Verifying its correctness and appropriateness
- Defending and explaining your choices during review
- Ensuring it meets the project's standards

Do not submit anything you cannot fully stand behind.

## No AI co-authorship

AI tools are **not** credited as authors or co-authors. Commit messages and pull
requests **MUST NOT** add `Co-Authored-By` trailers (or equivalent) for an AI
assistant. The human who runs the tool is the sole author and takes full
responsibility for the result.

## Generated artifacts

LOKF is defined once in `lokf.yaml`; the JSON-LD context, JSON Schema, SHACL
shapes, and OWL ontology are generated from it. AI assistance does not change
that contract: propose changes in `lokf.yaml` (or the toolkit, docs, or tests),
regenerate with `just build`, and commit the regenerated artifacts — never
hand-edit a generated file, whether by hand or with an AI.

## AI-assisted code reviews

AI review tools (Claude, Copilot, CodeRabbit, etc.) provide **automated quality
checks, not human reviews**.

- AI comments are suggestions, not requirements.
- PR owners may resolve AI comments without responding.
- Human reviewers may use AI feedback to inform their own review.
- A PR still requires human approval regardless of AI feedback.

## AI-assisted discussions

AI tools can be helpful **thinking aids** when preparing to participate in issues
and discussions. They may be used to clarify your own thinking, explore
alternative framings, or help draft *your* contribution for clarity and structure.

However, discussions exist to **surface, negotiate, and consolidate human
judgement**. AI systems **MUST NOT** be used to autonomously post comments,
replies, or messages in GitHub issues or discussions. Every contribution must
reflect a **human position** the author is prepared to explain, revise, and
defend. Posting AI-generated commentary as an independent "voice" undermines
trust, accountability, and the purpose of deliberation.

In short: AI may *support* participation; humans must *own* it.

## When to disclose AI assistance

**Required:**

- When proposing a fix or change to code or schema you don't fully understand,
  attribute the idea to AI so reviewers can assess it appropriately.

**Appreciated:**

- When brainstorming, distinguish "AI suggests X" from "I recommend X based on my
  own judgement." This helps prioritize ideas.

**Not required:**

- Routine use of AI to write code, schema, docs, issues, or PR descriptions.
- (AI co-authorship in commit messages is not merely "not required" — it is
  disallowed; see [No AI co-authorship](#no-ai-co-authorship).)

## What this means in practice

| Situation | Guidance |
| --------- | -------- |
| Writing code/schema/docs with Claude/Copilot | No disclosure needed; you own the result |
| Submitting an AI-suggested change you fully understand | No disclosure needed |
| Submitting an AI-suggested change in unfamiliar territory | Disclose the AI origin for reviewer context |
| Drafting an issue or PR description with AI | No disclosure needed; ensure it's accurate |
| Brainstorming in discussions | Be clear about AI-generated vs. your own ideas |
| Receiving AI review comments | Address or resolve at your discretion |
| Crediting an AI as a commit author or co-author | Not allowed |

## Trust and accountability

This covenant is built on trust. By contributing to LOKF, you agree that:

1. You will not submit AI-generated content without reviewing it.
2. You take responsibility for any issues arising from your contributions.
3. You will be honest about the origin of ideas when it matters for review quality.

---

*This covenant may evolve as AI tools and community needs change. It is adapted
from the [LinkML AI Covenant](https://github.com/linkml/linkml/blob/main/AI_COVENANT.md).
Feedback and suggestions are welcome.*
