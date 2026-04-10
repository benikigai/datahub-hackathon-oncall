// data-oncall dashboard — vanilla JS, no frameworks
(function () {
  const DATAHUB_UI = "http://100.114.31.63:9002";
  const PANES = ["coordinator", "detective", "reality_checker", "fixer"];
  const STATE_KEY = { idle: "idle", thinking: "thinking", querying: "querying", done: "done", error: "error" };

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
      $("ft-lora").textContent = `rank ${lc.rank} · α ${lc.alpha} · LR ${lc.lr} · ${lc.epochs}ep · ${lc.training_time_min}min`;

      $("bar-base").style.width = m.accuracy.base_pct + "%";
      $("bar-tuned").style.width = m.accuracy.fine_tuned_pct + "%";
      $("bar-base-pct").textContent = m.accuracy.base_pct + "%";
      $("bar-tuned-pct").textContent = m.accuracy.fine_tuned_pct + "%";
      $("bar-improvement").textContent = "+" + m.accuracy.improvement_pct + " points";

      $("sample-nl").textContent = m.sample_pair.nl;
      const code = $("sample-graphql");
      code.textContent = m.sample_pair.graphql;
      if (window.Prism) Prism.highlightElement(code);
    } catch (e) {
      console.error("Failed to load finetune_metrics.json", e);
    }
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
    try {
      await fetch("/reset", { method: "POST" });
    } catch (e) {
      console.error("reset failed", e);
    }
  }

  // ─── Wire up ─────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    loadFinetuneMetrics();
    $("trigger-btn").addEventListener("click", trigger);
    $("reset-btn").addEventListener("click", reset);
    $("incident-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") trigger();
    });
  });
})();
