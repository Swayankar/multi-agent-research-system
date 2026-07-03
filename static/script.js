const STEP_ORDER = ["search", "scrape", "write", "critique"];
const MARKDOWN_STEPS = new Set(["write", "critique"]);

const form = document.getElementById("topic-form");
const input = document.getElementById("topic-input");
const runBtn = document.getElementById("run-btn");
const errorBanner = document.getElementById("error-banner");
const traceProgress = document.getElementById("trace-progress");
const resultSection = document.getElementById("result");
const reportText = document.getElementById("report-text");
const feedbackText = document.getElementById("feedback-text");

const timers = {};

function statusItemEl(step) {
  return document.querySelector(`.status-item[data-step="${step}"]`);
}

function accordionEl(step) {
  return document.querySelector(`.accordion-item[data-step="${step}"]`);
}

function renderMarkdown(target, raw) {
  const html = window.marked ? window.marked.parse(raw || "") : (raw || "");
  target.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(html) : html;
}

function formatElapsed(seconds) {
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function startTimer(step) {
  stopTimer(step);
  const startedAt = Date.now();
  const timerEl = statusItemEl(step).querySelector('[data-role="timer"]');
  timerEl.textContent = "0s";
  const intervalId = setInterval(() => {
    timerEl.textContent = formatElapsed(Math.floor((Date.now() - startedAt) / 1000));
  }, 1000);
  timers[step] = { intervalId, startedAt };
}

function stopTimer(step) {
  if (timers[step]) {
    clearInterval(timers[step].intervalId);
  }
}

function finalizeTimer(step) {
  const timerEl = statusItemEl(step).querySelector('[data-role="timer"]');
  if (timers[step]) {
    const total = Math.floor((Date.now() - timers[step].startedAt) / 1000);
    timerEl.textContent = formatElapsed(total);
    clearInterval(timers[step].intervalId);
  }
}

function updateProgress() {
  const doneCount = STEP_ORDER.filter((s) => statusItemEl(s).classList.contains("done")).length;
  traceProgress.textContent = `${doneCount} / ${STEP_ORDER.length} complete`;
  traceProgress.classList.toggle("in-progress", doneCount > 0 && doneCount < STEP_ORDER.length);
  traceProgress.classList.toggle("all-done", doneCount === STEP_ORDER.length);
}

function resetUI() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
  resultSection.classList.add("hidden");
  reportText.innerHTML = "";
  feedbackText.innerHTML = "";

  STEP_ORDER.forEach((step) => {
    stopTimer(step);

    const statusEl = statusItemEl(step);
    statusEl.classList.remove("running", "done");
    statusEl.querySelector('[data-role="status"]').textContent = "Waiting";
    statusEl.querySelector('[data-role="timer"]').textContent = "";

    const accEl = accordionEl(step);
    accEl.classList.remove("done", "expanded");
    accEl.querySelector('[data-role="astate"]').textContent = "Not started";
    const toggle = accEl.querySelector('[data-role="toggle"]');
    toggle.disabled = true;
    toggle.onclick = null;
    const output = accEl.querySelector('[data-role="output"]');
    output.classList.add("hidden");
    output.innerHTML = "";
  });

  updateProgress();
}

function setStepRunning(step) {
  const statusEl = statusItemEl(step);
  statusEl.classList.add("running");
  statusEl.classList.remove("done");
  statusEl.querySelector('[data-role="status"]').textContent = "Running";
  startTimer(step);

  accordionEl(step).querySelector('[data-role="astate"]').textContent = "Running…";
}

function setStepDone(step, data) {
  const statusEl = statusItemEl(step);
  statusEl.classList.remove("running");
  statusEl.classList.add("done");
  statusEl.querySelector('[data-role="status"]').textContent = "Done";
  finalizeTimer(step);

  const accEl = accordionEl(step);
  const toggle = accEl.querySelector('[data-role="toggle"]');
  const output = accEl.querySelector('[data-role="output"]');
  const stateLabel = accEl.querySelector('[data-role="astate"]');

  if (data) {
    accEl.classList.add("done");
    stateLabel.textContent = "Done";
    toggle.disabled = false;

    if (MARKDOWN_STEPS.has(step)) {
      renderMarkdown(output, data);
    } else {
      output.textContent = data;
    }

    toggle.onclick = () => {
      const isHidden = output.classList.contains("hidden");
      output.classList.toggle("hidden");
      accEl.classList.toggle("expanded", isHidden);
    };
  } else {
    stateLabel.textContent = "No output";
  }

  updateProgress();
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
  runBtn.disabled = false;
  input.disabled = false;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const topic = input.value.trim();
  if (!topic) return;

  resetUI();
  runBtn.disabled = true;
  input.disabled = true;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/research`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ topic }));
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "step") {
      if (msg.status === "running") {
        setStepRunning(msg.step);
      } else if (msg.status === "done") {
        setStepDone(msg.step, msg.data);
      }
    } else if (msg.type === "complete") {
      renderMarkdown(reportText, msg.report || "");
      renderMarkdown(feedbackText, msg.feedback || "");
      resultSection.classList.remove("hidden");
      runBtn.disabled = false;
      input.disabled = false;
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (msg.type === "error") {
      showError(msg.message || "Something went wrong while running the pipeline.");
    }
  };

  ws.onerror = () => {
    showError("Connection error. Check that the server is running.");
  };

  ws.onclose = () => {
    runBtn.disabled = false;
    input.disabled = false;
  };
});

updateProgress();