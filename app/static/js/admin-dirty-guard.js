/* Ostrzeżenie przed wyjściem z formularza wpisu z niezapisanymi zmianami.
   Quill nie jest zwykłym polem formularza — synchronizuje się do #id_body_source
   dopiero przy "text-change" (patrz admin-editor.js), więc serializacja
   FormData tuż przed porównaniem zawsze widzi jego aktualny stan. */
(function () {
  var form = document.querySelector("form[data-dirty-guard]");
  if (!form) return;

  function snapshot() {
    return new URLSearchParams(new FormData(form)).toString();
  }

  var baseline = snapshot();
  var submitting = false;

  form.addEventListener("submit", function () {
    submitting = true;
  });

  window.addEventListener("beforeunload", function (event) {
    if (submitting || snapshot() === baseline) return;
    event.preventDefault();
    event.returnValue = "";
  });
})();
