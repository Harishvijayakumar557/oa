document.addEventListener("DOMContentLoaded", function () {
  const analyzeBtn =
    document.getElementById("analyzeRiskBtn") ||
    document.getElementById("analyzeBtn");
  const riskBadge = document.getElementById("riskBadge");
  const confidenceValue = document.getElementById("confidenceValue");
  const riskText = document.getElementById("riskText");
  const featureSummary = document.getElementById("featureSummary");
  const patientIdElement = document.getElementById("patientId");

  const sliderIds = [
    "gait_speed",
    "stride_time",
    "stride_length",
    "cadence",
    "knee_rom",
    "step_time_std",
  ];

  const normalRanges = {
    gait_speed: { unit: "m/s", min: 1.2, max: 1.4 },
    stride_time: { unit: "s", min: 1.0, max: 1.1 },
    stride_length: { unit: "m", min: 1.25, max: 1.45 },
    cadence: { unit: "steps/min", min: 110, max: 120 },
    knee_rom: { unit: "°", min: 55, max: 65 },
    step_time_std: { unit: "s", min: 0.02, max: 0.04 },
  };

  function formatValue(name, value) {
    const fmt = normalRanges[name] || { unit: "" };
    if (
      name === "step_time_std" ||
      name === "gait_speed" ||
      name === "stride_time" ||
      name === "stride_length"
    ) {
      return `${Number(value).toFixed(2)} ${fmt.unit}`;
    }
    return `${Number(value).toFixed(0)} ${fmt.unit}`;
  }

  function syncRangeLabels() {
    sliderIds.forEach((name) => {
      const input = document.getElementById(name);
      const output = document.getElementById(`${name}_value`);
      if (!input || !output) return;
      output.textContent = formatValue(name, input.value);
    });
  }

  function getCurrentMode() {
    const activeMode = document.querySelector(".mode-btn.active");
    return activeMode ? activeMode.dataset.mode : "LIVE";
  }

  function getCurrentFeatures() {
    return {
      gait_speed: Number(document.getElementById("gait_speed").value),
      stride_time: Number(document.getElementById("stride_time").value),
      stride_length: Number(document.getElementById("stride_length").value),
      cadence: Number(document.getElementById("cadence").value),
      knee_rom: Number(document.getElementById("knee_rom").value),
      step_time_std: Number(document.getElementById("step_time_std").value),
    };
  }

  function setSampleValues() {
    const values = {
      gait_speed: 1.25,
      stride_time: 1.1,
      stride_length: 1.3,
      cadence: 110,
      knee_rom: 55,
      step_time_std: 0.05,
    };

    Object.entries(values).forEach(([key, value]) => {
      const input = document.getElementById(key);
      if (!input) return;
      input.value = value;
    });
    syncRangeLabels();
  }

  sliderIds.forEach((name) => {
    const input = document.getElementById(name);
    if (!input) return;
    input.addEventListener("input", syncRangeLabels);
  });

  function renderFeatureCards(features) {
    if (!features || !Array.isArray(features)) return;

    featureSummary.innerHTML = features
      .map((feature) => {
        const status = feature.status === "normal" ? "Normal" : "Abnormal";
        const percentage = Math.min(
          100,
          Math.max(
            8,
            feature.deviation_percent > 0 ? feature.deviation_percent * 2 : 25,
          ),
        );
        const progress =
          feature.status === "normal" ? 100 : Math.min(100, percentage);
        const statusClass =
          feature.status === "normal"
            ? "feature-status normal"
            : "feature-status abnormal";
        const note = feature.clinical_note || "No clinical note available.";
        return `
          <div class="feature-widget">
            <div class="feature-widget-top">
              <div>
                <div class="feature-label">${feature.label}</div>
                <div class="feature-measured">${feature.value} ${feature.unit}</div>
              </div>
              <span class="${statusClass}">${status}</span>
            </div>
            <div class="feature-range-row"><span>Normal: ${feature.normal_range}</span></div>
            <div class="progress feature-progress" aria-label="${feature.label} progress">
              <div class="progress-bar ${feature.status === "normal" ? "bg-success" : "bg-warning"}" role="progressbar" style="width: ${progress}%"></div>
            </div>
            <small class="feature-note">${note}</small>
          </div>
        `;
      })
      .join("");
  }

  function updateRiskDisplay(label, confidence, probabilities, className) {
    if (riskBadge) {
      riskBadge.className = `status-badge ${className}`;
      riskBadge.textContent = label;
    }
    if (riskText) riskText.textContent = label;
    if (confidenceValue)
      confidenceValue.textContent = `${Number((confidence || 0) * 100).toFixed(1)}%`;

    if (window.riskChartInstance) {
      window.riskChartInstance.destroy();
    }

    const riskCanvas = document.getElementById("riskChart");
    if (!riskCanvas) return;
    const ctx = riskCanvas.getContext("2d");
    window.riskChartInstance = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Low", "Moderate", "High"],
        datasets: [
          {
            data: [
              Number(probabilities.low || 0),
              Number(probabilities.moderate || 0),
              Number(probabilities.high || 0),
            ],
            backgroundColor: ["#198754", "#ffc107", "#dc3545"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        layout: { padding: 12 },
        plugins: {
          legend: {
            position: "bottom",
            labels: { usePointStyle: true, boxWidth: 12, padding: 16 },
          },
        },
      },
    });
  }

  window.analyzeRisk = async function () {
    const payload = {
      mode: getCurrentMode(),
      patient_id: patientIdElement ? patientIdElement.value : null,
      features: getCurrentFeatures(),
    };

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      if (!response.ok) {
        const message =
          result && result.error
            ? result.error
            : "Unable to process prediction.";
        if (riskBadge) {
          riskBadge.className = "status-badge high";
          riskBadge.textContent = "Prediction failed";
        }
        if (riskText) riskText.textContent = "Prediction failed";
        if (confidenceValue) confidenceValue.textContent = "N/A";
        if (featureSummary)
          featureSummary.innerHTML = `<p class="text-danger mb-0">${message}</p>`;
        return;
      }

      const prediction = result.prediction || {};
      const probabilities = prediction.probabilities || {
        low: 0.33,
        moderate: 0.33,
        high: 0.34,
      };
      const label = prediction.label || "Unknown";
      const riskKey = label.toLowerCase().includes("low")
        ? "low"
        : label.toLowerCase().includes("moderate")
          ? "moderate"
          : label.toLowerCase().includes("high")
            ? "high"
            : "neutral";
      updateRiskDisplay(
        label,
        Number(prediction.confidence || 0),
        probabilities,
        riskKey,
      );
      renderFeatureCards(result.feature_analysis || []);

      if (result.redirect_url) {
        window.location.href = result.redirect_url;
      }
    } catch (error) {
      if (riskBadge) {
        riskBadge.className = "status-badge high";
        riskBadge.textContent = "Error";
      }
      if (riskText) riskText.textContent = "Error";
      if (confidenceValue) confidenceValue.textContent = "N/A";
      if (featureSummary)
        featureSummary.innerHTML =
          '<p class="text-danger mb-0">Unable to connect to the prediction API.</p>';
    }
  };

  if (analyzeBtn) {
    analyzeBtn.addEventListener("click", window.analyzeRisk);
  }

  const sampleBtn = document.getElementById("useSampleValuesBtn");
  if (sampleBtn) {
    sampleBtn.addEventListener("click", setSampleValues);
  }

  syncRangeLabels();
  setSampleValues();
});
