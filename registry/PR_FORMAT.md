# Shared Boardroom / Engine Room registry

Canonical file: registry/prs.json. Schema version 1 uses schemaVersion, repository, positive roadmapVersion, planVerified, plannedPrCount, observedAt, units and pullRequests. Unit IDs are immutable. prs lists actual linked GitHub PR numbers, not imagined PR ordinals. PullRequests is a dated observation, not GitHub's source of truth. Do not regenerate a second parallel roadmap or call an unstarted unit 'partially implemented'.

The authoritative contract is maintained in neophilism/Boardroom at registry/PR_FORMAT.md and registry/pr-contract.mjs. This repository's validator is a compatible fail-closed subset; consumers must honor GitHub's live state.
