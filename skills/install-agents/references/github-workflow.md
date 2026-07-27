# GitHub Actions template — periodic agents

Starting point for `.github/workflows/periodic-agents.yml` (write it at
exactly that path). Adapt the `schedule:` list and the trigger→agent `case`
map to the agents and slots the user chose — the two must stay in lockstep,
one cron entry and one `case` arm per agent. A `workflow_dispatch` input
keeps every agent manually runnable regardless of its slot.

The action ecosystem moves: if you are unsure an input below is still
current, check the `anthropics/claude-code-action` README before writing the
file — never guess input names.

```yaml
name: Periodic agents

on:
  schedule:
    - cron: "0 6 * * 1"   # architect  — Mon 06:00 UTC
    - cron: "0 6 * * 2"   # deadwood   — Tue 06:00 UTC
    - cron: "0 6 * * 3"   # docbot     — Wed 06:00 UTC
    - cron: "0 6 * * 4"   # refactor   — Thu 06:00 UTC
    - cron: "0 6 * * 5"   # sentinel   — Fri 06:00 UTC
    - cron: "0 6 * * 6"   # testforge  — Sat 06:00 UTC
    - cron: "0 6 * * 0"   # uidesigner — Sun 06:00 UTC
    - cron: "0 12 * * 1"  # uxpolish   — Mon 12:00 UTC
  workflow_dispatch:
    inputs:
      agent:
        description: "Agent to run (e.g. architect)"
        required: true

permissions:
  contents: write
  pull-requests: write

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - name: Map trigger to agent
        id: pick
        env:
          SCHEDULE: ${{ github.event.schedule }}
          DISPATCH_AGENT: ${{ inputs.agent }}
        run: |
          case "$SCHEDULE" in
            "0 6 * * 1")  agent=architect ;;
            "0 6 * * 2")  agent=deadwood ;;
            "0 6 * * 3")  agent=docbot ;;
            "0 6 * * 4")  agent=refactor ;;
            "0 6 * * 5")  agent=sentinel ;;
            "0 6 * * 6")  agent=testforge ;;
            "0 6 * * 0")  agent=uidesigner ;;
            "0 12 * * 1") agent=uxpolish ;;
            *)            agent="$DISPATCH_AGENT" ;;
          esac
          [ -n "$agent" ] || { echo "no agent mapped for this trigger" >&2; exit 1; }
          echo "agent=$agent" >> "$GITHUB_OUTPUT"

      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Read .claude/agents/${{ steps.pick.outputs.agent }}.md and act as
            that agent for exactly one run in this repository. Follow its
            process end to end: learn the project first, pick one primary
            change, verify with the project's linter and tests, and open a
            reviewable pull request — never commit to the default branch.
            Before starting, check open pull requests from previous runs; if
            one already covers the same ground, or nothing qualifies today,
            stop and report instead of forcing a change.
```

## Before the first scheduled run, the user must

1. Set the repository secret: `gh secret set ANTHROPIC_API_KEY`.
2. Allow Actions to open PRs: repo **Settings → Actions → General →
   Workflow permissions** — enable *"Allow GitHub Actions to create and
   approve pull requests"* (the `permissions:` block alone is not enough).

## Adapting

- **Subset of agents:** keep only their cron entries and `case` arms.
- **Other cadences:** daily → distinct hours (`0 6 * * *`, `0 7 * * *`, …);
  monthly → distinct days of month stepping by 3 (`0 6 1 * *`,
  `0 6 4 * *`, …). Keep one agent per trigger so runs never overlap.
- **Project setup:** if the repo needs dependencies installed before lint or
  tests can run, add those setup steps between checkout and the agent step.
