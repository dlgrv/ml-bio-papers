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
  var selectedTopics = new Set();
  var sortMode = "year-desc";

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

  function topicSet(li) {
    return new Set(
      (li.getAttribute("data-topics") || "")
        .split(/\s+/)
        .filter(Boolean)
    );
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
      var slug = li.getAttribute("data-slug");
      var textOk = empty || shown.has(slug);
      var topics = topicSet(li);
      var tagsOk = true;
      selectedTopics.forEach(function (t) {
        if (!topics.has(t)) tagsOk = false;
      });
      li.hidden = !(textOk && tagsOk);
    });
  }

  function intAttr(li, name) {
    var raw = li.getAttribute(name);
    if (raw === null || raw === "") return null;
    var n = parseInt(raw, 10);
    return isNaN(n) ? null : n;
  }

  function compareNullable(a, b, asc) {
    if (a === null && b === null) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    return asc ? a - b : b - a;
  }

  function sortIndex() {
    var ul = document.querySelector(".blog-index");
    if (!ul) return;
    var items = Array.prototype.slice.call(ul.querySelectorAll("li[data-slug]"));
    var mode = sortMode === "year" ? "year-desc" : sortMode;
    items.sort(function (a, b) {
      var c = 0;
      if (mode === "year-asc" || mode === "year-desc") {
        c = compareNullable(
          intAttr(a, "data-year"),
          intAttr(b, "data-year"),
          mode === "year-asc"
        );
        if (c !== 0) return c;
        return (a.getAttribute("data-slug") || "").localeCompare(
          b.getAttribute("data-slug") || ""
        );
      }
      return compareNullable(
        intAttr(a, "data-difficulty"),
        intAttr(b, "data-difficulty"),
        mode === "difficulty-asc"
      );
    });
    items.forEach(function (li) {
      ul.appendChild(li);
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

  function syncUrl() {
    var params = new URLSearchParams(location.search);
    var q = input.value.trim();
    if (q) params.set("q", q);
    else params.delete("q");
    if (sortMode && sortMode !== "year-desc" && sortMode !== "year") {
      params.set("sort", sortMode);
    } else {
      params.delete("sort");
    }
    if (selectedTopics.size) {
      params.set("tags", Array.from(selectedTopics).join(","));
    } else {
      params.delete("tags");
    }
    var qs = params.toString();
    var next = qs ? "?" + qs : location.pathname;
    if (next !== location.pathname + location.search) {
      history.replaceState(null, "", next);
    }
  }

  function updateTagCount() {
    var countEl = document.querySelector(".tag-filter__count");
    if (!countEl) return;
    if (selectedTopics.size) {
      countEl.textContent = String(selectedTopics.size);
      countEl.setAttribute("data-empty", "0");
    } else {
      countEl.textContent = "0";
      countEl.setAttribute("data-empty", "1");
    }
  }

  function apply() {
    filterIndex(input.value);
    sortIndex();
    renderDropdown(match(input.value));
    updateTagCount();
    syncUrl();
  }

  function fitSortSelect() {
    if (!sortSelect || !sortSelect.options.length) return;
    var probe = document.createElement("span");
    var cs = window.getComputedStyle(sortSelect);
    probe.setAttribute("aria-hidden", "true");
    probe.style.cssText =
      "position:absolute;visibility:hidden;white-space:nowrap;pointer-events:none;font:" +
      cs.font;
    document.body.appendChild(probe);
    var max = 0;
    Array.prototype.forEach.call(sortSelect.options, function (opt) {
      probe.textContent = opt.text;
      max = Math.max(max, probe.getBoundingClientRect().width);
    });
    document.body.removeChild(probe);
    sortSelect.style.width = Math.ceil(max) + "px";
  }

  var sortSelect = document.getElementById("sort");
  if (sortSelect) {
    fitSortSelect();
    sortSelect.addEventListener("change", function () {
      sortMode = sortSelect.value || "year-desc";
      apply();
    });
  }

  var tagFilter = document.getElementById("tag-filter");
  document.querySelectorAll('.tag-filter__option input[data-topic]').forEach(function (box) {
    box.addEventListener("change", function () {
      var topic = box.getAttribute("data-topic");
      if (!topic) return;
      if (box.checked) selectedTopics.add(topic);
      else selectedTopics.delete(topic);
      apply();
    });
  });

  if (tagFilter) {
    document.addEventListener("click", function (e) {
      if (!tagFilter.open) return;
      if (!e.target.closest("#tag-filter")) tagFilter.removeAttribute("open");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && tagFilter.open) tagFilter.removeAttribute("open");
    });
  }

  ready.then(function () {
    var params = new URLSearchParams(location.search);
    if (params.get("q")) {
      input.value = params.get("q");
    }
    var sort = params.get("sort") || "year-desc";
    if (sort === "year") sort = "year-desc";
    if (
      sort === "year-asc" ||
      sort === "year-desc" ||
      sort === "difficulty-asc" ||
      sort === "difficulty-desc"
    ) {
      sortMode = sort;
      if (sortSelect) sortSelect.value = sortMode;
    }
    var tags = (params.get("tags") || "")
      .split(",")
      .map(function (t) {
        return t.trim();
      })
      .filter(Boolean);
    tags.forEach(function (t) {
      selectedTopics.add(t);
      document.querySelectorAll('.tag-filter__option input[data-topic="' + t + '"]').forEach(function (box) {
        box.checked = true;
      });
    });
    apply();
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
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      e.preventDefault();
      input.focus();
    }
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search")) results.hidden = true;
  });
})();
