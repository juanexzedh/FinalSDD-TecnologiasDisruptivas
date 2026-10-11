// JavaScript mínimo del Incremento 1: la interacción sin recarga (HU-15) llega en el Incremento 5.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[action$='/logout']").forEach((f) => {
    f.addEventListener("submit", () => {});
  });
});
