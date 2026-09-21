/* Podpowiedzi wyników na /szukaj podczas wpisywania, z debounce i fetchem
   do /szukaj/live. Zwykły submit formularza (pełna lista wyników) działa
   jak dotąd — to tylko dodatkowa warstwa nad nim. */
(function () {
  var input = document.querySelector("[data-live-search-input]");
  var list = document.querySelector("[data-live-search-results]");
  if (!input || !list) return;

  var DEBOUNCE_MS = 200;
  var timer = null;
  var activeController = null;

  function hide() {
    list.hidden = true;
    list.innerHTML = "";
  }

  function render(results) {
    if (!results.length) {
      hide();
      return;
    }
    list.innerHTML = "";
    results.forEach(function (item) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = item.url;
      var title = document.createElement("span");
      title.className = "title";
      title.textContent = item.title;
      a.appendChild(title);
      if (item.excerpt) {
        var excerpt = document.createElement("span");
        excerpt.className = "excerpt";
        excerpt.textContent = item.excerpt;
        a.appendChild(excerpt);
      }
      li.appendChild(a);
      list.appendChild(li);
    });
    list.hidden = false;
  }

  input.addEventListener("input", function () {
    var query = input.value.trim();
    if (timer) clearTimeout(timer);
    if (activeController) activeController.abort();

    if (!query) {
      hide();
      return;
    }

    timer = setTimeout(function () {
      activeController = new AbortController();
      fetch("/szukaj/live?q=" + encodeURIComponent(query), { signal: activeController.signal })
        .then(function (response) { return response.json(); })
        .then(function (data) { render(data.results || []); })
        .catch(function (error) {
          if (error.name !== "AbortError") hide();
        });
    }, DEBOUNCE_MS);
  });

  input.addEventListener("blur", function () {
    setTimeout(hide, 150);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") hide();
  });
})();
