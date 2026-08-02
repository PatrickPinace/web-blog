/* web—blog · main.js — motyw, pasek postępu, wejścia, spis treści, podgląd wpisu */
(function () {
  var root = document.documentElement;

  /* --- motyw: prefers-color-scheme + ręczny przełącznik (zapamiętywany) --- */
  try {
    var saved = localStorage.getItem('wb-theme');
    if (saved) root.setAttribute('data-theme', saved);
  } catch (e) {}

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('[data-theme-toggle]');
    function label() {
      var dark = root.getAttribute('data-theme') === 'dark' ||
        (!root.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
      if (btn) btn.querySelector('[data-theme-label]').textContent = dark ? 'Jasny' : 'Ciemny';
      return dark;
    }
    if (btn) {
      label();
      btn.addEventListener('click', function () {
        var next = label() ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('wb-theme', next); } catch (e) {}
        label();
      });
    }

    /* --- pasek postępu czytania --- */
    var bar = document.querySelector('.progress');
    if (bar) {
      var update = function () {
        var max = root.scrollHeight - root.clientHeight;
        bar.style.width = (max > 0 ? (root.scrollTop / max) * 100 : 0) + '%';
      };
      window.addEventListener('scroll', update, { passive: true });
      window.addEventListener('resize', update);
      update();
    }

    /* --- wejścia przy scrollu (treść działa też bez JS) --- */
    var items = document.querySelectorAll('.reveal');
    if (items.length && 'IntersectionObserver' in window) {
      var vh = window.innerHeight, now = [], pending = [];
      Array.prototype.forEach.call(items, function (el, i) {
        if (el.getBoundingClientRect().top < vh * 0.92) {
          el.style.transitionDelay = Math.min(i, 8) * 45 + 'ms';
          now.push(el);
        } else pending.push(el);
      });
      document.body.classList.add('js-anim');
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { now.forEach(function (el) { el.classList.add('in'); }); });
      });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { rootMargin: '0px 0px -8% 0px' });
      pending.forEach(function (el) { io.observe(el); });
    }

    /* --- spis treści: aktywna sekcja + płynne przewijanie --- */
    var links = document.querySelectorAll('.toc a[href^="#"]');
    if (links.length && 'IntersectionObserver' in window) {
      var heads = [];
      Array.prototype.forEach.call(links, function (a) {
        var h = document.getElementById(a.getAttribute('href').slice(1));
        if (h) heads.push(h);
        a.addEventListener('click', function (ev) {
          var t = document.getElementById(a.getAttribute('href').slice(1));
          if (!t) return;
          ev.preventDefault();
          window.scrollTo({ top: t.getBoundingClientRect().top + window.scrollY - 100, behavior: 'smooth' });
        });
      });
      var tio = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          Array.prototype.forEach.call(links, function (a) {
            a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id);
          });
        });
      }, { rootMargin: '-100px 0px -65% 0px' });
      heads.forEach(function (h) { tio.observe(h); });
    }

    /* --- podgląd wpisu w kolumnie obok indeksu --- */
    var preview = document.querySelector('[data-preview]');
    if (preview) {
      var fields = {
        image: preview.querySelector('[data-preview-image]'),
        kind: preview.querySelector('[data-preview-kind]'),
        title: preview.querySelector('[data-preview-title]'),
        branch: preview.querySelector('[data-preview-branch]'),
        read: preview.querySelector('[data-preview-read]'),
        status: preview.querySelector('[data-preview-status]')
      };
      Array.prototype.forEach.call(document.querySelectorAll('.row'), function (row) {
        var fill = function () {
          Object.keys(fields).forEach(function (k) {
            if (fields[k] && row.dataset[k]) fields[k].textContent = row.dataset[k];
          });
        };
        row.addEventListener('mouseenter', fill);
        row.addEventListener('focus', fill);
      });
    }
  });
})();
