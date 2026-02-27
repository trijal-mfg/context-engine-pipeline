# Confluence Docs Search Guide

4,775 Markdown files in `docs/`. Each file is named `{page_id}_{title}.md` with YAML frontmatter:
```
---
title: ...
space: SPACE_KEY
page_id: 123456
url: ...
---
```

**Golden rule:** Always `grep` first to narrow to 2–5 files, then `Read` those files. Never try to read all docs at once.

---

## Space Keys (primary filter)

| Space | Count | What's in it |
|-------|-------|--------------|
| `TPG` | 977 | Teen Patti Gold — game ops, incidents, releases |
| `SRE` | 566 | Infrastructure, SOPs, runbooks, alerts |
| `FEAT` | 466 | Feature specs, product requirements |
| `PLATFORM` | 282 | Platform architecture, backend services |
| `LC` | 247 | Ludo Club game |
| `PC` | 184 | Parchis Club game |
| `LC1` | 184 | Ludo Club variants |
| `LQC` | 100 | Ludo Quick Club |
| `HG` | 35 | House Games |
| `MSE` | 34 | Mobile Support Engineering |
| `CC` | 22 | Cricket Club |
| `WG` | 11 | Word Games |

Personal/team spaces appear as UUIDs (e.g. `~834523218`) — usually one-off notes.

---

## Document Type Prefixes (in filename)

| Prefix | Count | Use for |
|--------|-------|---------|
| `RCA_` | 87 | Incident post-mortems |
| `SOP_` | 48 | Operational runbooks / alert response |
| `LLD_` | 17 | Low-level design / implementation specs |
| `SIO_` | 22 | Service I/O procedures |
| `WAD_` | 179 | Word game daily updates |
| `TPG_` | 124 | Teen Patti Gold specific |
| `TRV_` | 114 | Trivia game |
| `MFSDK_` | 26 | Moonfrog SDK |
| `AWS_` | 14 | AWS infrastructure |
| `EKS_` | 7 | Kubernetes |

---

## Search Patterns by Question Type

### Incidents / outages / crashes
```bash
# All RCAs
grep -ril "rca\|root cause\|postmortem" docs/ | sort -t_ -k1 -rn

# RCAs for a specific system
grep -ril "redis" docs/ | grep -i "rca\|crash\|outage\|down"

# Most recent (highest page_id = most recently created)
ls docs/*RCA*.md | sort -t_ -k1 -rn | head -10
```

### Runbooks / how to fix an alert
```bash
grep -ril "sop\|runbook\|steps to\|how to" docs/ | grep -i "KEYWORD"

# SOPs are almost always in SRE space
grep -rl "^space: SRE" docs/ | xargs grep -il "KEYWORD"
```

### Feature / product design
```bash
# LLD or HLD for a feature
grep -ril "FEATURE_NAME" docs/ | grep -i "lld\|hld\|design\|spec"

# Feature space
grep -rl "^space: FEAT" docs/ | xargs grep -il "FEATURE_NAME"
```

### Architecture / infrastructure
```bash
grep -rl "^space: PLATFORM" docs/ | xargs grep -il "KEYWORD"
grep -ril "architecture\|infrastructure\|deployment" docs/ | head -10
```

### Game-specific
```bash
# Filter by game space then keyword
grep -rl "^space: TPG" docs/ | xargs grep -il "KEYWORD"
grep -rl "^space: LC" docs/ | xargs grep -il "KEYWORD"
```

### Migration guides
```bash
grep -ril "migration\|migrate" docs/ | sort -t_ -k1 -rn | head -15
```

### Cost / infra reports
```bash
grep -ril "cost cadence\|cost report\|spend" docs/ | sort -t_ -k1 -rn
```

---

## Recency

Page IDs are sequential — **higher ID = more recently created page.**

```bash
# Sort any result set by recency
... | sort -t_ -k1 -rn | head -10
```

Approximate ID ranges:
- > 3,000,000,000 → 2023–2025
- 1,000,000,000 – 3,000,000,000 → 2021–2023
- < 1,000,000,000 → 2018–2021

---

## Efficient Multi-Step Search

```bash
# Step 1: broad keyword search
grep -ril "KEYWORD" docs/ | sort -t_ -k1 -rn | head -20

# Step 2: narrow by space
grep -rl "^space: SRE" docs/ | xargs grep -il "KEYWORD" | sort -t_ -k1 -rn

# Step 3: narrow by doc type
grep -rl "^space: SRE" docs/ | xargs grep -il "KEYWORD" | grep -i "sop\|rca"

# Step 4: read the top 2-3 results
```

---

## Common Keyword → Space Mapping

| Topic | Best spaces to search |
|-------|-----------------------|
| Redis, Kafka, Mongo, Couchbase | `SRE`, `PLATFORM`, `TPG` |
| Game server, delta failures, concurrents | `TPG`, `SRE` |
| Feature spec, game economy, UX | `FEAT`, `LC`, `PC`, `TPG` |
| Payments, IAP, Paytm, Razorpay | `TPG`, `PLATFORM` |
| Kubernetes, EKS, Docker | `PLATFORM`, `SRE` |
| SDK, mobile, iOS, Android | `MSE`, `MFSDK`, `FEAT` |
| Login, Facebook, Firebase | `TPG`, `FEAT` |
| Ads, analytics, CleverTap | `TPG`, `FEAT` |
