// Progressive enhancement for the audit form. Without JS the form still submits
// to GET /audit and returns a scorecard. With JS, we stream GET /audit/stream so
// the page narrates each real step (clone, parse, score) as the server reaches it.
(function () {
  var form = document.getElementById("audit-form");
  if (!form) return;

  var result = document.getElementById("result");
  var progress = document.getElementById("progress");
  var steps = document.getElementById("progress-steps");
  var input = form.elements["url"];
  var button = form.querySelector("button");

  function addStep(text) {
    // Mark the previous step done, add the new one as active.
    var prev = steps.querySelector(".pstep--active");
    if (prev) prev.className = "pstep pstep--done";
    var li = document.createElement("li");
    li.className = "pstep pstep--active";
    li.textContent = text;
    steps.appendChild(li);
  }

  function finish(html) {
    var last = steps.querySelector(".pstep--active");
    if (last) last.className = "pstep pstep--done";
    result.innerHTML = html;
    progress.hidden = true;
    button.disabled = false;
    input.disabled = false;
  }

  var tryExample = document.getElementById("try-example");
  if (tryExample) {
    tryExample.addEventListener("click", function () {
      input.value = "openhonest/slop-audit";
      if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  }

  form.addEventListener("submit", function (e) {
    if (typeof EventSource === "undefined") return; // let the plain form submit
    e.preventDefault();
    var value = input.value.trim();
    if (!value) return;

    result.innerHTML = "";
    steps.innerHTML = "";
    progress.hidden = false;
    button.disabled = true;
    input.disabled = true;
    addStep("Starting the audit…");

    var es = new EventSource("/audit/stream?url=" + encodeURIComponent(value));
    es.addEventListener("step", function (ev) { addStep(JSON.parse(ev.data)); });
    es.addEventListener("done", function (ev) { finish(JSON.parse(ev.data)); es.close(); });
    es.addEventListener("fail", function (ev) { finish(JSON.parse(ev.data)); es.close(); });
    es.onerror = function () {
      var last = steps.querySelector(".pstep--active");
      if (last) last.textContent = "Lost the connection. Try again.";
      button.disabled = false;
      input.disabled = false;
      es.close();
    };
  });
})();
