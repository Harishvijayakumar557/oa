document.addEventListener("DOMContentLoaded", function () {
  const languageSelect = document.getElementById("languageSelect");
  if (!languageSelect) return;

  languageSelect.addEventListener("change", function () {
    const language = languageSelect.value;
    const url = new URL(window.location.href);
    url.searchParams.set("lang", language);
    window.location.href = url.toString();
  });
});
