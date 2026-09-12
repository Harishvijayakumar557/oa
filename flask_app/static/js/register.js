document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("registerForm");
  const progressBar = document.getElementById("formProgressBar");
  const prevBtn = document.getElementById("prevStepBtn");
  const nextBtn = document.getElementById("nextStepBtn");
  const submitBtn = document.getElementById("submitBtn");
  const steps = Array.from(document.querySelectorAll(".form-step"));
  const stepDots = Array.from(
    document.querySelectorAll("[data-step-indicator]"),
  );
  const painRange = document.getElementById("painLevelRange");
  const painValue = document.getElementById("painLevelValue");

  if (!form) return;

  let currentStep = 0;

  function syncPainValue() {
    if (!painRange || !painValue) return;
    painValue.textContent = `${painRange.value} / 10`;
  }

  function updateReviewSummary() {
    const name = form.querySelector('[name="name"]')?.value || "Not provided";
    const age = form.querySelector('[name="age"]')?.value || "N/A";
    const gender = form.querySelector('[name="gender"]')?.value || "N/A";
    const phone = form.querySelector('[name="phone"]')?.value || "N/A";
    const email = form.querySelector('[name="email"]')?.value || "N/A";
    const mobility =
      form.querySelector('[name="mobility"]')?.value || "Not specified";
    const pain = form.querySelector('[name="pain_level"]')?.value || "5";

    const reviewName = document.getElementById("reviewName");
    const reviewAgeGender = document.getElementById("reviewAgeGender");
    const reviewContact = document.getElementById("reviewContact");
    const reviewPain = document.getElementById("reviewPain");
    const reviewMobility = document.getElementById("reviewMobility");

    if (reviewName) reviewName.textContent = name;
    if (reviewAgeGender) reviewAgeGender.textContent = `${age} / ${gender}`;
    if (reviewContact)
      reviewContact.textContent =
        phone === "N/A" ? email : `${phone} / ${email}`;
    if (reviewPain) reviewPain.textContent = `${pain}/10`;
    if (reviewMobility) reviewMobility.textContent = mobility;
  }

  function renderStep() {
    steps.forEach((step, index) => {
      step.classList.toggle("active", index === currentStep);
      step.classList.toggle("d-none", index !== currentStep);
    });

    stepDots.forEach((dot, index) => {
      dot.classList.toggle("active", index === currentStep);
      dot.classList.toggle("done", index < currentStep);
    });

    const progress = ((currentStep + 1) / steps.length) * 100;
    if (progressBar) progressBar.style.width = `${progress}%`;

    prevBtn.classList.toggle("d-none", currentStep === 0);
    nextBtn.classList.toggle("d-none", currentStep === steps.length - 1);
    submitBtn.classList.toggle("d-none", currentStep !== steps.length - 1);

    if (currentStep === steps.length - 1) {
      updateReviewSummary();
    }
  }

  nextBtn?.addEventListener("click", function () {
    const activeStep = steps[currentStep];
    const requiredFields = activeStep.querySelectorAll("[required]");
    let valid = true;

    requiredFields.forEach((field) => {
      if (!field.value.trim()) {
        valid = false;
        field.classList.add("is-invalid");
      } else {
        field.classList.remove("is-invalid");
      }
    });

    if (!valid) return;

    currentStep = Math.min(currentStep + 1, steps.length - 1);
    renderStep();
  });

  prevBtn?.addEventListener("click", function () {
    currentStep = Math.max(currentStep - 1, 0);
    renderStep();
  });

  painRange?.addEventListener("input", function () {
    syncPainValue();
    updateReviewSummary();
  });

  form.querySelectorAll("input, select, textarea").forEach((field) => {
    field.addEventListener("input", updateReviewSummary);
    field.addEventListener("change", updateReviewSummary);
  });

  syncPainValue();
  renderStep();
});
