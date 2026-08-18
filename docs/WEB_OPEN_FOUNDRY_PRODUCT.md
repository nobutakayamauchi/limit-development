# WEB OPEN FOUNDRY — Productization Draft

Status: PRODUCTIZATION CANDIDATE / INQUIRY FIRST / NOT YET PRICED

## Brand

- Parent brand: **LIMIT OVER DEVELOPMENT**
- Product / operating model: **WEB OPEN FOUNDRY**
- Core promise: **仕事してください。ホームページが勝手にできます。**

## Problem

Small teams and solo operators often duplicate the same work into separate surfaces:

- company introduction
- sales material
- progress reports
- product pages
- roadmap / changelog
- request intake
- portfolio / proof of work
- educational / recruiting content

That creates work outside the actual work.

## Product thesis

WEB OPEN FOUNDRY turns real operating activity into a public-safe web surface.

Core loop:

WORK -> OBSERVE -> FILTER -> PUBLISH -> PARTICIPATE / BUY

The customer should spend time on the real work. The website should be reconstructed from approved source data with minimal manual publishing work.

## Public surface modules

1. COMPANY — who operates it, what it exists for, decision boundary
2. LIVE — current public-safe operating state
3. LABORATORY — requests / research themes and status
4. FACTORY — active development / production lines
5. DOGFOOD — what is being tested in real use
6. HISTORY — durable daily activity record
7. SHOP — products, consultations, purchase paths

Modules are optional per customer. Do not create modules that have no useful source data.

## Safety invariant

**Publication is allowlist-only.**

Never treat “connected data” as “publishable data.” A source connector may contain private or dangerous information. Public output must be reconstructed from explicit permitted fields only.

Default private:

- customer identities and raw requests
- private repository content
- credentials and auth material
- raw logs and stack traces
- precise sensitive financial data
- medical / legal / employment information
- internal approvals and decision packets
- unrepaired vulnerability details and exploit steps
- anything whose publication status is UNKNOWN

Changing public data categories is a Human Gate.

## Current commercial position

Do not invent a price yet.

Initial route:

inquiry -> fit check -> source/data boundary review -> proposed scope -> explicit consent -> quote/invoice -> implementation

The Limit Over Development site is the reference dogfood implementation and eventual live demo.

## Fit questions before sale

- What real work is already producing structured evidence?
- Which systems are canonical sources (GitHub, issue tracker, CMS, CRM, etc.)?
- What must never become public?
- Which public questions should the site answer without human explanation?
- Which actions should visitors be able to take (request, inquiry, buy, verify, learn)?
- How stale can each public module be before it becomes misleading?
- What happens when a source is unavailable or contradictory?

## Product success test

A successful deployment should let the operator answer routine questions with one sentence:

> こちらをご覧ください。

And let normal work automatically improve the public proof, education, participation and sales surface without creating a second publishing job.
