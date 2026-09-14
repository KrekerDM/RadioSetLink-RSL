const AXES = ["lx", "ly", "rx", "ry", "lt", "rt"];
const TRIGGERS = ["lt", "rt"];
const BUTTONS = ["a", "b", "x", "y", "lb", "rb", "back", "start", "ls", "rs", "up", "down", "left", "right", "guide"];
const KEY_LABELS = { a: "A", b: "B", x: "X", y: "Y", lb: "LB", rb: "RB", back: "Back", start: "Start", ls: "LS", rs: "RS", up: "↑", down: "↓", left: "←", right: "→", guide: "Guide" };
const CONDITIONS = ["high", "mid", "low"];
const BAUDS = [420000, 416666, 400000, 115200];
const POLL_MS = 33;
const DRIVER_BUSY = ["downloading", "verifying", "installing"];

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const app = {
  lang: "en",
  profile: null,
  name: "",
  profiles: [],
  ports: [],
  state: null,
  inputKeys: "",
  deviceKey: "",
  listen: null,
  noteTimer: 0,
  driverOpen: false,
};

function t(key, vars = {}) {
  const text = I18N[app.lang]?.[key] ?? I18N.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
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
  return node("input", {
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
}

function assignButton(group, key) {
  return node("button", {
    type: "button",
    class: "button small",
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
    node("td", {}, meter(unipolar)),
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
  $("keys").replaceChildren(...BUTTONS.map((key) => node("span", { class: "key", "data-pad": key, text: KEY_LABELS[key] })));
}

function buildInputs(force) {
  const ids = inputIds();
  const key = ids.join(",");
  if (!force && key === app.inputKeys) return false;
  app.inputKeys = key;
  $("inputs").replaceChildren(...ids.map((id) => node("div", { class: "input-row", "data-id": id }, [
    node("span", { class: "caption", text: inputLabel(id) }),
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
}

function applyI18n() {
  document.documentElement.lang = app.lang;
  document.querySelectorAll("[data-i18n]").forEach((element) => (element.textContent = t(element.dataset.i18n)));
  document.querySelectorAll("[data-lang]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.lang === app.lang)));
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
  app.driverOpen = open;
  $("driver").hidden = !open;
  if (open && app.state) renderDriver(app.state.driver);
}

function renderDriver(driver) {
  if (!app.driverOpen || !driver) return;
  const { stage } = driver;
  const busy = DRIVER_BUSY.includes(stage);
  let text = t("driver.text");
  if (busy) text = t(`driver.${stage}`, { p: Math.round(driver.progress * 100) });
  if (stage === "installed") text = t("driver.installed");
  if (stage === "failed") text = t(`driver.err.${driver.error}`);
  $("driverText").textContent = text;
  $("driverProgress").hidden = stage !== "downloading";
  setMeter($("driverProgress"), driver.progress, true);
  $("driverInstall").hidden = busy || stage === "installed";
  $("driverInstall").textContent = t(stage === "failed" ? "driver.retry" : "driver.install");
  $("driverLater").hidden = busy;
  $("driverLater").textContent = t(stage === "installed" ? "driver.done" : "driver.later");
}

function statusLevel(state) {
  if (state.source?.signal) return "live";
  return state.target ? "wait" : "idle";
}

function statusText(state) {
  let text = t("status.idle");
  if (state.target && !state.source) text = t("status.waiting");
  if (state.source) text = state.source.signal ? t("status.connected", { name: state.source.name }) : t("status.nosignal");
  return state.output ? `${text} · ${t("status.output")}` : text;
}

function render() {
  const state = app.state;
  if (buildInputs(false)) document.querySelectorAll(".input-select").forEach((select) => fillInputOptions(select, select.value));
  fillDevices(false);

  for (const row of $("inputs").children) {
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
    setMeter(row.querySelector(".meter"), state.axes[key] ?? 0, TRIGGERS.includes(key));
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

  $("status").textContent = statusText(state);
  $("statusDot").dataset.level = statusLevel(state);
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

function setProfile(profile) {
  app.profile = profile;
  app.listen = null;
  buildMapping();
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
    setProfile(profile);
    renderProfiles();
  });

  $("save").addEventListener("click", async () => {
    const name = $("name").value.trim() || t("prof.default");
    const result = await api().save_profile(name, app.profile);
    if (!result.name) return;
    app.name = result.name;
    app.profiles = result.profiles;
    $("name").value = result.name;
    renderProfiles();
    flash(t("prof.saved"));
  });

  $("remove").addEventListener("click", async () => {
    if (!app.name) return;
    app.profiles = await api().delete_profile(app.name);
    app.name = "";
    renderProfiles();
    flash(t("prof.deleted"));
  });

  document.querySelectorAll("[data-preset]").forEach((button) => button.addEventListener("click", async () => {
    const kind = app.state?.source?.kind ?? $("kind").value;
    setProfile(await api().preset(Number(button.dataset.preset), kind));
  }));

  $("calibrate").addEventListener("click", async () => {
    if (app.state?.calibrating) setProfile(await api().calibrate_end());
    else api().calibrate_begin();
  });

  $("calReset").addEventListener("click", async () => setProfile(await api().calibrate_reset()));

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
  app.lang = data.lang || (navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en");
  app.profile = data.profile;
  app.name = data.name;
  app.profiles = data.profiles;
  app.ports = await api().ports();
  app.state = await api().state();
  wire();
  if (data.source) {
    $("kind").value = data.source.kind;
    $("baud").value = String(data.source.baud);
  }
  $("name").value = data.name;
  buildKeys();
  applyI18n();
  if (app.state.driver.stage !== "installed") openDriver(true);
  loop();
}

if (window.pywebview?.api?.boot) boot();
else window.addEventListener("pywebviewready", boot, { once: true });
