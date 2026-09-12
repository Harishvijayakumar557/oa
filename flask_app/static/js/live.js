document.addEventListener("DOMContentLoaded", function () {
  const connectBtn = document.getElementById("connectEsp32Btn");
  const disconnectBtn = document.getElementById("disconnectEsp32Btn");
  const statusBadge = document.getElementById("esp32StatusBadge");
  const liveKneeChartCanvas = document.getElementById("liveKneeChart");
  const modeButtons = document.querySelectorAll(".mode-btn");

  let liveChart = null;
  let pollTimer = null;

  function updateStatusIndicator(status) {
    if (!statusBadge) return;
    const labelMap = {
      connected: { text: "🟢 Connected", className: "status-badge low" },
      waiting: {
        text: "🟡 Waiting for ESP32",
        className: "status-badge neutral",
      },
      disconnected: { text: "🔴 Disconnected", className: "status-badge high" },
    };
    const choice = labelMap[status] || labelMap.waiting;
    statusBadge.className = choice.className;
    statusBadge.textContent = choice.text;
  }

  function setMode(mode) {
    const normalized = (mode || "LIVE").toUpperCase();
    modeButtons.forEach((button) => {
      const isActive = button.dataset.mode === normalized;
      button.classList.toggle("btn-primary", isActive);
      button.classList.toggle("btn-outline-primary", !isActive);
      button.classList.toggle("active", isActive);
    });

    const liveHelp = document.getElementById("liveModeHelp");
    const demoHelp = document.getElementById("demoModeHelp");
    if (liveHelp) liveHelp.classList.toggle("d-none", normalized !== "LIVE");
    if (demoHelp) demoHelp.classList.toggle("d-none", normalized !== "DEMO");

    if (connectBtn) {
      connectBtn.classList.toggle("d-none", normalized !== "LIVE");
    }
    if (disconnectBtn) {
      disconnectBtn.classList.toggle("d-none", normalized !== "LIVE");
    }

    const sampleBtn = document.getElementById("useSampleValuesBtn");
    if (sampleBtn) {
      sampleBtn.classList.toggle("d-none", normalized !== "DEMO");
    }

    if (normalized === "LIVE") {
      startPolling();
    } else {
      stopPolling();
      updateStatusIndicator("waiting");
    }
  }

  function initKneeChart() {
    if (!liveKneeChartCanvas) return;
    const ctx = liveKneeChartCanvas.getContext("2d");
    liveChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: Array.from({ length: 20 }, (_, i) => i),
        datasets: [
          {
            label: "Knee angle",
            data: Array.from({ length: 20 }, () => 55),
            borderColor: "#0d6efd",
            tension: 0.35,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: { y: { min: 0, max: 100 } },
      },
    });
  }

  function updateKneeChart(value) {
    if (!liveChart) return;
    const dataset = liveChart.data.datasets[0];
    dataset.data.push(Number(value) || 55);
    if (dataset.data.length > 20) dataset.data.shift();
    liveChart.data.labels = Array.from(
      { length: dataset.data.length },
      (_, i) => i,
    );
    liveChart.update();
  }

  function updateFeatureInputs(data) {
    const features = data && data.features ? data.features : {};
    const map = {
      gait_speed: "gait_speed",
      stride_time: "stride_time",
      stride_length: "stride_length",
      cadence: "cadence",
      knee_rom: "knee_rom",
      step_time_std: "step_time_std",
    };

    Object.entries(map).forEach(([key, id]) => {
      const input = document.getElementById(id);
      if (!input || features[key] === undefined) return;
      input.value = features[key];
      const output = document.getElementById(`${id}_value`);
      if (output) {
        if (
          id === "gait_speed" ||
          id === "stride_time" ||
          id === "stride_length"
        ) {
          const units = {
            gait_speed: "m/s",
            stride_time: "s",
            stride_length: "m",
          };
          output.textContent = `${Number(features[key]).toFixed(2)} ${units[id]}`;
        } else if (id === "cadence") {
          output.textContent = `${Number(features[key]).toFixed(0)} steps/min`;
        } else if (id === "knee_rom") {
          output.textContent = `${Number(features[key]).toFixed(0)} °`;
          updateKneeChart(features[key]);
        } else {
          output.textContent = `${Number(features[key]).toFixed(2)} s`;
        }
      }
    });
  }

  function pollLiveData() {
    fetch("/api/live-data")
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "connected" && data.features) {
          updateStatusIndicator("connected");
          updateFeatureInputs(data);
        } else if (data.status === "waiting") {
          updateStatusIndicator("waiting");
        } else {
          updateStatusIndicator("disconnected");
        }
      })
      .catch(() => updateStatusIndicator("disconnected"));
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollLiveData();
    pollTimer = setInterval(pollLiveData, 2000);
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  }

  function connectESP32() {
    fetch("/api/connect-esp32", { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "connected") {
          updateStatusIndicator("connected");
          if (disconnectBtn) disconnectBtn.classList.remove("d-none");
          if (connectBtn) connectBtn.classList.add("d-none");
          startPolling();
        } else {
          updateStatusIndicator("disconnected");
          if (disconnectBtn) disconnectBtn.classList.add("d-none");
          if (connectBtn) connectBtn.classList.remove("d-none");
          console.error(
            "ESP32 connection failed:",
            data.message || data.status,
          );
        }
      })
      .catch((error) => {
        updateStatusIndicator("disconnected");
        console.error("ESP32 connection error:", error);
      });
  }

  function disconnectESP32() {
    fetch("/api/disconnect-esp32", { method: "POST" })
      .then(() => {
        updateStatusIndicator("disconnected");
        stopPolling();
        if (disconnectBtn) disconnectBtn.classList.add("d-none");
        if (connectBtn) connectBtn.classList.remove("d-none");
      })
      .catch((error) => console.error("ESP32 disconnect error:", error));
  }

  modeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      setMode(button.dataset.mode || "LIVE");
    });
  });

  initKneeChart();
  updateStatusIndicator("waiting");
  const defaultMode =
    document.querySelector(".mode-btn.active")?.dataset.mode || "LIVE";
  setMode(defaultMode);

  if (connectBtn) connectBtn.addEventListener("click", connectESP32);
  if (disconnectBtn) disconnectBtn.addEventListener("click", disconnectESP32);
});
