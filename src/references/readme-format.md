# README.md format

Read by rr-leaf-writer and rr-parent-writer when writing a module README.md, and by rr-verifier when checking one.

For a person who has never seen this code. Simple words, short sentences, concrete. No jargon without a one-line explanation. Assume competence, not context.

```markdown
# <module name>

<One or two sentences: what this is and what it does.>

## What it is for

<Plain explanation of the problem it solves. 3 to 6 sentences.>

## How it works

<Plain walkthrough of the main flow. Mermaid diagram if it makes the flow clearer.>

## Files

- `name.ext` - what it does, in one line.

## How to use it

<Minimal, runnable example or the command to run. Real values, not placeholders where avoidable.>

## Things to know

<Gotchas, limits, assumptions, required environment. Short bullets.>
```

Adapt headings to the module. Drop sections that would be empty. Length follows the module: a small module gets a short README.
