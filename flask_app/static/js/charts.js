document.addEventListener("DOMContentLoaded", function () {
  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 500,
      easing: "easeOutCubic",
    },
    layout: {
      padding: {
        top: 12,
        right: 12,
        bottom: 12,
        left: 12,
      },
    },
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          usePointStyle: true,
          boxWidth: 12,
          padding: 16,
        },
      },
      tooltip: {
        mode: "index",
        intersect: false,
      },
    },
  };

  const riskChartCanvas = document.getElementById("riskChart");
  if (riskChartCanvas) {
    const ctx = riskChartCanvas.getContext("2d");
    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Low", "Moderate", "High"],
        datasets: [
          {
            data: [33, 33, 34],
            backgroundColor: ["#198754", "#ffc107", "#dc3545"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        ...baseOptions,
        cutout: "60%",
      },
    });
  }

  const contributionCanvas = document.getElementById(
    "featureContributionChart",
  );
  if (contributionCanvas) {
    const ctx = contributionCanvas.getContext("2d");
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["Speed", "Stride", "Cadence", "Knee ROM", "Std"],
        datasets: [
          {
            label: "Contribution",
            data: [20, 25, 18, 27, 10],
            backgroundColor: [
              "#0d6efd",
              "#4dabf7",
              "#74c0fc",
              "#a5d8ff",
              "#d0ebff",
            ],
            borderRadius: 8,
          },
        ],
      },
      options: {
        ...baseOptions,
        scales: {
          x: {
            grid: { display: false },
            ticks: { maxRotation: 0 },
          },
          y: {
            beginAtZero: true,
            grid: { color: "rgba(15, 23, 42, 0.08)" },
            ticks: { precision: 0 },
          },
        },
      },
    });
  }

  const kneeChartCanvas = document.getElementById("liveKneeChart");
  if (kneeChartCanvas) {
    const ctx = kneeChartCanvas.getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: ["1", "2", "3", "4", "5", "6", "7", "8"],
        datasets: [
          {
            label: "Knee angle",
            data: [42, 48, 55, 52, 58, 60, 56, 62],
            borderColor: "#0d6efd",
            backgroundColor: "rgba(13, 110, 253, 0.12)",
            borderWidth: 3,
            tension: 0.35,
            fill: true,
            pointRadius: 0,
          },
        ],
      },
      options: {
        ...baseOptions,
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: false,
            min: 30,
            max: 80,
            grid: { color: "rgba(15, 23, 42, 0.08)" },
          },
        },
      },
    });
  }

});
