/* Podpowiedzi tagów przy wpisywaniu, dla pola CSV "flask, case-study".
   Zwykły <input list="..."> podpowiada dla CAŁEJ wartości pola, nie dla
   ostatniego tokenu po przecinku — więc datalist wisi tu osobno na
   ukrytym polu, a JS przepisuje tylko ostatni token po wyborze. */
(function () {
  var input = document.querySelector("[data-tag-input]");
  var datalist = document.getElementById("existing-tags");
  if (!input || !datalist) return;

  var shadow = document.createElement("input");
  shadow.setAttribute("list", "existing-tags");
  shadow.style.cssText = "position:absolute;opacity:0;pointer-events:none;width:1px;height:1px";
  input.insertAdjacentElement("afterend", shadow);

  function lastToken() {
    var parts = input.value.split(",");
    return parts[parts.length - 1].trim();
  }

  input.addEventListener("input", function () {
    shadow.value = lastToken();
  });

  shadow.addEventListener("input", function () {
    var options = datalist.querySelectorAll("option");
    var matched = false;
    for (var i = 0; i < options.length; i++) {
      if (options[i].value === shadow.value) {
        matched = true;
        break;
      }
    }
    if (!matched) return;

    var parts = input.value.split(",");
    parts[parts.length - 1] = " " + shadow.value;
    input.value = parts.join(",").replace(/^\s+/, "") + ", ";
    shadow.value = "";
    input.focus();
  });
})();
