# Rederive setup for Arnold-RG repositories

Rederive (by Eric Zou): https://github.com/EricJujianZou/rederive

## Purpose

Use guided first-principles questions to learn why each codebase is designed as it is. Rederive is a **local coding-agent skill**, not a GitHub Action, continuous scanner, or hosted monitoring service. A **global install** makes it available across repositories without copying third-party code into every project.

## Prerequisites

- Node.js / npm (for `npx`), Git, Python 3, and Bash (on Windows, Git Bash or WSL if your agent requires Bash).
- Authenticated GitHub CLI (`gh auth login`) to clone public and private repositories accessible to the account.
- A compatible agent such as Codex, Cursor, or Claude Code.

## Set up

- **Windows:** open PowerShell in this directory; run `.\install-all.ps1`. For a custom clone folder, use `-Workspace 'D:\\my-code'`. Use `-SkipClone` to install only the global skill.
- **macOS/Linux:** run `bash install-all.sh` (optional arguments: owner and workspace).

Both scripts install the community skill globally, then clone currently accessible, non-archived repositories that do not already exist locally. **Existing folders are never pulled, reset or overwritten.** New repositories are discovered dynamically each time.

## Run a learning session

Open your coding agent inside a cloned repo. Run:

```
/rederive
```

Or target one repository directly:

```
/rederive https://github.com/Arnold-RG/worldshield-soc
```

Rederive maps architectural choices and asks you to reconstruct the decisions. Local learning logs and decision maps live under `.rederive/`; upstream instructions exclude them from Git commits. Sessions are interactive: installing the skill does **not** complete all 22 learning sessions automatically.

## Additional repository audit topics

Use a separate verified code audit for: language and framework versions, application flows, API/data boundaries, databases, Docker/Compose, Kubernetes manifests, IaC, deployment, GitHub Actions, security, testing, backups, restore procedures and compatibility. The presence of a config file is not evidence a deployment is running. Avoid adding Docker/Kubernetes to static sites without a real operational reason.

## Safety

Review the upstream skill before installing. Scripts do not run code inside target repositories, modify branches, overwrite local folders, merge PRs, or deploy changes. Do not commit private analysis logs. Keep project-specific vulnerability findings private until triaged.

Source: https://github.com/EricJujianZou/rederive (MIT licensed). The installer retrieves the official upstream skill; no upstream code is vendored here.
