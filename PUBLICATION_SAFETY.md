# Limit Development Public Disclosure Boundary

Status: DRAFT / FAIL-CLOSED

This repository exposes a public factory-tour surface. Transparency is useful only when it does not expose customers, security-sensitive details, private operations, credentials, or information that has not been explicitly approved for publication.

## Core rule

**PUBLICATION IS ALLOWLIST-ONLY.**

Nothing becomes public merely because it exists in a control file, a repository, an automation result, an inquiry, a request, or an internal observation.

A field is public only when the public builder explicitly selects it.

New fields are private by default.

Unknown publication status means **DO NOT PUBLISH**.

## Allowed public board classes

The current board may expose only the explicitly allowlisted classes below:

- current operating mode
- public main-project name
- public-safe focus summary
- aggregate request / shipped / approval-waiting status when the value is intentionally provided for public use
- project name
- already-public repository identifier
- public stage
- public speed classification
- short public-safe current-work summary
- low-risk public GitHub telemetry: latest activity time, open PR count, and Actions status

The builder must not pass arbitrary source objects through to the public JSON.

## Never auto-publish

The following are non-public by default and require a separate explicit publication decision even when related source material exists elsewhere:

- secrets, tokens, API keys, credentials, cookies, auth material
- customer names, email addresses, phone numbers, company-specific identifiers, contracts, invoices, payment details
- inquiry or request bodies before deliberate anonymization / generalization / publication approval
- private repository names, paths, file contents, branch names or internal URLs
- exact cash balances, private sales figures, bank information, tax information or other sensitive financial state
- medical, legal, employment or personal-life details that are not intentionally part of the public surface
- raw approval packets, internal human-gate reasoning or private operational notes
- unrepaired vulnerability details, exploit reproduction steps, security-sensitive architecture, incident secrets
- raw logs, stack traces, environment variables or debug dumps unless specifically sanitized and approved
- arbitrary commit messages or PR bodies merely because a repository is public
- hypotheses presented as confirmed facts
- data with unknown disclosure status

## Request Lab rule

A submitted request is **private by default**.

Submission does not grant publication permission.

Only an intentionally generalized and public-safe research theme may appear on the public site. It must not contain information that can reasonably identify the requester or their customer unless separate explicit permission exists.

The public pipeline may show a generalized state such as RECEIVED / RESEARCHING / PROTOTYPING / DOGFOOD / PRODUCTIZED, but no private request text is automatically copied to the public site.

## Incident rule

Security or incident transparency must not become an attack guide.

Until a problem is repaired and a separate publication decision is made, the public surface should use coarse labels such as:

- INCIDENT UNDER INVESTIGATION
- SAFETY FIX IN PROGRESS
- PUBLICATION WITHHELD

Detailed reproduction, vulnerable endpoints, credentials, internal topology and exploit mechanics stay non-public.

## Fail-closed behavior

If the builder cannot determine whether a field is allowed, it omits the field.

If telemetry cannot be fetched, the site shows UNKNOWN rather than guessing zero or success.

If a new internal field is added, it must not appear publicly unless the public allowlist is deliberately changed and the leak tests pass.

## CI enforcement

The PR validation workflow injects fake sensitive fields and fake sensitive commit messages and asserts that they cannot reach the generated public board.

A change that breaks the publication boundary must fail CI and must not be merged merely to restore the page.

## Human Gate

Changing what categories of information are public is a publication-policy change and therefore requires Human review.

Publishing, customer contact, payment changes, pricing changes, deploys that materially alter public disclosure, or release of previously withheld sensitive material remain separate Human Gates.
