# Alignment Audit (Rules 85-100 / 16 items)

Repo: async-weight-streaming — audited 2026-10-11 (post v0.1.1 revision)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section (not security-domain; still documented) | PASS | README "Limits & Second-order Effects" covers truncation bugs and unbounded-processing risk |
| 2 | Privacy/redaction: zero keys/tokens/real names | PASS | grep scan of repo → 0 secret patterns; contact only hcac4735@agent.qq.com; no PII in code or docs |
| 3 | Copyright boundary | PASS | README credits source repo by link + structural restatement; no >50-word copied text; LICENSE (MIT) present |
| 4 | Fact-check labeling of numbers | PASS | All Quickstart timings tagged [estimated] with instruction to run self_test.py; memory claims cite test assertions |
| 5 | Confidence grading (≥2 explicit) | PASS | README bottom: High (memory cap, test-proven) + Medium (real-world RAM relief, [estimated]) |
| 6 | Minimal Fallback (PLAN B) | PASS | README "Minimal Fallback": pure-shell split+sha256 and stdlib file_digest alternatives |
| 7 | Quickstart timing | PASS | "~5 min" total with per-step timings; staged self-test → stats → hash → head |
| 8 | Design trade-off priority | PASS | "Design Trade-offs": memory bound > correctness > simplicity > throughput |
| 9 | CHANGELOG ≥2 iterations | PASS | v0.1.0 + v0.1.1 with named improvements |
| 10 | Exemption instruction (session rule) | N/A | Session-level governance; static repo not applicable |
| 11 | Time-sensitive data dated | PASS | README bottom: "as of 2026-10-11" |
| 12 | Explicit core assumptions (≥3) | PASS | "[Core Assumptions]": 4 items (sequential access, read(n) contract, resident proxy, consumer holds no refs) |
| 13 | Three-family self-test, all PASS | PASS | `python self_test.py` → 13/13 (functional 4, error paths 4, extreme edges 5: empty file, 10 MiB, truncated stream, exact block size, min budget) |
| 14 | Socratic FAQ "When NOT to use" | PASS | FAQ: small files / random-access workloads / not-a-database |
| 15 | ≥2 content iterations, ≥20% one dimension | PASS | v0.1.1: all perf numbers source-tagged (rule-4 coverage 0 informal→0 untagged), dead code removed, 1 new failure mode documented — README fact-labeling dimension reworked end-to-end |
| 16 | ≤60-word first paragraph with judgment | PASS | Opening paragraph: 58 words, closes with "keep using plain open().read()" judgment |

Additional: Second-order effects section — PASS (invisible truncation + feasibility-invites-unbounded-processing, each with countermeasure).
