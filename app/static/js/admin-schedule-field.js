/* Pole daty publikacji jest widoczne tylko przy statusie "Zaplanowany".
   Osobny plik zamiast atrybutu `onchange` — CSP ma script-src 'self'
   bez 'unsafe-inline'. */
(function () {
  document.addEventListener("change", function (event) {
    var targetId = event.target.getAttribute("data-schedule-toggle");
    if (!targetId) return;
    var field = document.getElementById(targetId);
    if (!field) return;
    field.hidden = event.target.value !== "scheduled";
  });
})();
