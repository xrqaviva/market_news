/* Lightweight calendar date picker (antd DatePicker-like) for the report
 * sidebar. Reads #calendar-dates JSON ({date: last-report-url}), shows a
 * month grid, disables dates without reports, and jumps to the picked day's
 * last report. Works on both the fusion page and standalone report pages.
 */
(function () {
  "use strict";

  var datesJson = document.getElementById("calendar-dates");
  if (!datesJson) return;
  var dateTargets = {};
  try {
    dateTargets = JSON.parse(datesJson.textContent || "{}");
  } catch (e) {
    return;
  }
  var available = Object.keys(dateTargets).sort();
  if (!available.length) return;

  var filter = document.getElementById("calendar-filter");
  if (!filter) return;
  var input = filter.querySelector("input");
  var pop = filter.querySelector(".calendar-pop");
  var titleEl = filter.querySelector(".calendar-title");
  var grid = filter.querySelector(".calendar-grid");
  var todayBtn = filter.querySelector('[data-nav="today"]');

  var selected = available[available.length - 1];
  var viewYear = Number(selected.slice(0, 4));
  var viewMonth = Number(selected.slice(5, 7)) - 1;

  function pad(n) { return String(n).padStart(2, "0"); }

  function render() {
    titleEl.textContent = viewYear + "年" + (viewMonth + 1) + "月";
    var first = new Date(viewYear, viewMonth, 1);
    var startWeekday = (first.getDay() + 6) % 7; // Monday first
    var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    var cells = [];
    for (var i = 0; i < startWeekday; i++) cells.push('<span class="calendar-day empty"></span>');
    for (var d = 1; d <= daysInMonth; d++) {
      var date = viewYear + "-" + pad(viewMonth + 1) + "-" + pad(d);
      var url = dateTargets[date];
      var cls = "calendar-day";
      if (!url) cls += " disabled";
      if (date === selected) cls += " selected";
      cells.push(
        '<button type="button" class="' + cls + '" data-date="' + date + '"' +
        (url ? "" : " disabled") + ">" + d + "</button>"
      );
    }
    grid.innerHTML = cells.join("");
  }

  function show() {
    render();
    pop.hidden = false;
  }

  function hide() {
    pop.hidden = true;
  }

  function jump(date) {
    var url = dateTargets[date];
    if (url) window.location.href = url;
  }

  input.addEventListener("click", function (e) {
    e.stopPropagation();
    pop.hidden ? show() : hide();
  });

  filter.querySelectorAll(".calendar-head [data-nav]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var nav = btn.getAttribute("data-nav");
      if (nav === "year-prev") viewYear -= 1;
      else if (nav === "year-next") viewYear += 1;
      else if (nav === "month-prev") {
        viewMonth -= 1;
        if (viewMonth < 0) { viewMonth = 11; viewYear -= 1; }
      } else if (nav === "month-next") {
        viewMonth += 1;
        if (viewMonth > 11) { viewMonth = 0; viewYear += 1; }
      }
      render();
    });
  });

  grid.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-date]");
    if (!btn || btn.disabled) return;
    selected = btn.getAttribute("data-date");
    jump(selected);
  });

  if (todayBtn) {
    todayBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      jump(available[available.length - 1]);
    });
  }

  document.addEventListener("click", function (e) {
    if (!filter.contains(e.target)) hide();
  });
})();
