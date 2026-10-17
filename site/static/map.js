(function () {
  var el = document.getElementById("map");
  if (!el || !window.L) return;
  var spot = [parseFloat(el.dataset.lat), parseFloat(el.dataset.lng)];
  var map = L.map(el, { scrollWheelZoom: false }).setView(spot, 16);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  L.marker(spot).addTo(map).bindPopup(el.dataset.name);
})();
