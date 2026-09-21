# Style and self-containment

Read by rr-leaf-writer and rr-parent-writer before writing any doc, and by rr-verifier when checking one.

## Self-containment

A reader must be able to act on one file alone, without opening another file in the tree.

Rules:

- No cross-document links or pointers such as "see the parent README", "as described in `../core/CLAUDE.md`", "refer to the root docs".
- Repeat the context a reader needs, even if it also appears elsewhere. Duplication across files is expected and correct here.
- Referring to source files by path is fine and encouraged. Referring to other docs is not.
- Define local terms, acronyms, and domain words in the file that uses them.
- Each file states what the module is and where it sits in the repo in its first lines, so it works when read in isolation.

## Style constraints

These apply to every generated file:

- Plain, direct language.
- No emojis.
- No em dashes.
- No preamble, no closing summary, no meta-commentary about the documentation itself.
- Mermaid is allowed and encouraged for diagrams, flows, state machines, and protocols.
- Do not invent behavior. If something is unclear from the code, say it is unclear or leave it out. Never guess at intent and present it as fact.
- Override any of this only when the user explicitly asks.
