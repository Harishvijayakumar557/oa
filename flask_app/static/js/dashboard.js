document.addEventListener("DOMContentLoaded", function () {
  const dashboardElement = document.getElementById("dashboardData");
  if (!dashboardElement) return;

  const dashboard = JSON.parse(dashboardElement.textContent || "{}");

  const riskChartCtx = document.getElementById("riskDistributionChart");
  if (riskChartCtx) {
    new Chart(riskChartCtx.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: ["Low", "Moderate", "High"],
        datasets: [
          {
            data: [
              dashboard.risk_distribution?.low || 0,
              dashboard.risk_distribution?.moderate || 0,
              dashboard.risk_distribution?.high || 0,
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
            labels: {
              usePointStyle: true,
              boxWidth: 12,
              padding: 16,
            },
          },
        },
      },
    });
  }

  const weeklyChartCtx = document.getElementById("weeklyTrendChart");
  if (weeklyChartCtx) {
    const weeklyData = dashboard.weekly_trend || [];
    new Chart(weeklyChartCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: weeklyData.map((item) => item.label || "Day"),
        datasets: [
          {
            label: "Screenings",
            data: weeklyData.map((item) => item.value || 0),
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
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: 12 },
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            grid: { color: "rgba(15, 23, 42, 0.08)" },
          },
        },
      },
    });
  }
});
