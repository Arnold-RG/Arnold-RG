# Project Security Standard — Arnold-RG / ArnovaGroup

**Scope:** All current repositories and new software products. This is a selection and release framework, **not** a claim that every codebase has passed a security audit. Review the actual implementation, architecture and business data before deciding which controls are required.

## Mandatory baseline — proportionate to risk

1. **Inventory and threat model:** Document entry points, trust boundaries, dependencies, data flows, hosting and third-party services. Separate publicly accessible content from privileged operations.
2. **Access and secrets:** Enforce least-privilege repository, CI, API and service permissions. Never commit tokens, credentials, signing keys or customer private data. Require human approval for sensitive actions. Use host-managed secret stores when credentials are necessary.
3. **Dependencies and CI:** Keep dependency update automation where relevant; maintain lint, tests and security checks for the actual stack. Review supply-chain changes. Prefer narrowly scoped CI permissions and protected deployment environments.
4. **Input, output and data protection:** Validate inputs at the server/trust boundary; use context-appropriate escaping and parameterized queries. Apply rate limiting and abuse protection to exposed services. Minimize and protect personal/financial data, exports, logs and backups.
5. **Reliability and release safety:** Run tests before merging, document rollback and recovery for stateful systems, use appropriate backups and restrict production deployment permissions. Static sites do not require Kubernetes or a database just to satisfy a checklist.
6. **Reporting:** Include responsible vulnerability disclosure and supported versions. Do not claim compliance, encryption, AI reliability or successful security tests without evidence.

## Select security domains only when applicable

| Domain | When to activate | Minimum design questions |
| --- | --- | --- |
| IAM | Accounts, administrators, API/service identities, private data, customer portals | Server-enforced authentication and authorization; MFA where supported; scoped tokens; secure sessions; account recovery; access reviews |
| Cloud security | Cloud hosting, CI/CD, managed data stores, containers, third-party APIs | Minimal runtime and deploy permissions; environment isolation; secret management; logging; infrastructure scanning where applicable; backups and rollback |
| GRC | Every project at a proportionate level; strongest for financial, health, personal data and client operations | Applicable privacy/licensing requirements, consent, retention, risk register and verified policies; no unsupported certification |
| AI security | LLMs, AI models, agent workflows, retrieval systems, automated decisions | Treat prompts, retrieved pages and logs as untrusted; protect API keys/model/data; prevent prompt injection and data exfiltration; scope tools; human review for irreversible actions |
| OT security | Direct access to industrial automation, PLC, SCADA, IoT control or safety-critical machinery | Segmentation, restricted access, change windows, vendor/safety review, passive assessment first; never run generic active scanners blindly on production OT |

## Repository-specific security scope (inventory on 2026-11-20)

This is a *triage map*, not test evidence. Recheck whenever the stack changes.

| Repository | Main current security focus |
| --- | --- |
| `worldshield-soc` | Public feed integrity, ingestion/parser safety, scheduled job token scope; AI safeguards only for actual AI report generation |
| `arnold-portfolio` | Static web assets, external links, document/photo privacy, least-privilege publishing |
| `Boutique-la-difference` | Public catalogue and customer-contact privacy; payment/auth controls only if backend transactions exist |
| `elvora` | Flutter/mobile + backend boundaries; API authentication, personal data protection, AI/agent scope if those capabilities run |
| `STANS-archived-fork` | Container/Kubernetes IaC and secrets, CI supply chain, API access, client/server isolation |
| `study-atlas` | Static learning content + educational scripts; safe submissions, dependency checks and privacy |
| `Arnold-RG` | Profile/static deployment, action permissions and public portfolio data |
| `peakwise` | Python/backend access, model and dataset integrity, frontend/API boundaries and secret management |
| `our-money-hub` | Household-finance confidentiality, client-side encryption/key handling, data isolation and recovery |
| `2daymovie` | Python web app input validation, route security, deployment secrets and abuse prevention |
| `kingdom-life-krakow` | Public GitHub-token admin page, asset upload and external links, consented photos and private community data |
| `AbroadCost` | Browser data handling, third-party data integrity, outbound links, no client secrets |
| `ragi` | Web/backend authentication when applicable, API security, secrets, storage and deployment |
| `STANS` | Container/Kubernetes/IaC security, CI scanning, secret lifecycle and authorization |
| `vira` | ArnovaGroup website contact privacy, public CI and external integrations, truthful client/AI claims |
| `boutique-la-difference-office` | Node server and admin surface, authorization, protected customer/office data, server-side validation |
| `hamwe` | Frontend dependencies, web/API trust boundaries and privacy; enable IAM only when private accounts exist |
| `network-scanner` | Scope authorization, bounded scanning, topology export privacy, shell input validation |
| `port-scanner` | Authorized targets, bounded port probes, sensitive banners and export safety |
| `network-monitor` | MAC/IP inventory and log retention, authorized monitoring, least-privilege OS access |
| `security-hardening-checker` | Read-only guarantee, minimum privileges, confidential host reports and honest findings |
| `log-analyzer` | Untrusted log parsing, read-only behavior, privileged log access and sensitive-output protection |

**OT scope:** None of the currently inspected repositories obviously implements industrial-control operations; do not add OT integrations by assumption.

## Changes and sign-off

For existing and new repositories: inspect README/source/workflows → identify applicable risks and current controls → make narrow changes on a branch → add or update stack-appropriate automated checks → run tests and inspect actual CI results → document residual risks and rollback plan → submit a **draft PR** for owner review. Do not merge or deploy automatically.

For a new repository, repeat the assessment before the first public release and again when an app gains a backend, accounts, payments, personal data, AI tools, cloud workloads or OT connectivity. Never reuse credentials or private client content across projects.

## Current rollout note (2026-11-20)

All 22 inspected repositories contained Dependabot configuration and at least one GitHub Actions workflow. Fifteen already contained `SECURITY.md`. Seven missing policies were proposed as reviewable pull requests: `kingdom-life-krakow`, `vira`, `network-scanner`, `port-scanner`, `network-monitor`, `security-hardening-checker`, and `log-analyzer`. Pending PRs are **not** merged protections. This inventory is not evidence that all code paths, deployments or cloud settings were audited or that all CI checks pass.
