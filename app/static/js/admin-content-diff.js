/* Panel "Co zmieniłem?" — porównanie bieżącej treści w edytorze z zapisaną
   wersją (initial-content), po stronie klienta, bez wysyłania niczego na
   serwer. To NIE jest wersjonowanie — nie zapisuje historii, tylko pokazuje
   różnicę względem tego, co jest teraz w formularzu, żeby autor zobaczył
   swoje zmiany przed submitem. Diff słowo-po-słowie, LCS na tekście bez
   znaczników HTML (sama treść, nie markup). */
(function () {
  var button = document.querySelector("[data-show-diff]");
  var panel = document.querySelector("[data-diff-panel]");
  var body = document.querySelector("[data-diff-body]");
  var closeButton = document.querySelector("[data-diff-close]");
  var initial = document.getElementById("initial-content");
  var hidden = document.getElementById("editor-root") &&
    document.getElementById(document.getElementById("editor-root").dataset.targetField);
  if (!button || !panel || !body || !initial || !hidden) return;

  function stripTags(html) {
    // Wstawia spację na granicy każdego tagu blokowego, żeby "koniec
    // jednego akapitu" i "początek następnego" nie zlepiły się w jedno
    // słowo — textContent sam z siebie nie dodaje separatora tam, gdzie
    // w renderze byłby nowy wiersz.
    var withBreaks = (html || "").replace(/<\/(p|h[1-6]|li|blockquote|div|tr|td|th)>/gi, " $&");
    var div = document.createElement("div");
    div.innerHTML = withBreaks;
    return (div.textContent || "").replace(/\s+/g, " ").trim();
  }

  function tokenize(text) {
    return text.length ? text.split(" ") : [];
  }

  // Najdłuższy wspólny podciąg tokenów — tablica DP, standardowy algorytm.
  // Wpisy tej długości (setki/tysiące słów) trzymają O(n*m) w rozsądnym
  // czasie; dla znacznie dłuższych treści warto by przejść na diff blokowy.
  function diffWords(a, b) {
    var n = a.length, m = b.length;
    var dp = new Array(n + 1);
    for (var i = 0; i <= n; i++) dp[i] = new Array(m + 1).fill(0);
    for (i = 1; i <= n; i++) {
      for (var j = 1; j <= m; j++) {
        dp[i][j] = a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }

    var ops = [];
    i = n; var jj = m;
    while (i > 0 || jj > 0) {
      if (i > 0 && jj > 0 && a[i - 1] === b[jj - 1]) {
        ops.push({ type: "same", word: a[i - 1] });
        i--; jj--;
      } else if (jj > 0 && (i === 0 || dp[i][jj - 1] >= dp[i - 1][jj])) {
        ops.push({ type: "added", word: b[jj - 1] });
        jj--;
      } else {
        ops.push({ type: "removed", word: a[i - 1] });
        i--;
      }
    }
    return ops.reverse();
  }

  function render() {
    var before = tokenize(stripTags(initial.value));
    var after = tokenize(stripTags(hidden.value));

    if (before.join(" ") === after.join(" ")) {
      body.innerHTML = "<p class=\"diff-empty\">Treść bez zmian od ostatniego zapisu.</p>";
      return;
    }

    var ops = diffWords(before, after);
    var html = ops.map(function (op) {
      var word = op.word.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      if (op.type === "added") return '<ins>' + word + '</ins>';
      if (op.type === "removed") return '<del>' + word + '</del>';
      return word;
    }).join(" ");
    body.innerHTML = "<p>" + html + "</p>";
  }

  button.addEventListener("click", function () {
    render();
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  closeButton.addEventListener("click", function () {
    panel.hidden = true;
  });
})();
