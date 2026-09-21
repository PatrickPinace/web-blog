/* Podgląd wpisu w panelu: przełącznik "widok mobilny" zwężający treść
   do szerokości telefonu, bez fizycznego resize okna przeglądarki. */
(function () {
  var toggle = document.querySelector("[data-preview-mobile-toggle]");
  var main = document.querySelector("[data-preview-main]");
  if (!toggle || !main) return;

  toggle.addEventListener("click", function () {
    var active = main.classList.toggle("preview-mobile");
    toggle.classList.toggle("is-active", active);
    toggle.textContent = active ? "Widok desktopowy" : "Widok mobilny";
  });
})();
