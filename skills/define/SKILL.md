---
name: define
description: >-
  Turn a request into a problem statement, scope (in and out), and
  done-criteria, and write them to the issue. Use before planning, when the
  request is still loose. Not for task breakdown (plan) or solution design.
---

# define

Turn a loose request into a definition someone can plan from: what problem, how much of it, and how we know it is done. Say what and how much, never how.

## 1. Gather

- Read the issue, its comments, and anything it links. No issue: the request in the conversation is the source.
- Read the code the request touches, enough to name the real files, functions, and current behavior. A definition that cites `src/export.py` beats one that says "the export code."
- Note what the issue already answers. Never ask the user something the issue or the code already says.

## 2. Ask, or assume

- Ask only questions whose answers change the scope or the done-criteria. Skip ones about style or implementation.
- The user is present: ask them now, a few at a time, before writing.
- The user said they won't be around, or you run unattended: don't wait. Take the most reasonable answer, state it as an assumption, and keep the question under **Open questions** so someone can overturn it.

## 3. Write the definition

```
## Problem
Who is affected, what they cannot do today, and why it matters.
Cite the current behavior in the code (file, function).

## Scope
### In
- each capability this work delivers
### Out
- each nearby thing it deliberately does not do, and why

## Done-criteria
- observable, testable outcomes, one per line
- each phrased so a person can check it: input → expected result

## Assumptions
- what you decided without an answer

## Open questions
- each question still worth asking?
```

- Done-criteria describe behavior, not tasks. "Running `export --csv` writes a header row" is a criterion; "add a CSV writer" is a task for `plan`.
- Out-of-scope items must be real temptations, things a planner might otherwise build.
- No design: no architecture, libraries, data models, or task lists.

## 4. Record it

- An issue exists: post the definition as a comment (`gh issue comment <n> --body-file <file>`), unless the user asked for the issue body.
- No issue yet: show the draft to the user and settle the open questions with them first. File an issue only once they confirm.
- Change no code, tests, or files in the repository.

## 5. Report

The issue URL, a one-line summary of the scope, and the open questions that remain.
