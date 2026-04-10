# DataHub × Nebius Hackathon — IDEAS

🎯 **Pick your idea by 10:30 AM** — 15 min after problem reveal. See SELECTED-IDEA for the recommended commit.

**All three ideas use the same skeleton**: Coordinator agent \+ 3 specialist agents on Nebius, DataHub as shared blackboard memory, SQLite as the "real data" oracle. Commit to architecture before April 10, swap prompts/tools when the problem statement drops at 10:15.

## 🎯 Dataset → idea mapping (huge intel from the official README)

The hackathon authors **engineered each dataset for a specific L-level pattern**. Reading the dataset README before event day reveals what the problem statement is likely to involve:

| Dataset | Pre-baked test case | Best idea fit | Pre-built variants |
| :---- | :---- | :---- | :---- |
| **healthcare** | Forking pipeline; quality issues should halt billing but NOT demographics | **\#1 Incident Response (L6)** ⭐ | `healthcare.db` (issues planted) |
| **nyc-taxi** | 3-stage pipeline where staging silently falls 3 days behind raw | **\#2 Reality Auditor (L5)** | `nyc_taxi.db` \+ `nyc_taxi_pipeline.db` |
| **olist-ecommerce** | 9 tables with planted orphan keys, NULL categories, ID format mismatches | **\#2 Reality Auditor (L5)** OR reconciliation variant | `olist.db` (clean) \+ `olist_dirty.db` (broken) |

**The single most useful pre-event action**: read each dataset's README at `~/code/datahub-static-assets/datasets/<name>/README.md` on Studio A. They list every planted issue and which downstream is affected. This is the cheat code to event day.

---

## 🥇 Idea \#1 — "Data Incident Response Team" (the kit's L6 example, executed well)

**Tagline**: *"Page a team of agents instead of waking up an on-call engineer."*

### Trigger

"Production dashboard is showing wrong revenue numbers — handle it."

### Agent team (parallel via OpenClaw, all on Nebius R1)

| Agent | Role | Tools |
| :---- | :---- | :---- |
| 🕵️ **Detective** | Queries DataHub MCP for lineage, finds upstream tables, inspects schema history, identifies suspect joins | DataHub MCP, GraphQL API |
| 🔬 **Reality-Checker** | Runs actual SQL against the SQLite oracle, compares row counts/distributions/freshness vs. what DataHub *says* | SQLite tools, DataHub read |
| 🔧 **Fixer** | Proposes either a metadata fix (update DataHub tags/owners/freshness) or a SQL patch, writes a postmortem document | DataHub Python SDK (write), file write |
| 🧠 **Coordinator** | Synthesizes findings, posts to Slack/Discord, writes the incident report back into DataHub as an annotation | All agents above \+ Slack webhook |

### Why it wins

- Maps **1:1 to the kit's L6 diagram** — judges instantly recognize you nailed the brief  
- Demonstrates *all* of: DataHub read, DataHub write, SQL execution, multi-agent coordination, MCP integration  
- **Wow moment** \= live "page" → 30s of agents arguing → fix proposal printed  
- The L6 incident response framing is also implicitly an enterprise sales pitch — exactly what DataHub Cloud sells. Judges from DataHub will love it.

### Unfair advantage

You've built this exact pattern in OpenClaw (SCOUT/PLANNER/SAFETY in nebius-hackathon RoboStore). Rename, rewire to DataHub MCP, done.

### Effort to pre-build

6/10 — agent skeleton \+ DataHub MCP wiring \+ Slack webhook \+ a fake "production incident" trigger

---

## 🥈 Idea \#2 — "Reality vs Lineage Auditor" (L5 → L6 by stacking agents)

**Tagline**: *"DataHub says 1,050 entities. We checked. 312 of them are lying."*

### The trick

Run a continuous audit pass over a DataHub instance. For every dataset, three agents in parallel ask different questions:

| Agent | Question | Action |
| :---- | :---- | :---- |
| 🪞 **Schema Auditor** | DataHub's schema says X columns; what does the actual SQLite table report? | Diff schemas, flag drift |
| ⏰ **Freshness Auditor** | DataHub says "updated daily"; what's the most recent timestamp in actual data? | Compute true staleness |
| 📊 **Quality Auditor** | DataHub has no quality flags; let the agent compute null rates, outliers, type drift | Write findings back to DataHub as glossary terms |

**Coordinator** ranks findings by severity, generates an "Audit Score: 73/100" dashboard, and **enriches DataHub itself** so the next pass starts smarter (closes the L2 feedback loop on top of L5/L6).

### Why it wins

- Concrete numbers, visual diff, **"we found 312 lies"** is a killer demo line  
- Judges from DataHub will love it because **it actively improves their product**  
- Combines L2 \+ L5 \+ L6 in one architecture (3 levels in one demo)

### Unfair advantage

Injester's Karpathy loop is exactly the "improve over iterations" pattern. Lift the loop, point it at DataHub instead of webpages.

### Effort to pre-build

5/10 — three Python agents \+ DataHub SDK write-back \+ a simple HTML scoreboard

---

## 🥉 Idea \#3 — "Schema-Change Bouncer" (L4 always-on → L6 multi-agent jury)

**Tagline**: *"A pull request changes a column type. Three agents vote on whether to merge."*

### Trigger

Schema-change event (simulate via watching the SQLite file or a webhook).

### Agent team

| Agent | Role |
| :---- | :---- |
| ⚠️ **Blast Radius Agent** | Traverses DataHub lineage to find every downstream dashboard/table affected. Counts users impacted via DataHub usage stats. |
| 📜 **Compliance Agent** | Checks DataHub glossary terms (PII, financial, regulated). Reads ownership and pings owners. |
| 🧪 **Backwards-Compat Agent** | Reads the actual SQLite data, simulates the change, reports breakages. |
| ⚖️ **Judge (Coordinator)** | Collects votes, classifies as `safe / risky / blocked`, posts decision back to DataHub as a tagged annotation, optionally pages Slack. |

### Why it wins

- **Production-pattern** judges immediately recognize from real dataops workflows  
- "Always-on" framing differentiates from L3 agents  
- **Demo moment**: make a destructive schema change live, watch agents block it in real-time

### Unfair advantage

Topology \+ OpenClaw for the multi-agent voting pattern. Sideline's MCP+A2A protocols if you want to expose the bouncer as an MCP tool to judges' Cursor.

### Effort to pre-build

7/10 — webhook listener \+ 4 agents \+ ASCII demo of "change blocked"

---

## Comparison matrix

|  | \#1 Incident Response | \#2 Reality Auditor | \#3 Schema Bouncer |
| :---- | :---- | :---- | :---- |
| Levels hit | L6 | L2+L5+L6 | L4+L6 |
| Pre-build effort | 6/10 | 5/10 | 7/10 |
| Demo wow factor | 9/10 | 8/10 | 7/10 |
| Maps to kit's L6 example | ✅ exact | partial | partial |
| Judges' enterprise relevance | very high | high | very high |
| Reuses Ben's existing code | OpenClaw 1:1 | Injester Karpathy loop | Topology \+ Sideline MCP |
| Risk of being done by other teams | medium | low | low |

## Recommendation: Idea \#1

- The kit's own L6 diagram is essentially this idea — judges will instantly recognize you nailed the brief  
- OpenClaw orchestration code from `nebius-hackathon` (RoboStore SCOUT/PLANNER/SAFETY) ports almost 1:1  
- "Live page → watch agents fight → see the fix" demo arc is irresistible  
- Uses every primitive: DataHub read, DataHub write, SQL on real data, multi-agent coordination, MCP, Slack — judges' "did they use everything?" checkbox lights up green

**See `DataHub-Nebius - SELECTED-IDEA.md` for the build plan.**  
