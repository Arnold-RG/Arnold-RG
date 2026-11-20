# Security Engineering Standard — risk-based application

**Scope:** All repositories owned by Arnold-RG, existing and future.  
**Status:** Architecture and review policy. This document does **not** certify, deploy, or prove any security control.

## Non-negotiable baseline, scaled to the project

1. **Inventory and threat model:** identify users, stored data, trust boundaries, exposed interfaces, third-party services, and failure modes before implementation.
2. **Secure development:** validate untrusted input, encode output, avoid exposed secrets and sensitive logs, pin/lock dependencies when possible, and run repeatable security-aware tests in CI.
3. **Least privilege:** service credentials, CI permissions, OS privileges and human administrator rights must match actual responsibilities.
4. **Secure operation:** use TLS when appropriate, encrypted storage where risk warrants, monitoring, error handling, incident response, rollback, and tested backups for persistent important data.
5. **Review gate:** preserve existing design and usability; changes happen on reviewable branches/PRs. Do not deploy or merge based solely on passing static checks. Capture actual evidence.
6. **Right-sized infrastructure:** Docker for services that need reproducibility; Kubernetes only if genuinely useful to the deployment and support capacity. Pagination only for growing result sets, not as security theater.

## Selective specializations

| Area | Use when | Example controls | Skip when |
| --- | --- | --- | --- |
| AI Security | LLMs, ML inference, agents, RAG or automated high-impact decisions | Prompt-injection isolation, trusted tool boundaries, scoped agent permissions, output validation, data minimization, model evaluation, human approval for destructive actions | No AI or model components |
| GRC | Personal/sensitive data, customers, payments, regulated workflows, significant operational risk | Risk register, data inventory, licensing/consent review, retention and deletion policy, incident playbooks, applicable-law review and evidence | Do not impose enterprise paperwork on a public brochure |
| Cloud Security | Hosted backends, cloud storage, public APIs, containers, CI/CD or cloud-managed identity | Private networks, secret stores, IAM for workloads, hardened images, monitored access, tested restore and rollback | Pure offline/local programs with no external dependency |
| IAM | Human users, admin panels, shared data, API tokens, privileged automation | Server-enforced authorization, safe session handling, MFA/passkeys for privileged roles, scoped API credentials, revocation and audit | Truly anonymous public static content |
| OT Security | Actual industrial controls, ICS/SCADA, factory/energy/building systems or hardware affecting physical operations | Safety-first asset inventory, network segmentation, vendor-safe change windows, passive detection and tested isolation | Generic websites, SOC dashboards, or network utilities that do not control OT |

**Key distinction:** OT Security refers to *operational technology*, not ordinary IT operations or SOC operations. GRC is governance work, not an application plugin.

## Initial repository triage (November 2026)

The mapping below is an initial classification from repository roots and selected README/config reviews, **not** a completed source-code security assessment. “Conditional” means activate only after the referenced functionality is confirmed.

| Repository | Suggested priority and relevant focus |
| --- | --- |
| 2daymovie | **Medium** — API/hosting controls; IAM conditional on accounts; input and dependency tests |
| AbroadCost | **Low–Medium** — static client-side integrity, dependency hygiene, honest financial disclaimers; IAM only if accounts appear |
| arnold-portfolio | **Low** — static site, safe links/embeds, supply-chain checks; no unnecessary IAM/OT |
| Arnold-RG | **Low** — profile and dashboard content integrity, safe links, CI permissions |
| Boutique-la-difference | **Low–Medium** — public catalog integrity, third-party images, forms and client-data collection if added |
| boutique-la-difference-office | **High** — admin IAM, MFA/TOTP, audit logs, stock-change authorization, backup and secure deployment |
| elvora | **High** — sensitive fitness/health data privacy, mobile permissions and secure storage; AI safety conditional on AI capabilities |
| hamwe | **Medium** — web-app input/output safety and deployment; IAM conditional on actual user accounts |
| kingdom-life-krakow | **Medium** — public site baseline; evaluate admin.html and any content-admin workflows before allowing privileged writes |
| log-analyzer | **Medium** — log privacy, bounded parsing, safe handling of hostile log content and CLI privilege |
| network-monitor | **Medium** — least privilege, safe data capture and scope, no excessive network permissions |
| network-scanner | **Medium** — authorized targets only, bounded timeouts/rates and safe output; OT only if an ICS environment is explicitly in scope |
| our-money-hub | **High** — financial data minimization, encryption and recovery; true server-side IAM before shared remote data |
| peakwise | **Medium–High** — backend/ML artifact trust, data handling, AI/model safeguards when applicable |
| port-scanner | **Medium** — authorized scope, rate limits, timeouts, output sanitization; not OT by default |
| ragi | **High** — agent/tool trust, owner IAM, secret handling, network isolation, persistent-data safeguards |
| security-hardening-checker | **Medium** — least-privileged inspection, safe checks, no unapproved changes to host security settings |
| STANS | **High** — CI/container/IaC security, secret management, deployment validation and operational recovery; OT only if tied to control systems |
| STANS-archived-fork | **Maintenance-only until ownership purpose is confirmed** — avoid duplicate production work; scan before reuse |
| study-atlas | **Low–Medium** — content/build integrity, safe exercises, isolated test scripts |
| vira | **Low** — static frontend, browser security, safe external content; no mandatory IAM/OT |
| worldshield-soc | **High** — untrusted threat-feed validation, source attribution, safe rendering, scheduled workflow permissions; AI guardrails if analysis agents are introduced |

## Verification and acceptance criteria

- **Applicability:** record why a specialization applies or why it is not needed.
- **Evidence:** show changed files, test commands, CI outcomes, and owner-review links; do not claim a feature is protected merely because it is documented.
- **Privacy:** never use live customer, employee, location or financial data in tests without explicit authorization and an approved handling process.
- **AI autonomy:** apply permissions to *actions*, not just prompts. Require human approval for destructive, irreversible, monetary, privileged or externally consequential actions unless the owner has expressly approved a narrowly scoped safe workflow.
- **Remediation:** prioritize exploitable exposure, broken authorization, secret disclosure, data loss, and missing recovery controls before cosmetic or low-impact changes.
- **Compatibility:** provide a rollback plan and test existing deployment routes before switching cloud settings, domains, authentication or ports.

## Work allocation and sign-off

- **Elvora (policy and design):** assess relevant standards, maintain controls and document legal/licensing questions for professional review.
- **Forge (implementation):** create narrow changes with tests, type checks, deployment compatibility and rollback documentation.
- **Herod (assurance):** adversarial tests, security regressions, backup/restore tests, dependency/CI review, and unresolved-risk reporting.
- **Jarvis (release coordination):** prioritize risks, keep owner review visible and do not publish unapproved changes.

Names above describe the intended project workflow, not evidence of autonomous employees operating continuously.

## Reference guidance

- NIST CSF 2.0 — https://www.nist.gov/cyberframework
- NIST SP 800-63-4 Digital Identity — https://csrc.nist.gov/pubs/sp/800/63/4/final
- NIST SP 800-82 Rev.3 OT Security — https://csrc.nist.gov/pubs/sp/800/82/r3/final
- OWASP Top 10 for Agentic Applications (2026) — https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OWASP GenAI LLM Top 10 (2026) — https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/

**Decision rule:** security controls must be proportionate, tested, maintained and useful. A security control that breaks the product or cannot be operated securely is not an automatic upgrade.
