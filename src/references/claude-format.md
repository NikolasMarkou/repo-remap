# CLAUDE.md format

Read by rr-leaf-writer and rr-parent-writer when writing a module CLAUDE.md, and by rr-verifier when checking one.

For Claude working in this module. Operational, specific, no motivation or sales copy. Target around 200 lines, hard ceiling 300 lines. If it will not fit, cut narrative and keep contracts, invariants, and paths.

```markdown
# <module name>

Path: `<path from repo root>`
Purpose: <one line>

## Scope

<What lives here and what explicitly does not.>

## Architecture

<Structure, data flow, control flow. Mermaid for state machines, protocols, pipelines.>

## Key files

| File | Role | Notes |
| --- | --- | --- |

## Public interface

<Exported functions, classes, endpoints, CLI commands, events. Signatures with types. Inputs, outputs, raised errors.>

## Data shapes

<Important structs, schemas, payloads, DB tables, config keys.>

## Invariants and constraints

<What must stay true. Ordering requirements, thread or async rules, idempotency, resource lifecycles.>

## Dependencies

<Internal modules relied on and what is used from them. External packages and why.>

## Failure modes

<Known errors, how they surface, how they are handled.>

## Working here

<Concrete rules for changing this code: conventions, where to add new cases, what to update in tandem, how to test, commands to run.>
```

Include the `Path:` line and enough context that the file is useful when read alone.
