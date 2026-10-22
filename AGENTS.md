# Umami Avocado development agents

Read README.md, docs/DEVELOPMENT_PLAN.md and registry/PR_FORMAT.md before changes. Follow the planned work IDs UA-001 to UA-030 and dependencies. Never label planned work as partially implemented.

## Current boundaries
- This GitHub repository is **PUBLIC**. Never put secrets, private vendor quotes, confidential biology or owner information in commits, issues, PRs or logs.
- The foundational web UI, API and worker are inert: no external lab credentials, charges, specimens, manufacturing or food clearance are present.
- Agents may draft experiments but may never approve their own physical activity, bypass scoped human/expert authorization, spend money or initiate a biological shipment.
- Keep SIMULATED versus PHYSICAL permanently distinct in future schemas; no conversion based on mutable free-text or model output.

## Work queue and completion
- Canonical roadmap is registry/prs.json; validate with node scripts/validate-pr-registry.mjs.
- Implement the highest-priority dependency-ready PR. If blocked by provider access, hosting, budgets or scientific approval, record that precise blocker and proceed to an unrelated ready unit.
- Before merging normal code work, verify actual latest-head tests and repo merge requirements. An independent paid human code audit is not a general prerequisite, but physical-lab and legal/regulatory authorizations are separate gates.
- Each merged PR requires working changes and accurate evidence. Never infer merge or implementation from a planned registry entry.
- Continue immediately to the next ready work item when an accepted PR is merged; coordinate exclusive ownership with Boardroom when available.
