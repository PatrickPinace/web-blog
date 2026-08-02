/* Potwierdzenie przed wysłaniem formularza usuwania.
   Osobny plik, nie atrybut `onsubmit` — CSP ma script-src 'self' bez
   'unsafe-inline', więc skrypt w atrybucie nigdy by się nie wykonał
   i usuwanie działałoby bez pytania. */
(function () {
  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  document.addEventListener("change", function (event) {
    var exclusiveWith = event.target.getAttribute("data-exclusive-with");
    if (exclusiveWith) {
      var sibling = event.target.form.elements[exclusiveWith];
      if (sibling) sibling.value = "";
      event.target.form.requestSubmit();
      return;
    }
    var form = event.target.closest("[data-submit-on-change]");
    if (form) {
      form.requestSubmit();
    }
  });
})();
