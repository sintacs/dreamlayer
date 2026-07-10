/* figment.js — the no-code lens builder's brain (INNOVATION_SESSION 5, Category 1).
 *
 * A figment is data, not code: scenes, timed/event transitions, pulses. This is
 * the pure logic behind landing/lens-builder.html — the budget rules (in exact
 * lockstep with reality_compiler/v2/figment.py; a Python test asserts the
 * numbers match), the recipe templates, the proof/safety card, and the
 * canonical export. No DOM here, so it runs in the browser AND under Node for
 * tests.
 *
 * The point of the whole platform: the installer re-checks this proof; it never
 * trusts the author. Same as the phone and the Brain.
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) module.exports = factory();
  else root.LensKit = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // -- budgets (keep in lockstep with reality_compiler/v2/figment.py) --------
  var B = {
    MAX_SCENES: 32, MAX_COUNTERS: 8, MAX_LINES: 5, MAX_TEXT_LEN: 24,
    MAX_PULSE_HZ: 4.0, MIN_SCENE_SEC: 0.5, MAX_SCENE_SEC: 24 * 3600.0,
    MAX_NAME_LEN: 40, MAX_BRANCHES: 4,
  };
  var END = "@end", SELF = "@self";
  var COLORS = ["background", "surface", "text_primary", "text_secondary",
    "accent_memory", "accent_attention", "accent_success", "accent_error",
    "border_subtle", "status_paused"];
  var SIZES = ["sm", "md", "lg"];
  // token -> hex, for the live ring preview (mirrors halo-lua/display/palette.lua)
  var HEX = {
    background: "#000000", surface: "#0E1416", text_primary: "#ECF0F1",
    text_secondary: "#A8B8C0", accent_memory: "#2CC79A", accent_attention: "#E06B52",
    accent_success: "#56D364", accent_error: "#E05252", border_subtle: "#2A3C44",
    status_paused: "#8FA8B2",
  };

  // -- model -----------------------------------------------------------------
  function line(content, opts) {
    opts = opts || {};
    return { content: String(content).slice(0, B.MAX_TEXT_LEN),
             row: opts.row || 0, size: opts.size || "md",
             color: opts.color || "text_primary" };
  }
  function scene(id, o) {
    o = o || {};
    var s = { id: id, lines: o.lines || [] };
    if (o.duration_sec != null) s.duration_sec = o.duration_sec;
    if (o.on_timeout) s.on_timeout = o.on_timeout;      // [{target, emit?}]
    if (o.on) s.on = o.on;                              // {event: {target}}
    if (o.pulse) s.pulse = o.pulse;                     // {window_sec, rate_hz, color}
    if (o.tick) s.tick = o.tick;
    return s;
  }
  function figment(name, initial) {
    return { id: "", name: name || "My lens", initial: initial || "",
             version: 2, scenes: {}, counters: {}, meta: {} };
  }
  function addScene(fig, s) { fig.scenes[s.id] = s; if (!fig.initial) fig.initial = s.id; return s; }

  // -- recipe templates (the no-coder's on-ramp) -----------------------------
  function tInterval(o) {
    o = o || {}; var work = o.work || 180, rest = o.rest || 30;
    var f = figment(o.name || "Interval timer", "work");
    addScene(f, scene("work", {
      duration_sec: work, tick: "countdown",
      lines: [line("WORK", { row: 0, size: "lg", color: "accent_memory" })],
      pulse: { window_sec: Math.min(10, work), rate_hz: 2.0, color: "accent_attention" },
      on_timeout: [{ target: "rest" }],
      on: { double: { target: END } },
    }));
    addScene(f, scene("rest", {
      duration_sec: rest, tick: "countdown",
      lines: [line("REST", { row: 0, size: "lg", color: "accent_success" })],
      on_timeout: [{ target: "work" }],
      on: { double: { target: END } },
    }));
    return f;
  }
  function tCountdown(o) {
    o = o || {}; var secs = o.seconds || 300;
    var f = figment(o.name || "Countdown", "run");
    addScene(f, scene("run", {
      duration_sec: secs, tick: "countdown",
      lines: [line(o.label || "TIME", { row: 0, size: "lg", color: "accent_memory" })],
      pulse: { window_sec: Math.min(10, secs), rate_hz: 2.0, color: "accent_attention" },
      on_timeout: [{ target: END }],
      on: { double: { target: END } },
    }));
    return f;
  }
  function tChecklist(o) {
    o = o || {}; var steps = o.steps || ["Step one", "Step two", "Step three"];
    var f = figment(o.name || "Checklist ritual", "s0");
    for (var i = 0; i < steps.length; i++) {
      var next = i + 1 < steps.length ? "s" + (i + 1) : END;
      addScene(f, scene("s" + i, {
        lines: [line(String(steps[i]).slice(0, B.MAX_TEXT_LEN), { row: 0, size: "md" }),
                line("nod / double-tap →", { row: 2, size: "sm", color: "text_secondary" })],
        on: { double: { target: next }, "imu:nod": { target: next } },
      }));
    }
    return f;
  }
  function tBreathing(o) {
    o = o || {}; var inS = o.in_s || 4, hold = o.hold_s || 4, out = o.out_s || 4;
    var f = figment(o.name || "Box breathing", "in");
    var mk = function (id, label, dur, nxt, col) {
      return scene(id, {
        duration_sec: dur, lines: [line(label, { row: 0, size: "lg", color: col })],
        pulse: { window_sec: dur, rate_hz: 1.0, color: col },
        on_timeout: [{ target: nxt }], on: { double: { target: END } },
      });
    };
    addScene(f, mk("in", "BREATHE IN", inS, "hold1", "accent_memory"));
    addScene(f, mk("hold1", "HOLD", hold, "out", "text_secondary"));
    addScene(f, mk("out", "BREATHE OUT", out, "hold2", "accent_success"));
    addScene(f, mk("hold2", "HOLD", hold, "in", "text_secondary"));
    return f;
  }
  var TEMPLATES = [
    { id: "interval", name: "Interval timer", blurb: "Work / rest rounds — pulses near the switch.", make: tInterval },
    { id: "countdown", name: "Countdown", blurb: "A single timer that pulses as it lands.", make: tCountdown },
    { id: "checklist", name: "Checklist ritual", blurb: "Named stages you advance with a nod.", make: tChecklist },
    { id: "breathing", name: "Box breathing", blurb: "In · hold · out · hold, gently breathing the ring.", make: tBreathing },
  ];

  // -- validation (a subset of budgets.verify — everything the builder emits) -
  function timed(s) { return s.duration_sec != null; }
  function targets(s) {
    var out = [];
    (s.on_timeout || []).forEach(function (t) { out.push(t.target); });
    if (s.on) Object.keys(s.on).forEach(function (k) { out.push(s.on[k].target); });
    return out;
  }
  function validate(fig) {
    var v = [];
    function bad(code, msg, sid) { v.push({ code: code, msg: msg, scene: sid || null }); }
    if (!fig.name || fig.name.length > B.MAX_NAME_LEN) bad("name", "name must be 1.." + B.MAX_NAME_LEN + " chars");
    var ids = Object.keys(fig.scenes);
    if (ids.length === 0) bad("empty", "a lens needs at least one scene");
    if (ids.length > B.MAX_SCENES) bad("scene_count", ids.length + " scenes > max " + B.MAX_SCENES);
    if (Object.keys(fig.counters || {}).length > B.MAX_COUNTERS) bad("counter_count", "too many counters");
    if (ids.length && ids.indexOf(fig.initial) < 0) bad("initial", "start scene '" + fig.initial + "' doesn't exist");
    ids.forEach(function (sid) {
      var s = fig.scenes[sid];
      if ((s.lines || []).length > B.MAX_LINES) bad("lines", s.lines.length + " lines > max " + B.MAX_LINES, sid);
      var rows = {};
      (s.lines || []).forEach(function (ln) {
        if ((ln.content || "").length > B.MAX_TEXT_LEN) bad("text_len", "a line is > " + B.MAX_TEXT_LEN + " chars", sid);
        if (ln.row < 0 || ln.row >= B.MAX_LINES) bad("row", "row " + ln.row + " out of range", sid);
        if (rows[ln.row]) bad("row", "two lines on row " + ln.row, sid); rows[ln.row] = 1;
        if (COLORS.indexOf(ln.color) < 0) bad("color", "'" + ln.color + "' is not a palette color", sid);
        if (SIZES.indexOf(ln.size) < 0) bad("size", "unknown size '" + ln.size + "'", sid);
      });
      if (timed(s) && !(s.duration_sec >= B.MIN_SCENE_SEC && s.duration_sec <= B.MAX_SCENE_SEC))
        bad("duration", "duration must be " + B.MIN_SCENE_SEC + ".." + B.MAX_SCENE_SEC + "s", sid);
      if (timed(s) && !(s.on_timeout && s.on_timeout.length)) bad("timeout", "a timed scene needs a 'when it ends' step", sid);
      if (!timed(s) && s.on_timeout && s.on_timeout.length) bad("timeout", "on-timeout needs a duration", sid);
      if (s.on_timeout && s.on_timeout.length > B.MAX_BRANCHES) bad("branches", "too many timeout branches", sid);
      targets(s).forEach(function (tg) {
        if (tg !== END && tg !== SELF && ids.indexOf(tg) < 0) bad("target", "goes to unknown scene '" + tg + "'", sid);
      });
      if (s.pulse) {
        if (!timed(s)) bad("pulse", "pulse needs a timed scene", sid);
        if (!(s.pulse.rate_hz > 0 && s.pulse.rate_hz <= B.MAX_PULSE_HZ)) bad("pulse_rate", "pulse > " + B.MAX_PULSE_HZ + "Hz (the photic-safety cap)", sid);
        if (timed(s) && s.pulse.window_sec > s.duration_sec) bad("pulse", "pulse window exceeds the scene", sid);
        if (COLORS.indexOf(s.pulse.color) < 0) bad("color", "pulse color is not a token", sid);
      }
    });
    return { ok: v.length === 0, violations: v };
  }

  // -- the proof, as a consent card (mirrors reality_compiler/v2/safety.py) ---
  function safetyCard(fig) {
    var rep = validate(fig);
    var worstHz = 0, longest = 0, sceneCount = Object.keys(fig.scenes).length;
    Object.keys(fig.scenes).forEach(function (sid) {
      var s = fig.scenes[sid];
      if (s.pulse) worstHz = Math.max(worstHz, s.pulse.rate_hz);
      if (timed(s)) longest = Math.max(longest, s.duration_sec);
    });
    return {
      ok: rep.ok,
      violations: rep.violations,
      cannot: [
        "pulse faster than " + B.MAX_PULSE_HZ + " Hz — the photic-safety cap (this one: ≤ " + (worstHz || 0) + " Hz)",
        "reach the network, your files, the camera, or the mic — it is data, not code",
        "show more than " + B.MAX_LINES + " lines at once",
        "swallow your kill switch — double-long-press banish lives below every lens",
      ],
      will: [sceneCount + " scene(s), each held at least half a second"],
    };
  }

  function canonical(fig) { return JSON.stringify(fig, Object.keys(fig).sort()); }

  return {
    BUDGETS: B, COLORS: COLORS, SIZES: SIZES, HEX: HEX, END: END, SELF: SELF,
    TEMPLATES: TEMPLATES, figment: figment, scene: scene, line: line, addScene: addScene,
    validate: validate, safetyCard: safetyCard, canonical: canonical,
    templates: { interval: tInterval, countdown: tCountdown, checklist: tChecklist, breathing: tBreathing },
  };
});
