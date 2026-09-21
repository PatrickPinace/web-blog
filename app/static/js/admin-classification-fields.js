/* Branża i projekt koncepcyjny dotyczą realizacji. Bez JavaScriptu są
   widoczne; z JS blok jest tylko zwijany, nigdy czyszczony ani disabled. */
(function () {
  var form = document.querySelector("form[data-dirty-guard]");
  if (!form) return;

  var kind = form.querySelector('[name="kind"]');
  var fields = form.querySelector("[data-case-study-fields]");
  var branch = form.querySelector('[name="branch"]');
  var concept = form.querySelector('[name="is_concept"]');
  var retained = form.querySelector("[data-classification-retained]");
  if (!kind || !fields || !branch || !concept || !retained) return;

  function hasClassification() {
    return Boolean(branch.value.trim() || concept.checked);
  }

  function sync() {
    var isCaseStudy = kind.value === "realizacja";
    fields.hidden = !isCaseStudy;
    retained.hidden = isCaseStudy || !hasClassification();
  }

  kind.addEventListener("change", sync);
  branch.addEventListener("input", sync);
  concept.addEventListener("change", sync);
  sync();
})();
