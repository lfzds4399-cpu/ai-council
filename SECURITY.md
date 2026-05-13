# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Use GitHub's private security advisory channel:
**https://github.com/lfzds4399-cpu/ai-council/security/advisories/new**

Include: vulnerable version, repro steps, impact assessment, and your contact preference.

## Response targets

- Acknowledgement: within **72 hours**
- Triage + severity assessment: within **7 days**
- Fix or mitigation plan: within **30 days** for high-severity

## Supported versions

The latest minor version receives security fixes. Older minors are best-effort.

## Threat model

`ai-council` is a pure-Python decision aggregator. It does not by itself touch the network, the filesystem (beyond the optional `MeetingStore`), or shell. The realistic risk surface is:

1. **Malicious voter code** — a `Voter` you install runs in-process with full Python privileges. Audit third-party voters before adding them to a `Council`.
2. **MeetingStore on disk** — the default JSONL store writes to a path you choose. If that path is world-writable, a local attacker can tamper with the audit log.
3. **LLM-backed voters** — if you wrap an LLM call in a voter, the prompt is whatever the proposal contains. Sanitize untrusted proposal content before voting.

## Hardening checklist for users

- Pin your `ai-council` version in `requirements.txt` / `pyproject.toml`.
- Treat the `Council`'s output as advisory; combine with policy gates outside the framework for irreversible actions (money, deletes, deploys).
- For production audit trails, write the `MeetingStore` to a path only your service account can write.
