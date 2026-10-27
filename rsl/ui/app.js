const AXES = ["lx", "ly", "rx", "ry", "lt", "rt"];
const TRIGGERS = ["lt", "rt"];
const BUTTONS = ["a", "b", "x", "y", "lb", "rb", "back", "start", "ls", "rs", "up", "down", "left", "right", "guide"];
const KEY_LABELS = { a: "a", b: "b", x: "x", y: "y", lb: "lb", rb: "rb", back: "back", start: "start", ls: "ls", rs: "rs", guide: "guide" };
const ARROWS = { up: "M6 2 11 10H1z", down: "M6 10 1 2h10z", left: "M2 6 10 1v10z", right: "M10 6 2 11V1z" };
const CONDITIONS = ["high", "mid", "low"];
const BAUDS = [420000, 416666, 400000, 115200];
const POLL_MS = 33;
const CONFIRM_MS = 3000;
const DRIVER_BUSY = ["downloading", "verifying", "installing"];
const OUTPUT_ERRORS = ["driver", "module", "output"];
const SVG = "http://www.w3.org/2000/svg";

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const app = {
  lang: navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en",
  profile: null,
  name: "",
  dirty: false,
  profiles: [],
  ports: [],
  state: null,
  inputKeys: "",
  deviceKey: "",
  listen: null,
  noteTimer: 0,
  removeTimer: 0,
  removeArmed: false,
  driverOpen: false,
  lastFocus: null,
};

function t(key, vars = {}) {
  const text = I18N[app.lang]?.[key] ?? I18N.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

function count(n, key) {
  const forms = t(key).split("|");
  let index = n === 1 ? 0 : 1;
  if (app.lang === "ru") {
    const tens = n % 100;
    const ones = n % 10;
    index = ones === 1 && tens !== 11 ? 0 : ones >= 2 && ones <= 4 && (tens < 12 || tens > 14) ? 1 : 2;
  }
  return `${n} ${forms[Math.min(index, forms.length - 1)]}`;
}

function node(tag, props = {}, children = []) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") element.className = value;
    else if (key === "text") element.textContent = value;
    else if (key.startsWith("on")) element.addEventListener(key.slice(2), value);
    else if (key.startsWith("data-") || key.startsWith("aria-")) element.setAttribute(key, value);
    else element[key] = value;
  }
  element.append(...[].concat(children).filter((child) => child != null));
  return element;
}

function arrow(key) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("width", "12");
  svg.setAttribute("height", "12");
  svg.setAttribute("viewBox", "0 0 12 12");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute("d", ARROWS[key]);
  svg.append(path);
  return svg;
}

function setFact(id, text) {
  const element = $(id);
  if (element.dataset.text === text) return;
  element.dataset.text = text;
  element.title = text;
  element.replaceChildren(...text.split(/(\d+(?:[.,]\d+)?)/).filter(Boolean).map((part) => (/^\d/.test(part) ? node("span", { class: "num", text: part }) : document.createTextNode(part))));
}

function inputLabel(id) {
  const match = /^([abch])(\d+)([xy]?)$/.exec(id);
  if (!match) return id;
  const n = Number(match[2]) + 1;
  if (match[1] === "c") return `CH${n}`;
  if (match[1] === "a") return t("in.axis", { n });
  if (match[1] === "b") return t("in.button", { n });
  return t("in.hat", { n, axis: match[3].toUpperCase() });
}

function inputIds() {
  return Object.keys(app.state?.values ?? {});
}

function meter(unipolar) {
  return node("div", { class: unipolar ? "meter uni" : "meter" }, node("i"));
}

function setMeter(element, value, unipolar) {
  const fill = element.firstChild;
  if (unipolar) {
    fill.style.left = "0";
    fill.style.width = `${Math.max(0, Math.min(1, value)) * 100}%`;
    return;
  }
  const v = Math.max(-1, Math.min(1, value));
  fill.style.left = `${50 + Math.min(v, 0) * 50}%`;
  fill.style.width = `${Math.abs(v) * 50}%`;
}

function push() {
  app.dirty = true;
  api().set_profile(app.profile);
}

function flash(text) {
  $("note").textContent = text;
  clearTimeout(app.noteTimer);
  app.noteTimer = setTimeout(() => ($("note").textContent = ""), 2500);
}

function fillInputOptions(select, value) {
  const ids = inputIds();
  if (value && !ids.includes(value)) ids.push(value);
  select.replaceChildren(
    node("option", { value: "", text: t("map.none") }),
    ...ids.map((id) => node("option", { value: id, text: inputLabel(id) })),
  );
  select.value = value;
}

function inputSelect(cfg) {
  const select = node("select", {
    class: "input-select",
    onchange: () => {
      cfg.in = select.value;
      push();
    },
  });
  fillInputOptions(select, cfg.in);
  return select;
}

function percentInput(cfg, field, max) {
  const input = node("input", {
    type: "number",
    min: 0,
    max,
    step: 1,
    value: Math.round(cfg[field] * 100),
    onchange: (event) => {
      const value = Math.max(0, Math.min(max, Math.round(Number(event.target.value) || 0)));
      event.target.value = value;
      cfg[field] = value / 100;
      push();
    },
  });
  return node("span", { class: "with-unit" }, [input, node("span", { class: "unit", text: "%" })]);
}

function assignButton(group, key) {
  return node("button", {
    type: "button",
    class: "btn compact",
    "data-listen": `${group}:${key}`,
    "aria-pressed": "false",
    text: t("map.assign"),
    onclick: () => toggleListen(group, key),
  });
}

function axisRow(key) {
  const cfg = app.profile.axes[key];
  const unipolar = TRIGGERS.includes(key);
  return node("tr", { "data-axis": key }, [
    node("td", { text: t(`out.${key}`) }),
    node("td", {}, inputSelect(cfg)),
    node("td", {}, node("input", {
      type: "checkbox",
      checked: cfg.inv,
      "aria-label": t("col.invert"),
      onchange: (event) => {
        cfg.inv = event.target.checked;
        push();
      },
    })),
    node("td", {}, percentInput(cfg, "dz", 50)),
    node("td", {}, percentInput(cfg, "expo", 100)),
    node("td", {}, assignButton("axes", key)),
    node("td", {}, [meter(unipolar), node("span", { class: "value" })]),
  ]);
}

function buttonRow(key) {
  const cfg = app.profile.buttons[key];
  const when = node("select", {
    onchange: () => {
      cfg.when = when.value;
      push();
    },
  }, CONDITIONS.map((c) => node("option", { value: c, text: t(`when.${c}`) })));
  when.value = cfg.when;
  return node("tr", { "data-button": key }, [
    node("td", { text: t(`out.${key}`) }),
    node("td", {}, inputSelect(cfg)),
    node("td", {}, when),
    node("td", {}, assignButton("buttons", key)),
    node("td", {}, node("span", { class: "ind" })),
  ]);
}

function buildMapping() {
  $("axesBody").replaceChildren(...AXES.map(axisRow));
  $("buttonsBody").replaceChildren(...BUTTONS.map(buttonRow));
  paintListen();
}

function buildKeys() {
  $("keys").replaceChildren(...BUTTONS.map((key) => node("span", { class: "key", "data-pad": key, title: t(`out.${key}`) }, ARROWS[key] ? arrow(key) : KEY_LABELS[key])));
}

function buildInputs(force) {
  const ids = inputIds();
  const key = ids.join(",");
  if (!force && key === app.inputKeys) return false;
  app.inputKeys = key;
  $("inputs-list").replaceChildren(...ids.map((id) => node("div", { class: "input-row", "data-id": id }, [
    node("span", { class: "label", text: inputLabel(id) }),
    id.startsWith("b") ? node("span", { class: "ind" }) : meter(false),
    node("span", { class: "value" }),
  ])));
  $("inputsEmpty").hidden = ids.length > 0;
  return true;
}

function fillDevices(force) {
  const kind = $("kind").value;
  const list = kind === "hid" ? app.state?.devices ?? [] : app.ports;
  const key = `${kind}|${app.lang}|${list.map((d) => `${d.id}=${d.name}`).join("|")}`;
  $("baudField").hidden = kind !== "crsf";
  if (!force && key === app.deviceKey) return;
  app.deviceKey = key;
  const select = $("device");
  const target = app.state?.target;
  const previous = select.value || (target?.kind === kind ? target.id : "");
  select.replaceChildren(...(list.length
    ? list.map((d) => node("option", { value: d.id, text: d.name }))
    : [node("option", { value: "", text: t("src.none") })]));
  if (list.some((d) => d.id === previous)) select.value = previous;
}

function renderProfiles() {
  const select = $("profiles");
  select.replaceChildren(
    node("option", { value: "", text: t("prof.unsaved") }),
    ...app.profiles.map((name) => node("option", { value: name, text: name })),
  );
  select.value = app.profiles.includes(app.name) ? app.name : "";
  $("remove").disabled = !app.name;
  disarmRemove();
}

function applyText() {
  document.documentElement.lang = app.lang;
  document.querySelectorAll("[data-i18n]").forEach((element) => (element.textContent = t(element.dataset.i18n)));
  document.querySelectorAll("[data-i18n-label]").forEach((element) => element.setAttribute("aria-label", t(element.dataset.i18nLabel)));
  document.querySelectorAll("[data-lang]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.lang === app.lang)));
}

function applyI18n() {
  applyText();
  buildKeys();
  buildMapping();
  buildInputs(true);
  fillDevices(true);
  renderProfiles();
  if (app.state) render();
}

function toggleListen(group, key) {
  const same = app.listen?.group === group && app.listen?.key === key;
  app.listen = same ? null : { group, key, base: { ...(app.state?.values ?? {}) } };
  paintListen();
}

function paintListen() {
  const active = app.listen ? `${app.listen.group}:${app.listen.key}` : "";
  document.querySelectorAll("[data-listen]").forEach((button) => {
    const on = button.dataset.listen === active;
    button.setAttribute("aria-pressed", String(on));
    button.textContent = t(on ? "map.listening" : "map.assign");
  });
}

function detect(values) {
  if (!app.listen) return;
  let best = "";
  let delta = 0.5;
  for (const [id, value] of Object.entries(values)) {
    if (!(id in app.listen.base)) continue;
    const change = Math.abs(value - app.listen.base[id]);
    if (change > delta) {
      delta = change;
      best = id;
    }
  }
  if (!best) return;
  const { group, key } = app.listen;
  const cfg = app.profile[group][key];
  cfg.in = best;
  if (group === "buttons") cfg.when = values[best] > 0.5 ? "high" : values[best] < -0.5 ? "low" : "mid";
  app.listen = null;
  push();
  buildMapping();
}

function openDriver(open) {
  if (open === app.driverOpen) return;
  app.driverOpen = open;
  $("driver-dialog").hidden = !open;
  document.querySelector(".app").inert = open;
  if (open) {
    app.lastFocus = document.activeElement;
    if (app.state) renderDriver(app.state.driver);
    const target = $("driverInstall").hidden ? $("driverLater") : $("driverInstall");
    target.focus();
  } else if (app.lastFocus) {
    app.lastFocus.focus();
    app.lastFocus = null;
  }
}

function renderDriver(driver) {
  if (!app.driverOpen || !driver) return;
  const { stage } = driver;
  const busy = DRIVER_BUSY.includes(stage);
  let text = t("driver.text");
  if (busy) text = t(`driver.${stage}`, { p: Math.round(driver.progress * 100) });
  if (stage === "installed") text = t("driver.installed");
  if (stage === "failed") text = t(`driver.err.${driver.error}`);
  $("driverTitle").textContent = t(stage === "installed" ? "driver.titleReady" : "driver.title");
  $("driverText").textContent = text;
  $("driverFile").textContent = driver.file ?? "";
  $("driverCond").hidden = busy || stage === "installed";
  $("driverProgress").hidden = stage !== "downloading";
  setMeter($("driverProgress"), driver.progress, true);
  $("driverInstall").hidden = busy || stage === "installed";
  $("driverInstall").textContent = t(stage === "failed" ? "driver.retry" : "driver.install");
  $("driverLater").hidden = busy;
  $("driverLater").textContent = t(stage === "installed" ? "driver.done" : "driver.later");
}

function sourceLevel(state) {
  if (state.source) return state.source.signal ? "live" : "nosignal";
  return state.target ? "wait" : "idle";
}

function setModule(id, on, bad, facts) {
  $(id).dataset.on = String(on);
  $(id).dataset.bad = String(bad);
  for (const [field, text] of Object.entries(facts)) setFact(field, text);
}

function renderModules(state) {
  const level = sourceLevel(state);
  const kind = state.source?.kind ?? state.target?.kind ?? $("kind").value;
  const name = state.source ? `${t(`kind.${kind}`)} · ${state.source.name}` : t(`kind.${kind}`);
  setModule("modSource", level === "live", level === "nosignal", { factSourceName: name, factSourceState: t(`fact.src.${level}`) });

  const calibrated = Object.keys(app.profile?.cal ?? {}).length;
  const profileName = app.name ? (app.dirty ? `${app.name} · ${t("prof.changed")}` : app.name) : t("prof.unsaved");
  setModule("modProfile", Boolean(app.name) && !app.dirty, false, {
    factProfileName: profileName,
    factProfileCal: t("fact.cal", { n: count(calibrated, "unit.channels") }),
  });

  const ids = inputIds();
  const axes = ids.filter((id) => id.startsWith("a") || id.startsWith("c")).length;
  const buttons = ids.filter((id) => id.startsWith("b")).length;
  const hats = ids.filter((id) => id.startsWith("h")).length / 2;
  const buttonLine = hats ? `${count(buttons, "unit.buttons")} · ${count(hats, "unit.hats")}` : count(buttons, "unit.buttons");
  setModule("modInputs", ids.length > 0, false, {
    factInputsAxes: count(axes, kind === "crsf" ? "unit.channels" : "unit.axes"),
    factInputsButtons: buttonLine,
  });

  const outputError = OUTPUT_ERRORS.includes(state.error);
  setModule("modPad", state.output, outputError, { factPadState: t(state.output ? "fact.pad.on" : outputError ? "fact.pad.error" : "fact.pad.off") });

  const mappedAxes = AXES.filter((key) => app.profile?.axes[key].in).length;
  const mappedButtons = BUTTONS.filter((key) => app.profile?.buttons[key].in).length;
  setModule("modMap", mappedAxes + mappedButtons > 0, false, {
    factMapAxes: t("fact.map.axes", { n: mappedAxes, total: AXES.length }),
    factMapButtons: t("fact.map.buttons", { n: mappedButtons, total: BUTTONS.length }),
  });

  const driver = state.driver ?? { stage: "installed", progress: 0 };
  setModule("modDriver", driver.stage === "installed", driver.stage === "failed", {
    factDriverState: t(`fact.driver.${driver.stage}`, { p: Math.round(driver.progress * 100) }),
  });
}

function render() {
  const state = app.state;
  if (buildInputs(false)) document.querySelectorAll(".input-select").forEach((select) => fillInputOptions(select, select.value));
  fillDevices(false);

  for (const row of $("inputs-list").children) {
    const value = state.values[row.dataset.id] ?? 0;
    const [, level, text] = row.children;
    if (level.classList.contains("ind")) {
      level.classList.toggle("on", value > 0);
      text.textContent = value > 0 ? "1" : "0";
    } else {
      setMeter(level, value, false);
      text.textContent = value.toFixed(2);
    }
  }
  for (const row of $("axesBody").children) {
    const key = row.dataset.axis;
    const value = state.axes[key] ?? 0;
    setMeter(row.querySelector(".meter"), value, TRIGGERS.includes(key));
    row.querySelector(".value").textContent = value.toFixed(2);
  }
  for (const row of $("buttonsBody").children) {
    row.querySelector(".ind").classList.toggle("on", Boolean(state.buttons[row.dataset.button]));
  }
  for (const key of $("keys").children) {
    key.classList.toggle("on", Boolean(state.buttons[key.dataset.pad]));
  }
  for (const [id, x, y] of [["stickL", state.axes.lx, state.axes.ly], ["stickR", state.axes.rx, state.axes.ry]]) {
    const dot = $(id).firstChild;
    dot.style.left = `${50 + x * 50}%`;
    dot.style.top = `${50 - y * 50}%`;
  }
  $("trigL").firstChild.style.height = `${state.axes.lt * 100}%`;
  $("trigR").firstChild.style.height = `${state.axes.rt * 100}%`;

  renderModules(state);
  $("toggle").textContent = t(state.output ? "run.stop" : "run.start");
  $("connect").textContent = t(state.target ? "src.disconnect" : "src.connect");
  $("kind").disabled = Boolean(state.target);
  $("device").disabled = Boolean(state.target);
  $("baud").disabled = Boolean(state.target);
  $("error").hidden = !state.error;
  $("error").textContent = state.error ? t(`err.${state.error}`) : "";
  $("calibrate").textContent = t(state.calibrating ? "cal.finish" : "cal.start");
  $("calibrate").setAttribute("aria-pressed", String(state.calibrating));
  $("calHint").hidden = !state.calibrating;

  renderDriver(state.driver);
  detect(state.values);
}

async function loop() {
  for (;;) {
    try {
      app.state = await api().state();
      render();
    } catch (error) {
      console.error(error);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }
}

function setProfile(profile, dirty) {
  app.profile = profile;
  app.dirty = dirty;
  app.listen = null;
  buildMapping();
}

function disarmRemove() {
  clearTimeout(app.removeTimer);
  app.removeArmed = false;
  $("remove").dataset.armed = "false";
  $("remove").textContent = t("prof.delete");
}

async function removeProfile() {
  if (!app.name) return;
  if (!app.removeArmed) {
    app.removeArmed = true;
    $("remove").dataset.armed = "true";
    $("remove").textContent = t("prof.confirmDelete", { name: app.name });
    app.removeTimer = setTimeout(disarmRemove, CONFIRM_MS);
    return;
  }
  app.profiles = await api().delete_profile(app.name);
  app.name = "";
  app.dirty = true;
  renderProfiles();
  flash(t("prof.deleted"));
}

function wire() {
  $("baud").replaceChildren(...BAUDS.map((b) => node("option", { value: String(b), text: String(b) })));

  document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => {
    app.lang = button.dataset.lang;
    api().set_lang(app.lang);
    applyI18n();
  }));

  $("toggle").addEventListener("click", () => {
    if (app.state?.output) api().stop();
    else if (app.state?.driver?.stage !== "installed") openDriver(true);
    else api().start();
  });

  $("driverInstall").addEventListener("click", () => api().install_driver());
  $("driverLater").addEventListener("click", () => openDriver(false));
  $("modDriver").addEventListener("click", (event) => {
    event.preventDefault();
    openDriver(true);
  });

  $("kind").addEventListener("change", async () => {
    if ($("kind").value === "crsf") app.ports = await api().ports();
    fillDevices(true);
  });

  $("refresh").addEventListener("click", async () => {
    app.ports = await api().ports();
    fillDevices(true);
  });

  $("connect").addEventListener("click", () => {
    if (app.state?.target) {
      api().disconnect();
      return;
    }
    const id = $("device").value;
    if (!id) return;
    api().connect({ kind: $("kind").value, id, baud: Number($("baud").value) });
  });

  $("profiles").addEventListener("change", async () => {
    const name = $("profiles").value;
    if (!name) return;
    const profile = await api().load_profile(name);
    if (!profile) return;
    app.name = name;
    $("name").value = name;
    setProfile(profile, false);
    renderProfiles();
  });

  $("save").addEventListener("click", async () => {
    const name = $("name").value.trim() || t("prof.default");
    const result = await api().save_profile(name, app.profile);
    if (!result.name) return;
    app.name = result.name;
    app.dirty = false;
    app.profiles = result.profiles;
    $("name").value = result.name;
    renderProfiles();
    flash(t("prof.saved"));
  });

  $("remove").addEventListener("click", removeProfile);

  $("applyPreset").addEventListener("click", async () => {
    const kind = app.state?.source?.kind ?? $("kind").value;
    setProfile(await api().preset(Number($("preset").value), kind), true);
  });

  $("calibrate").addEventListener("click", async () => {
    if (app.state?.calibrating) setProfile(await api().calibrate_end(), true);
    else api().calibrate_begin();
  });

  $("calReset").addEventListener("click", async () => setProfile(await api().calibrate_reset(), true));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && app.driverOpen && !DRIVER_BUSY.includes(app.state?.driver?.stage)) {
      openDriver(false);
      return;
    }
    if (event.key === "Escape" && app.listen) {
      app.listen = null;
      paintListen();
    }
  });
}

async function boot() {
  const data = await api().boot();
  app.lang = data.lang || app.lang;
  app.profile = data.profile;
  app.name = data.name;
  app.profiles = data.profiles;
  applyText();
  $("version").textContent = data.version;
  $("name").value = data.name;
  app.ports = await api().ports();
  app.state = await api().state();
  wire();
  if (data.source) {
    $("kind").value = data.source.kind;
    $("baud").value = String(data.source.baud);
  }
  applyI18n();
  if (app.state.driver.stage !== "installed") openDriver(true);
  loop();
}

applyText();

if (window.pywebview?.api?.boot) boot();
else window.addEventListener("pywebviewready", boot, { once: true });
