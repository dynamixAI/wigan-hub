(function () {
  var root = document.body.dataset.root || "";
  var nameBox = document.getElementById("q-name");
  var whereBox = document.getElementById("q-where");
  var out = document.getElementById("results");
  var places = null;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  // lower case, and postcodes without spaces so "wn71aa" and "WN7 1AA" both match
  function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9 ]/g, " "); }
  function squash(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ""); }

  function load() {
    if (places) return Promise.resolve(places);
    return fetch(root + "search.json").then(function (r) { return r.json(); }).then(function (d) {
      places = d.map(function (p) {
        return { p: p, name: norm(p[0]), where: norm(p[1] + " " + p[2] + " " + p[5]), pc: squash(p[2]) };
      });
      return places;
    });
  }

  function words(s) { return norm(s).split(/\s+/).filter(Boolean); }

  function matchesWhere(x, q, ws) {
    var sq = squash(q);
    if (sq.length >= 5 && /\d/.test(sq) && x.pc.indexOf(sq) === 0) return true;
    return ws.every(function (w) { return x.where.indexOf(w) !== -1; });
  }

  function rank(x, nameWords, rawName) {
    if (!nameWords.length) return 0;
    var n = norm(rawName).trim();
    if (x.name.trim() === n) return 0;
    if (x.name.indexOf(n) === 0) return 1;
    return 2;
  }

  function row(p) {
    var r = /^\d$/.test(p[3]) ? p[3] : "x", shown = r === "x" ? "–" : r;
    var side = p[7] ? '<span class="chip old">' + esc(p[7]) + "</span>" : "";
    if (p[6]) side += "<span>" + esc(p[6]) + "</span>";
    return '<a class="row" href="' + root + "place/" + p[4] + '.html"><span class="rating r' + r + '">' + shown +
      '</span><span class="row-main"><span class="row-name">' + esc(p[0]) + '</span><span class="row-meta">' +
      esc(p[1]) + (p[2] ? ", " + esc(p[2]) : "") + '</span></span><span class="row-side">' + side + "</span></a>";
  }

  function show() {
    var rawName = nameBox.value.trim(), rawWhere = whereBox.value.trim();
    var nameWords = words(rawName), whereWords = words(rawWhere);
    if (!nameWords.length && !whereWords.length) { out.innerHTML = ""; return; }
    load().then(function (all) {
      var hits = all.filter(function (x) {
        var nameOk = nameWords.every(function (w) { return x.name.indexOf(w) !== -1; });
        return nameOk && (!whereWords.length || matchesWhere(x, rawWhere, whereWords));
      });
      hits.sort(function (a, b) {
        return rank(a, nameWords, rawName) - rank(b, nameWords, rawName) || a.p[0].localeCompare(b.p[0]);
      });
      var shown = hits.slice(0, 30).map(function (x) { return row(x.p); });
      var where = rawWhere ? " in " + esc(rawWhere) : "";
      out.innerHTML = hits.length
        ? '<p class="more">' + hits.length + (hits.length === 1 ? " place" : " places") + where +
          (hits.length > 30 ? ", showing the first 30" : "") + '</p><div class="list">' + shown.join("") + "</div>"
        : '<p class="more">Nothing matches that. Check the spelling, or try just the street or the first half of the postcode.</p>';
    });
  }

  if (nameBox && whereBox) {
    var timer;
    [nameBox, whereBox].forEach(function (box) {
      box.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(show, 120); });
    });
  }

  // filters on area pages
  var filters = document.querySelectorAll(".filters button");
  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filters.forEach(function (b) { b.classList.toggle("on", b === btn); });
      var d = btn.dataset;
      document.querySelectorAll("#area-list .item").forEach(function (el) {
        var r = el.dataset.rating, n = /^\d$/.test(r) ? +r : null, keep = true;
        if (d.recent) keep = n !== null && el.dataset.old === "0";
        else if (!d.all) keep = n !== null && n >= +d.min && n <= +d.max;
        el.hidden = !keep;
      });
    });
  });
})();
