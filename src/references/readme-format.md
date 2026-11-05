# README.md format

Read by rr-leaf-writer and rr-parent-writer when writing a module README.md, and by rr-verifier when checking one.

For a person who has never seen this code. Simple words, short sentences, concrete. No jargon without a one-line explanation. Assume competence, not context.

```markdown
# <module name>

<One or two sentences: what this is and what it does.>

## What it is for

<Plain explanation of the problem it solves. 3 to 6 sentences.>

## How it works

<Plain walkthrough of the main flow. ASCII box diagram if it makes the flow clearer.>

## Files

- `name.ext` - what it does, in one line.

## How to use it

<Minimal, runnable example or the command to run. Real values, not placeholders where avoidable.>

## Things to know

<Gotchas, limits, assumptions, required environment. Short bullets.>
```

Adapt headings to the module. Drop sections that would be empty. Length follows the module: a small module gets a short README.

## Diagram style

A README.md diagram is an ASCII box diagram in a plain `text` fence. Never use a mermaid fence in a README.md; mermaid belongs in AGENTS.md. Draw a diagram only when it shows a flow, a fan-out or a pipeline better than prose would.

Rules:

- Label what enters at the top in plain text, with shapes or types in parentheses when they matter.
- Put each component in a box built from box-drawing characters. Give a box 2 to 4 short lines: name, then the key fact.
- Join steps with a vertical line that ends in a down arrow on every edge. Boxes are optional for trivial steps; a plain text line between two arrows is fine.
- Fan out with a horizontal bar and T-junctions. Draw parallel branches side by side with boxes of equal width. Rejoin with the mirror T-junctions.
- Show a bypass or optional path as a second vertical line down the right side, with a short note beside it.
- Branch or loop labels go on the line they belong to, in plain words (for example `FAIL, max 2 retries`).
- Keep every diagram line at most 78 characters wide. No emojis, no em dashes.

Example:

```text
            User: "remap this repo"
                       │
                       ▼
             ┌───────────────────┐
             │ rr-orchestrator   │
             │ runs the mapper   │
             └───────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
 ┌───────────────┐           ┌───────────────┐
 │ leaf writer   │           │ leaf writer   │
 │ module A      │           │ module B      │
 └───────────────┘           └───────────────┘
         │                           │
         └─────────────┬─────────────┘
                       ▼
             ┌───────────────────┐
             │ rr-verifier       │       FAIL: back to the writer
             │ PASS or defects   │       (max 2 retries)
             └───────────────────┘
                       │
                       ▼
             parent writer, one level up
```
