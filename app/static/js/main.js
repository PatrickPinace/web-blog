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

      /* Krótka ostatnia sekcja może nigdy nie przekroczyć progu -65% od
         dołu, więc scrollspy potrafi utknąć na przedostatnim linku mimo
         dojechania do końca strony — przy samym dole wymuszamy ostatni. */
      var lastLink = links[links.length - 1];
      var atBottom = function () {
        return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      };
      window.addEventListener('scroll', function () {
        if (!atBottom()) return;
        Array.prototype.forEach.call(links, function (a) {
          a.classList.toggle('active', a === lastLink);
        });
      }, { passive: true });
    }

    /* --- filtr tagów na żywo (/tagi), z fuzzy fallbackiem na literówkę ---
       Ten sam dwuetapowy algorytm co app/utils/search.py (dokładny podciąg,
       a dopiero gdy to da zero wyników — podobieństwo trigramowe), przepisany
       na JS, bo tu działa w locie po już wyrenderowanej liście, bez okrążenia
       przez serwer. Próg i minimalna długość tokenu takie same jak w Pythonie,
       żeby zachowanie było przewidywalne względem /szukaj. */
    var tagInput = document.querySelector('[data-tag-filter]');
    if (tagInput) {
      var PL_MAP = { 'ą':'a','ć':'c','ę':'e','ł':'l','ń':'n','ó':'o','ś':'s','ź':'z','ż':'z' };
      var normalize = function (s) {
        s = s.toLowerCase().replace(/[ąćęłńóśźż]/g, function (c) { return PL_MAP[c]; });
        return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
      };
      var trigrams = function (s) {
        if (s.length < 3) return [s];
        var padded = '  ' + s + ' ', out = [];
        for (var i = 0; i < padded.length - 2; i++) out.push(padded.slice(i, i + 3));
        return out;
      };
      var trigramSimilarity = function (a, b) {
        if (!a || !b) return 0;
        if (a.length < 2 || b.length < 2) return a === b ? 1 : 0;
        var ta = trigrams(a), tb = trigrams(b);
        var setA = {}; ta.forEach(function (t) { setA[t] = true; });
        var union = {}; ta.forEach(function (t) { union[t] = true; }); tb.forEach(function (t) { union[t] = true; });
        var inter = 0;
        tb.forEach(function (t) { if (setA[t]) inter++; });
        var unionSize = Object.keys(union).length;
        return unionSize ? inter / unionSize : 0;
      };

      var FUZZY_THRESHOLD = 0.3, MIN_FUZZY_LEN = 4;
      var cloud = document.querySelector('[data-tag-cloud]');
      var emptyMsg = document.querySelector('[data-tag-filter-empty]');
      var links = Array.prototype.slice.call(cloud.querySelectorAll('a'));
      var entries = links.map(function (a) {
        return { el: a, normalized: normalize(a.dataset.tagName || a.textContent) };
      });

      var applyFilter = function () {
        var query = normalize(tagInput.value.trim());
        if (!query) {
          entries.forEach(function (e) { e.el.hidden = false; });
          emptyMsg.hidden = true;
          return;
        }

        var exact = entries.filter(function (e) { return e.normalized.indexOf(query) !== -1; });
        var visible = exact;

        if (!visible.length && query.length >= MIN_FUZZY_LEN) {
          visible = entries.filter(function (e) {
            return trigramSimilarity(query, e.normalized) >= FUZZY_THRESHOLD;
          });
        }

        entries.forEach(function (e) { e.el.hidden = true; });
        visible.forEach(function (e) { e.el.hidden = false; });
        emptyMsg.hidden = visible.length > 0;
      };

      tagInput.addEventListener('input', applyFilter);
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
