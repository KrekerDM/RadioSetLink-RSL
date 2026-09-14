import math

AXES = ("lx", "ly", "rx", "ry", "lt", "rt")
TRIGGERS = ("lt", "rt")
BUTTONS = ("a", "b", "x", "y", "lb", "rb", "back", "start", "ls", "rs", "up", "down", "left", "right", "guide")
CONDITIONS = ("high", "mid", "low")


def clamp(value, low, high):
    return max(low, min(high, value))


def number(value, low, high):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return low
    return clamp(result, low, high) if math.isfinite(result) else low


def blank_profile():
    return {
        "axes": {key: {"in": "", "inv": False, "dz": 0.0, "expo": 0.0} for key in AXES},
        "buttons": {key: {"in": "", "when": "high"} for key in BUTTONS},
        "cal": {},
    }


def normalize_profile(data):
    profile = blank_profile()
    if not isinstance(data, dict):
        return profile
    axes = data.get("axes") if isinstance(data.get("axes"), dict) else {}
    for key in AXES:
        source = axes.get(key) if isinstance(axes.get(key), dict) else {}
        target = profile["axes"][key]
        target["in"] = str(source.get("in") or "")
        target["inv"] = bool(source.get("inv"))
        target["dz"] = number(source.get("dz"), 0.0, 0.5)
        target["expo"] = number(source.get("expo"), 0.0, 1.0)
    buttons = data.get("buttons") if isinstance(data.get("buttons"), dict) else {}
    for key in BUTTONS:
        source = buttons.get(key) if isinstance(buttons.get(key), dict) else {}
        target = profile["buttons"][key]
        target["in"] = str(source.get("in") or "")
        target["when"] = source.get("when") if source.get("when") in CONDITIONS else "high"
    cal = data.get("cal") if isinstance(data.get("cal"), dict) else {}
    for key, pair in cal.items():
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            low, high = number(pair[0], -1.0, 1.0), number(pair[1], -1.0, 1.0)
            if high - low > 0.05:
                profile["cal"][str(key)] = [low, high]
    return profile


def preset(mode, prefix):
    profile = blank_profile()
    aileron, elevator, throttle, rudder = (f"{prefix}{i}" for i in range(4))
    if mode == 1:
        left, right = (rudder, elevator), (aileron, throttle)
    else:
        left, right = (rudder, throttle), (aileron, elevator)
    profile["axes"]["lx"]["in"], profile["axes"]["ly"]["in"] = left
    profile["axes"]["rx"]["in"], profile["axes"]["ry"]["in"] = right
    for offset, key in enumerate(("a", "b", "x", "y")):
        profile["buttons"][key]["in"] = f"{prefix}{offset + 4}"
    return profile


def calibrated(value, pair):
    if not pair:
        return clamp(value, -1.0, 1.0)
    low, high = pair
    return clamp((value - low) / (high - low) * 2.0 - 1.0, -1.0, 1.0)


def shape_stick(value, cfg):
    if cfg["inv"]:
        value = -value
    magnitude = abs(value)
    deadzone = cfg["dz"]
    if magnitude <= deadzone:
        return 0.0
    value = math.copysign((magnitude - deadzone) / (1.0 - deadzone), value)
    expo = cfg["expo"]
    return (1.0 - expo) * value + expo * value ** 3


def shape_trigger(value, cfg):
    if cfg["inv"]:
        value = -value
    level = (value + 1.0) / 2.0
    deadzone = cfg["dz"]
    if level <= deadzone:
        return 0.0
    level = (level - deadzone) / (1.0 - deadzone)
    expo = cfg["expo"]
    return (1.0 - expo) * level + expo * level ** 3


def apply(profile, values):
    cal = profile["cal"]
    axes = {}
    for key in AXES:
        cfg = profile["axes"][key]
        raw = values.get(cfg["in"])
        if raw is None:
            axes[key] = 0.0
            continue
        value = calibrated(raw, cal.get(cfg["in"]))
        axes[key] = shape_trigger(value, cfg) if key in TRIGGERS else shape_stick(value, cfg)
    buttons = {}
    for key in BUTTONS:
        cfg = profile["buttons"][key]
        raw = values.get(cfg["in"])
        if raw is None:
            buttons[key] = False
            continue
        value = calibrated(raw, cal.get(cfg["in"]))
        if cfg["when"] == "low":
            buttons[key] = value < -0.5
        elif cfg["when"] == "mid":
            buttons[key] = abs(value) <= 0.5
        else:
            buttons[key] = value > 0.5
    return axes, buttons
