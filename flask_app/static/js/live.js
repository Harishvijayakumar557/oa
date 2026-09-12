document.addEventListener("DOMContentLoaded", function () {
  const statusBadge = document.getElementById("esp32StatusBadge");
  const liveKneeChartCanvas = document.getElementById("liveKneeChart");
  const modeButtons = document.querySelectorAll(".mode-btn");
  const toggleSimBtn = document.getElementById("toggleSimBtn");

  const serverIpDisplay = document.getElementById("serverIpDisplay");
  const udpPortDisplay = document.getElementById("udpPortDisplay");
  const liveKneeAngle = document.getElementById("liveKneeAngle");
  const liveStepCount = document.getElementById("liveStepCount");
  const liveCadenceVal = document.getElementById("liveCadenceVal");
  const liveSourceVal = document.getElementById("liveSourceVal");
  const packetCountVal = document.getElementById("packetCountVal");
  const kneeStatusLabel = document.getElementById("kneeStatusLabel");

  let liveChart = null;
  let pollTimer = null;
  let isSimulating = false;

  // 1. Fetch Local Server IP & Wi-Fi Ingestion Details
  function loadWifiInfo() {
    fetch("/api/wifi-info")
      .then((res) => res.json())
      .then((data) => {
        if (serverIpDisplay) {
          serverIpDisplay.textContent = data.local_ip || "127.0.0.1";
        }
        if (udpPortDisplay) {
          udpPortDisplay.textContent = data.udp_port || 5005;
        }
      })
      .catch((err) => console.debug("Could not fetch Wi-Fi info:", err));
  }

  // 2. Update Status Indicator Badges
  function updateStatusIndicator(status, source, clientIp) {
    if (!statusBadge) return;
    if (status === "connected") {
      let sourceLabel = "Wi-Fi (UDP)";
      if (source === "wifi_http") sourceLabel = "Wi-Fi (HTTP)";
      else if (source === "simulation") sourceLabel = "Simulation";

      statusBadge.className = "badge bg-success text-white px-3 py-2 fs-6";
      statusBadge.innerHTML = `<i class="bi bi-wifi me-1"></i>Connected: ${sourceLabel}${clientIp ? ` (${clientIp})` : ""}`;
    } else {
      statusBadge.className = "badge bg-warning text-dark px-3 py-2 fs-6";
      statusBadge.innerHTML = `<i class="bi bi-arrow-repeat spin me-1"></i>Waiting for ESP32 Wi-Fi...`;
    }
  }

  // 3. Switch between LIVE (Wi-Fi) and DEMO (Manual)
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

  // 4. Initialize Smooth Real-Time Knee Flexion/Extension Chart
  function initKneeChart() {
    if (!liveKneeChartCanvas) return;
    const ctx = liveKneeChartCanvas.getContext("2d");
    liveChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: Array.from({ length: 30 }, (_, i) => i + 1),
        datasets: [
          {
            label: "Knee Angle (°)",
            data: Array.from({ length: 30 }, () => 50),
            borderColor: "#0d6efd",
            backgroundColor: "rgba(13, 110, 253, 0.08)",
            borderWidth: 2.5,
            tension: 0.35,
            fill: true,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
          y: {
            min: 15,
            max: 95,
            title: { display: true, text: "Degrees (°)" },
            grid: { color: "rgba(0,0,0,0.05)" },
          },
          x: {
            display: false,
          },
        },
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { boxWidth: 12 },
          },
        },
      },
    });
  }

  // 5. Update Waveform with Incoming Dynamic Angles
  function updateKneeWaveform(historyArray, currentVal) {
    if (!liveChart) return;
    const dataset = liveChart.data.datasets[0];
    if (Array.isArray(historyArray) && historyArray.length > 0) {
      dataset.data = historyArray;
    } else if (currentVal !== undefined) {
      dataset.data.push(Number(currentVal) || 50);
      if (dataset.data.length > 30) dataset.data.shift();
    }
    liveChart.data.labels = Array.from(
      { length: dataset.data.length },
      (_, i) => i + 1
    );
    liveChart.update("none");
  }

  // 6. Update Feature Inputs & Sliders
  function updateFeatureInputs(features) {
    if (!features || typeof features !== "object") return;
    const map = {
      gait_speed: { unit: "m/s", decimals: 2 },
      stride_time: { unit: "s", decimals: 2 },
      stride_length: { unit: "m", decimals: 2 },
      cadence: { unit: "steps/min", decimals: 0 },
      knee_rom: { unit: "°", decimals: 0 },
      step_time_std: { unit: "s", decimals: 3 },
    };

    Object.entries(map).forEach(([key, meta]) => {
      const input = document.getElementById(key);
      const output = document.getElementById(`${key}_value`);
      if (input && features[key] !== undefined) {
        input.value = features[key];
      }
      if (output && features[key] !== undefined) {
        output.textContent = `${Number(features[key]).toFixed(meta.decimals)} ${meta.unit}`;
      }
    });
  }

  // 7. Poll Real-Time Telemetry from Flask Ingestion Engine
  function pollLiveData() {
    fetch("/api/live-data")
      .then((res) => res.json())
      .then((data) => {
        const isConnected = data.status === "connected";
        updateStatusIndicator(data.status, data.source, data.client_ip);

        // Update live metrics cards
        if (liveKneeAngle && data.knee_angle !== undefined) {
          liveKneeAngle.textContent = `${Number(data.knee_angle).toFixed(1)} °`;
        }
        if (kneeStatusLabel && data.knee_angle !== undefined) {
          const deg = Number(data.knee_angle);
          if (deg < 35) kneeStatusLabel.textContent = "Extension / Stance";
          else if (deg > 60) kneeStatusLabel.textContent = "Peak Flexion / Swing";
          else kneeStatusLabel.textContent = "Mid-Swing Cycle";
        }

        if (liveStepCount && data.step_count !== undefined) {
          liveStepCount.textContent = data.step_count;
        }

        if (liveCadenceVal && data.features && data.features.cadence) {
          liveCadenceVal.textContent = Number(data.features.cadence).toFixed(0);
        }

        if (liveSourceVal) {
          if (data.source === "wifi_udp") liveSourceVal.textContent = "Wi-Fi (UDP)";
          else if (data.source === "wifi_http") liveSourceVal.textContent = "Wi-Fi (HTTP)";
          else if (data.source === "simulation") liveSourceVal.textContent = "Test Stream";
          else liveSourceVal.textContent = isConnected ? "Active" : "Awaiting";
        }

        if (packetCountVal && data.packets_received !== undefined) {
          packetCountVal.textContent = `${data.packets_received} samples`;
        }

        // Update continuous knee angle waveform
        if (data.knee_angle_history) {
          updateKneeWaveform(data.knee_angle_history, data.knee_angle);
        }

        // Update the 6 gait sliders automatically if connected
        if (isConnected && data.features) {
          updateFeatureInputs(data.features);
        }
      })
      .catch((err) => {
        console.debug("Telemetry polling issue:", err);
      });
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollLiveData();
    pollTimer = setInterval(pollLiveData, 280); // Fast 3.5 Hz refresh for smooth waveform
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  }

  // 8. Toggle Test Wi-Fi Simulation
  if (toggleSimBtn) {
    toggleSimBtn.addEventListener("click", function () {
      fetch("/api/simulation/toggle", { method: "POST" })
        .then((res) => res.json())
        .then((res) => {
          isSimulating = !!res.simulation;
          if (isSimulating) {
            toggleSimBtn.className = "btn btn-sm btn-danger";
            toggleSimBtn.innerHTML = '<i class="bi bi-stop-circle me-1"></i>Stop Test Stream';
          } else {
            toggleSimBtn.className = "btn btn-sm btn-outline-success";
            toggleSimBtn.innerHTML = '<i class="bi bi-play-circle me-1"></i>Test Wi-Fi Stream';
          }
        });
    });
  }

  // 9. Bind Mode Selector Buttons
  modeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      setMode(button.dataset.mode || "LIVE");
    });
  });

  // Initialize
  loadWifiInfo();
  initKneeChart();
  updateStatusIndicator("waiting");
  const defaultMode =
    document.querySelector(".mode-btn.active")?.dataset.mode || "LIVE";
  setMode(defaultMode);
});
