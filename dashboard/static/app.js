// data-oncall dashboard — vanilla JS, no frameworks
(function () {
  const DATAHUB_UI = "http://100.114.31.63:9002";
  const PANES = ["coordinator", "detective", "reality_checker", "fixer"];
  const STATE_KEY = { idle: "idle", thinking: "thinking", querying: "querying", done: "done", error: "error" };

  // ─── Replay mode detection ───────────────────────────────────────────
  // On the Tailscale Funnel URL we have a real live backend on Mac Mini.
  // On any other host (Vercel, localhost-static, github.io, etc.) the
  // backend isn't reachable — we fall back to a client-side replay of the
  // canned 27-event sequence so the page still tells the full story.
  const IS_REPLAY_MODE =
    !location.hostname.includes("eliass-mac-mini") &&
    !location.hostname.includes("localhost") &&
    !location.hostname.includes("127.0.0.1");

  // Client-side event sequence for replay mode (mirrors dashboard/stub_agents.py)
  const REPLAY_EVENTS = [
    { delay: 0,    agent: "system",          type: "agent_started",          data: { incident: "revenue dashboard showing wrong numbers — investigate" } },
    { delay: 300,  agent: "coordinator",     type: "agent_started",          data: {} },
    { delay: 900,  agent: "coordinator",     type: "thinking",               data: { text: "User reports the revenue dashboard showing wrong numbers. I need to identify which dataset backs the dashboard, trace its upstream lineage, validate the upstream against reality, and propose a fix." } },
    { delay: 1600, agent: "coordinator",     type: "thinking",               data: { text: "I'll dispatch Detective and Reality-Checker in parallel via asyncio.gather — Detective on lineage, Reality-Checker on the cross-instance assertion diff. Fixer waits for both, then writes the postmortem back." } },
    { delay: 2200, agent: "detective",       type: "agent_started",          data: {} },
    { delay: 2400, agent: "reality_checker", type: "agent_started",          data: {} },
    { delay: 2900, agent: "detective",       type: "nl_query",               data: { question: "Find the dataset for the seller performance view in olist_dirty" } },
    { delay: 3700, agent: "detective",       type: "graphql_generated",      data: { graphql: '{ search(input: {type: DATASET, query: "v_seller_performance", start: 0, count: 5}) { searchResults { entity { urn ... on Dataset { name platform { name } } } } } }' } },
    { delay: 4300, agent: "detective",       type: "graphql_executed",       data: { summary: "Identified affected dataset: v_seller_performance", rows: 1 } },
    { delay: 4700, agent: "reality_checker", type: "nl_query",               data: { question: "Show me all assertions and their latest results for olist_order_items, olist_customers, olist_products in BOTH olist_source and olist_dirty" } },
    { delay: 5500, agent: "detective",       type: "nl_query",               data: { question: "Get all upstream lineage from olist_dirty.v_seller_performance, 2 hops" } },
    { delay: 6200, agent: "detective",       type: "graphql_generated",      data: { graphql: '{ lineage(input: {urn: "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.v_seller_performance,PROD)", direction: UPSTREAM, count: 100, hops: 2}) { count entities { entity { urn } degree } } }' } },
    { delay: 7000, agent: "reality_checker", type: "graphql_executed",       data: { summary: "Queried 6 assertion sets (3 tables × 2 instances)", rows: 6 } },
    { delay: 7400, agent: "detective",       type: "graphql_executed",       data: { summary: "Found 5 upstream datasets", rows: 5 } },
    { delay: 8200, agent: "detective",       type: "agent_completed",        data: { summary: "Lineage: v_seller_performance ← olist_order_items ← olist_sellers (3 hops)" } },
    { delay: 9400, agent: "reality_checker", type: "agent_completed",        data: { summary: "Found 3 production-only failures: 5,632 truncated seller_ids, 7,955 deleted customers, 988 NULL categories" } },
    { delay: 10000, agent: "coordinator",    type: "coordinator_synthesizing", data: {} },
    { delay: 10600, agent: "fixer",          type: "agent_started",          data: {} },
    { delay: 11200, agent: "fixer",          type: "tool_called",            data: { tool: "datahub_sdk.quarantine_dataset", args: { urn: "olist_dirty.main.olist_order_items", incident_id: "INC-REPLAY" } } },
    { delay: 11800, agent: "fixer",          type: "postmortem_written",     data: { urn: "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_order_items,PROD)", annotation: "⚠️ INC-REPLAY: 5632 seller_id_length_eq_32 violations" } },
    { delay: 12400, agent: "fixer",          type: "tool_called",            data: { tool: "datahub_sdk.quarantine_dataset", args: { urn: "olist_dirty.main.olist_customers", incident_id: "INC-REPLAY" } } },
    { delay: 13000, agent: "fixer",          type: "postmortem_written",     data: { urn: "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_customers,PROD)", annotation: "⚠️ INC-REPLAY: 7955 row_count_eq_99441 violations" } },
    { delay: 13600, agent: "fixer",          type: "tool_called",            data: { tool: "datahub_sdk.quarantine_dataset", args: { urn: "olist_dirty.main.olist_products", incident_id: "INC-REPLAY" } } },
    { delay: 14200, agent: "fixer",          type: "postmortem_written",     data: { urn: "urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.main.olist_products,PROD)", annotation: "⚠️ INC-REPLAY: 988 product_category_name_not_null violations" } },
    { delay: 15000, agent: "fixer",          type: "tool_called",            data: { tool: "slack.post", args: { channel: "#data-incidents" } } },
    { delay: 15400, agent: "fixer",          type: "slack_posted",           data: { channel: "#data-incidents", text: "🚨 INC-REPLAY: 3 referential integrity bugs in olist_dirty — 3 tables quarantined" } },
    { delay: 16000, agent: "fixer",          type: "agent_completed",        data: { summary: "Quarantined 3 datasets, Slack post sent" } },
    { delay: 16600, agent: "coordinator",    type: "thinking",               data: { text: "Synthesizing the final postmortem. Detective traced lineage to v_seller_performance. Reality-Checker found 3 production-only assertion failures. Fixer quarantined the 3 affected tables via Python SDK." } },
    { delay: 17400, agent: "coordinator",    type: "agent_completed",        data: { summary: "Postmortem complete for INC-REPLAY" } },
    { delay: 18000, agent: "system",         type: "incident_complete",      data: {
        elapsed_ms: 17800,
        postmortem: "INCIDENT INC-REPLAY: Production data quality failure detected in olist_dirty.\n  • olist_order_items: 5,632 seller_id_length_eq_32 violations\n  • olist_customers: 7,955 row_count_eq_99441 violations\n  • olist_products: 988 product_category_name_not_null violations\nAll 11 assertions pass on the clean olist_source instance, confirming the issues are confined to production. 3 datasets quarantined via DataHub Python SDK. Recommend the data-platform team rerun the upstream loader and investigate the source of the corruption."
      }
    },
  ];

  async function runReplay() {
    const start = Date.now();
    for (const { delay, agent, type, data } of REPLAY_EVENTS) {
      const elapsed = Date.now() - start;
      if (delay > elapsed) await new Promise(r => setTimeout(r, delay - elapsed));
      handleEvent({ ts: new Date().toISOString(), agent, type, data });
    }
  }

  // ─── DOM helpers ─────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const paneBody = (agent) => $(`pane-${agent}`);
  const paneEl = (agent) => document.querySelector(`.agent-pane[data-agent="${agent}"]`);
  const ledEl = (agent) => paneEl(agent)?.querySelector(".led");
  const tokensEl = (agent) => paneEl(agent)?.querySelector(".tokens");
  const costEl = (agent) => paneEl(agent)?.querySelector(".cost");
  const modelBadgeEl = (agent) => document.querySelector(`.model-badge[data-agent="${agent}"]`);

  // ─── Run state ───────────────────────────────────────────────────────
  let eventSource = null;
  let runStart = 0;
  let elapsedTimer = null;
  let totalCost = 0;
  const agentTokens = { coordinator: 0, detective: 0, reality_checker: 0, fixer: 0 };

  // Cost per agent (USD per million tokens, output side as approximation)
  const COST_PER_TOKEN = {
    coordinator: 2.50e-6,        // Kimi-K2-Thinking
    detective: 0.09e-6,          // Llama 8B
    reality_checker: 0.09e-6,
    fixer: 1.20e-6,              // MiniMax M2.5
  };

  // ─── Fine-tune story panel ───────────────────────────────────────────
  async function loadFinetuneMetrics() {
    try {
      const r = await fetch("/static/finetune_metrics.json");
      const m = await r.json();

      $("ft-base-model").textContent = m.base_model.split("/").pop();
      $("ft-tuned-model").textContent = m.fine_tuned_model.split("/").pop();
      $("ft-pairs").textContent = `${m.training.train_pairs} train · ${m.training.val_pairs} val · ${m.training.patterns_covered} patterns`;
      const lc = m.lora_config;
      $("ft-lora").textContent = `rank ${lc.rank} · α ${lc.alpha} · LR ${lc.lr} · ${lc.epochs}ep · batch ${lc.batch_size}`;

      // Status badge
      const status = m.fine_tune_status || "unknown";
      const badge = $("ft-status-badge");
      if (badge) {
        if (status === "trained_pending_deployment") {
          badge.textContent = "TRAINED · PENDING DEPLOY";
          badge.className = "status-pending";
        } else if (status === "trained_nebius_deploy_deprecated") {
          badge.textContent = "TRAINED · NEBIUS DEPLOY DEPRECATED";
          badge.className = "status-pending";
        } else if (status === "deployed") {
          badge.textContent = "DEPLOYED";
          badge.className = "status-done";
        } else {
          badge.textContent = status.toUpperCase();
        }
      }

      // Deployment note (the why-no-deployed-endpoint explanation)
      const noteEl = $("ft-deployment-note");
      if (noteEl) {
        noteEl.textContent = m.deployment_note || "";
        noteEl.style.display = m.deployment_note ? "block" : "none";
      }

      // Job details
      const setText = (id, v) => { const el = $(id); if (el) el.textContent = v; };
      setText("ft-job-id", m.job_id || "—");
      setText("ft-job-type", m.job_type || "—");
      setText("ft-created", formatTs(m.created_at));
      setText("ft-completed", formatTs(m.completed_at));
      setText("ft-duration", m.training_time_min ? `${m.training_time_min} min` : "—");
      setText("ft-cost", m.estimated_cost_usd != null ? `$${m.estimated_cost_usd.toFixed(2)}` : "—");

      // Loss curve table
      const tbody = $("loss-tbody");
      if (tbody && Array.isArray(m.loss_curve)) {
        tbody.innerHTML = "";
        // Find max for the bar scaling
        const maxLoss = Math.max(...m.loss_curve.map(e => Math.max(e.train_loss, e.val_loss)));
        for (const epoch of m.loss_curve) {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>Epoch ${epoch.epoch}</td>
            <td>${epoch.train_loss.toFixed(4)}</td>
            <td>${epoch.val_loss.toFixed(4)}</td>
            <td>
              <div class="loss-mini-bar">
                <div class="loss-mini-fill train" style="width: ${(epoch.train_loss / maxLoss * 100).toFixed(1)}%"></div>
                <div class="loss-mini-fill val" style="width: ${(epoch.val_loss / maxLoss * 100).toFixed(1)}%"></div>
              </div>
            </td>
          `;
          tbody.appendChild(tr);
        }
      }
      if (m.loss_summary) {
        $("loss-summary").innerHTML = `
          <div class="loss-summary-row">
            <strong>Val loss:</strong> ${m.loss_summary.val_loss_start.toFixed(4)} → ${m.loss_summary.val_loss_end.toFixed(4)}
            <span class="loss-delta">−${m.loss_summary.val_loss_drop_pct}%</span>
          </div>
          <div class="loss-summary-row">${m.loss_summary.trajectory}</div>
        `;
      }

      // Accuracy bars (may be null until measure_accuracy.py runs)
      if (m.accuracy.base_pct != null && m.accuracy.fine_tuned_pct != null) {
        $("bar-base").style.width = m.accuracy.base_pct + "%";
        $("bar-tuned").style.width = m.accuracy.fine_tuned_pct + "%";
        $("bar-base-pct").textContent = m.accuracy.base_pct + "%";
        $("bar-tuned-pct").textContent = m.accuracy.fine_tuned_pct + "%";
        $("bar-improvement").textContent = "+" + m.accuracy.improvement_pct + " points";
        $("accuracy-note").textContent = m.accuracy.metric_definition || "";
      } else {
        $("bar-base").style.width = "0%";
        $("bar-tuned").style.width = "0%";
        $("bar-base-pct").textContent = "TBD";
        $("bar-tuned-pct").textContent = "TBD";
        $("bar-improvement").textContent = "run measure_accuracy.py";
        $("accuracy-note").textContent = m.accuracy.note || "";
      }

      $("sample-nl").textContent = m.sample_pair.nl;
      const code = $("sample-graphql");
      code.textContent = m.sample_pair.graphql;
      if (window.Prism) Prism.highlightElement(code);

      // Artifact links
      const links = m.links || {};
      const setLink = (id, url) => {
        const el = $(id);
        if (el && url) { el.href = url; el.style.display = ""; }
        else if (el) { el.style.display = "none"; }
      };
      setLink("ft-link-hf", links.huggingface);
      setLink("ft-link-wandb", links.wandb);
      setLink("ft-link-gh", links.github);
    } catch (e) {
      console.error("Failed to load finetune_metrics.json", e);
    }
  }

  function formatTs(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("en-US", { hour: "numeric", minute: "2-digit", month: "short", day: "numeric" });
    } catch { return iso; }
  }

  // ─── LED state per agent ─────────────────────────────────────────────
  function setLed(agent, state) {
    const led = ledEl(agent);
    if (!led) return;
    led.className = "led " + state;
    const badge = modelBadgeEl(agent);
    if (badge) badge.dataset.active = (state !== "idle" && state !== "done") ? "true" : "false";
  }

  // ─── Append event to a pane ──────────────────────────────────────────
  function appendEvent(agent, type, data) {
    const body = paneBody(agent);
    if (!body) return;
    const div = document.createElement("div");
    div.className = `event event-${type}`;

    const label = document.createElement("div");
    label.className = "event-label";
    label.textContent = type.replace(/_/g, " ");
    div.appendChild(label);

    const content = document.createElement("div");
    content.className = "event-content";

    if (type === "thinking") {
      content.textContent = data.text || "";
    } else if (type === "nl_query") {
      content.textContent = "❓ " + (data.question || "");
    } else if (type === "graphql_generated") {
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.className = "language-graphql";
      code.textContent = data.graphql || "";
      pre.appendChild(code);
      content.appendChild(pre);
      if (window.Prism) Prism.highlightElement(code);
    } else if (type === "graphql_executed") {
      content.textContent = "✓ " + (data.summary || "") + (data.rows ? ` (${data.rows} rows)` : "");
    } else if (type === "tool_called") {
      const tool = data.tool || "?";
      const arg = data.args ? Object.values(data.args)[0] : "";
      content.textContent = `↪ ${tool}(${typeof arg === "string" ? arg.slice(0, 50) : arg})`;
    } else if (type === "postmortem_written") {
      content.textContent = "📝 " + (data.annotation || "");
    } else if (type === "slack_posted") {
      content.textContent = "📨 " + (data.channel || "") + ": " + (data.text || "").slice(0, 80);
    } else if (type === "error") {
      content.textContent = "⚠ " + (data.message || JSON.stringify(data));
    } else {
      content.textContent = JSON.stringify(data);
    }

    div.appendChild(content);
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  // ─── Handle one event from SSE ───────────────────────────────────────
  function handleEvent(event) {
    const { agent, type, data } = event;
    if (!agent || agent === "system") {
      if (type === "incident_complete") {
        finishRun(data);
      } else if (type === "error") {
        $("status-badge").className = "status-error";
        $("status-badge").textContent = "ERROR";
        appendEvent("coordinator", type, data);
      }
      return;
    }

    // Update LED based on event type
    if (type === "agent_started") setLed(agent, "querying");
    else if (type === "thinking") setLed(agent, "thinking");
    else if (type === "nl_query") setLed(agent, "querying");
    else if (type === "graphql_executed") setLed(agent, "querying");
    else if (type === "tool_called") setLed(agent, "querying");
    else if (type === "agent_completed") setLed(agent, "done");
    else if (type === "error") setLed(agent, "error");
    else if (type === "coordinator_synthesizing") setLed("coordinator", "thinking");

    appendEvent(agent, type, data);

    // Bump token / cost counters (rough — we count events as ~150 tokens each)
    const tokensThisEvent = 150;
    agentTokens[agent] = (agentTokens[agent] || 0) + tokensThisEvent;
    const t = agentTokens[agent];
    if (tokensEl(agent)) tokensEl(agent).textContent = t.toLocaleString() + " tok";
    const c = t * (COST_PER_TOKEN[agent] || 0);
    if (costEl(agent)) costEl(agent).textContent = "$" + c.toFixed(4);
    totalCost += tokensThisEvent * (COST_PER_TOKEN[agent] || 0);
    $("cost-counter").textContent = "💰 $" + totalCost.toFixed(4);
  }

  // ─── Start / finish helpers ──────────────────────────────────────────
  function startRun() {
    runStart = Date.now();
    totalCost = 0;
    PANES.forEach((a) => {
      agentTokens[a] = 0;
      paneBody(a).innerHTML = "";
      setLed(a, "idle");
      if (tokensEl(a)) tokensEl(a).textContent = "0 tok";
      if (costEl(a)) costEl(a).textContent = "$0.0000";
    });
    $("postmortem-body").className = "empty";
    $("postmortem-body").textContent = "Running…";
    $("affected-datasets").innerHTML = "";

    $("status-badge").className = "status-running";
    $("status-badge").textContent = "RUNNING";
    $("trigger-btn").disabled = true;
    elapsedTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - runStart) / 1000);
      const m = String(Math.floor(sec / 60)).padStart(2, "0");
      const s = String(sec % 60).padStart(2, "0");
      $("elapsed").textContent = `⏱ ${m}:${s}`;
    }, 200);
  }

  function finishRun(data) {
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
    $("status-badge").className = "status-done";
    $("status-badge").textContent = "COMPLETE";
    $("trigger-btn").disabled = false;
    PANES.forEach((a) => {
      const led = ledEl(a);
      if (led && !led.classList.contains("error")) setLed(a, "done");
    });

    const elapsed = data.elapsed_ms ? (data.elapsed_ms / 1000).toFixed(1) + "s" : "";
    const pm = data.postmortem || "";
    $("postmortem-body").className = "populated";
    $("postmortem-body").textContent = pm + (elapsed ? `\n\n— ${elapsed} elapsed` : "");

    // Render dataset deep-links from any postmortem_written events
    const links = $("affected-datasets");
    links.innerHTML = "";
    document.querySelectorAll(".event-postmortem_written .event-content").forEach((el) => {
      const text = el.textContent || "";
      const m = text.match(/(olist_dirty\.main\.\w+)/);
      if (m) {
        const tableShort = m[1];
        const a = document.createElement("a");
        a.className = "dataset-link";
        a.href = `${DATAHUB_UI}/dataset/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Asqlite%2C${encodeURIComponent(tableShort)}%2CPROD%29/`;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = `→ ${tableShort} [open in DataHub]`;
        links.appendChild(a);
      }
    });

    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  // ─── Trigger button ──────────────────────────────────────────────────
  async function trigger() {
    const incident = $("incident-input").value.trim();
    if (!incident) return;
    const stub = $("stub-mode").checked;

    startRun();

    // Replay mode: fire canned events client-side, no backend call
    if (IS_REPLAY_MODE) {
      try {
        await runReplay();
      } finally {
        $("trigger-btn").disabled = false;
      }
      return;
    }

    try {
      const r = await fetch("/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident, stub }),
      });
      if (r.status === 409) {
        $("status-badge").className = "status-error";
        $("status-badge").textContent = "BUSY — RESET FIRST";
        $("trigger-btn").disabled = false;
        return;
      }
      if (!r.ok) throw new Error("trigger failed: " + r.status);
    } catch (e) {
      $("status-badge").className = "status-error";
      $("status-badge").textContent = "ERROR";
      $("postmortem-body").textContent = "Failed to start run: " + e.message;
      $("trigger-btn").disabled = false;
      return;
    }

    // Open SSE stream
    eventSource = new EventSource("/stream");
    eventSource.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data));
      } catch (err) {
        console.error("bad event", e.data, err);
      }
    };
    eventSource.onerror = (e) => {
      console.warn("SSE error/close", e);
    };
  }

  async function reset() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = null;
    PANES.forEach((a) => {
      paneBody(a).innerHTML = "";
      setLed(a, "idle");
      agentTokens[a] = 0;
      if (tokensEl(a)) tokensEl(a).textContent = "0 tok";
      if (costEl(a)) costEl(a).textContent = "$0.0000";
    });
    totalCost = 0;
    $("cost-counter").textContent = "💰 $0.0000";
    $("elapsed").textContent = "⏱ 00:00";
    $("postmortem-body").className = "empty";
    $("postmortem-body").textContent = "Awaiting incident…";
    $("affected-datasets").innerHTML = "";
    $("status-badge").className = "status-idle";
    $("status-badge").textContent = "IDLE";
    $("trigger-btn").disabled = false;
    // In replay mode there's no backend to call
    if (IS_REPLAY_MODE) return;
    try {
      await fetch("/reset", { method: "POST" });
    } catch (e) {
      console.error("reset failed", e);
    }
  }

  // ─── Replay-mode banner ──────────────────────────────────────────────
  function showReplayBanner() {
    if (!IS_REPLAY_MODE) return;
    const banner = document.createElement("div");
    banner.id = "replay-banner";
    banner.innerHTML = `
      <strong>📼 DEMO REPLAY MODE</strong> — This hosted version replays a canned sequence client-side.
      For the actual live backend running on Mac Mini hardware (real DataHub, real Nebius models), visit
      <a href="https://eliass-mac-mini.tail365038.ts.net:10001/" target="_blank" rel="noreferrer">the Tailscale Funnel URL</a>
      (availability depends on Mac Mini being online).
    `;
    document.body.insertBefore(banner, document.getElementById("topbar").nextSibling);
  }

  // ─── Wire up ─────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    loadFinetuneMetrics();
    showReplayBanner();
    $("trigger-btn").addEventListener("click", trigger);
    $("reset-btn").addEventListener("click", reset);
    $("incident-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") trigger();
    });
  });
})();
