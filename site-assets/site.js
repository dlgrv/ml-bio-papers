(function () {
  var themeBtn = document.getElementById("theme");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var dark = !document.documentElement.classList.contains("dark");
      document.documentElement.classList.toggle("dark", dark);
      try {
        localStorage.setItem("theme", dark ? "dark" : "light");
      } catch (e) {}
    });
  }

  var lang = document.getElementById("lang");
  if (lang) {
    lang.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-lang]");
      if (!btn) return;
      e.preventDefault();
      lang.removeAttribute("open");
    });
  }

  /* Hide topbar on scroll down only on phone (not desktop/tablet). */
  {
    var phone = matchMedia("(max-width: 767px)");
    var reduce = matchMedia("(prefers-reduced-motion: reduce)");
    var lastY = scrollY;
    var ticking = false;
    var showNav = function () {
      document.documentElement.classList.remove("nav-hidden");
    };
    addEventListener(
      "scroll",
      function () {
        if (!phone.matches || reduce.matches) {
          showNav();
          return;
        }
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
          var y = scrollY;
          var dy = y - lastY;
          if (y < 12) showNav();
          else if (dy > 6) document.documentElement.classList.add("nav-hidden");
          else if (dy < -6) showNav();
          lastY = y;
          ticking = false;
        });
      },
      { passive: true }
    );
    phone.addEventListener("change", function () {
      if (!phone.matches) showNav();
    });
  }

  var input = document.getElementById("q");
  var results = document.getElementById("search-results");
  if (!input || !results) return;

  var script = document.querySelector('script[src$="site.js"]');
  var base = script ? script.src.replace(/site\.js(?:\?.*)?$/, "") : "static/";
  var home = base.replace(/static\/?$/, "") || "./";
  var papers = [];
  var ready = fetch(base + "search.json")
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      papers = data || [];
    })
    .catch(function () {
      papers = [];
    });

  function hrefFor(slug) {
    return home + slug + "/";
  }

  function match(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    return papers.filter(function (p) {
      return [p.title_ru, p.title, p.authors, String(p.year), p.slug]
        .concat(p.topics || [])
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }

  function filterIndex(q) {
    var list = document.querySelectorAll(".blog-index > li[data-slug]");
    if (!list.length) return;
    var shown = new Set(
      match(q).map(function (p) {
        return p.slug;
      })
    );
    var empty = !q.trim();
    list.forEach(function (li) {
      li.hidden = !(empty || shown.has(li.getAttribute("data-slug")));
    });
  }

  function renderDropdown(hits) {
    if (!hits.length) {
      results.hidden = true;
      results.innerHTML = "";
      return;
    }
    results.innerHTML = hits
      .slice(0, 8)
      .map(function (p) {
        return (
          '<a class="search-hit" href="' +
          hrefFor(p.slug) +
          '"><b>' +
          escapeHtml(p.title_ru) +
          "</b><span>" +
          escapeHtml(String(p.year || "")) +
          "</span></a>"
        );
      })
      .join("");
    results.hidden = false;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function apply() {
    var q = input.value;
    filterIndex(q);
    renderDropdown(match(q));
  }

  ready.then(function () {
    var params = new URLSearchParams(location.search);
    if (params.get("q")) {
      input.value = params.get("q");
      apply();
    }
  });

  input.addEventListener("input", apply);
  input.addEventListener("focus", apply);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      results.hidden = true;
      input.blur();
    }
    if (e.key === "Enter") {
      var first = results.querySelector(".search-hit");
      if (first) {
        e.preventDefault();
        location.href = first.getAttribute("href");
      }
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== input && !e.metaKey && !e.ctrlKey) {
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      e.preventDefault();
      input.focus();
    }
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search")) results.hidden = true;
  });
})();
