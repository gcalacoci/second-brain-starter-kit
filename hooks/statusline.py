#!/usr/bin/env python3
"""Claude Code status line: model | dir (branch) | ctx | backlog | plan usage or cost | cron.

Installed by setup.sh as ~/.claude/statusline.py and set as "statusLine" in settings.json.
Context colours follow CONTEXT_WARN_TIERS (thousands: notice,warning,critical; default
100,140,170 for a 200k window), the same tiers as hooks/context-warn.py. The last segment
names scheduled jobs whose last run failed (~/.local/state/cron-status, written by
.overmind/lib/cron.sh); nothing shows while they all pass.
"""
import calendar, glob, json, os, sys, time, subprocess


def tiers():
    try:
        n, w, c = (int(float(x) * 1000) for x in
                   (os.environ.get("CONTEXT_WARN_TIERS") or "100,140,170").split(","))
        return n, w, c
    except ValueError:
        return 100_000, 140_000, 170_000


def cron_segment():
    """Failed scheduled jobs, red; None when every job's last run passed."""
    d = os.environ.get("CRON_STATE_DIR") or os.path.expanduser("~/.local/state/cron-status")
    failed = []
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(path) as f:
                s = json.load(f)
            if int(s.get("rc", 0)) != 0:
                failed.append(str(s.get("name") or os.path.basename(path)[:-5]))
        except Exception:
            continue
    return "\033[1;31mcron ✗ %s\033[0m" % ", ".join(failed) if failed else None


def g(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def tok(n):
    n = float(n)
    if n >= 1_000_000:
        return ("%.1fM" % (n / 1_000_000)).replace(".0M", "M")
    if n >= 1000:
        return "%dk" % round(n / 1000)
    return str(int(n))


def until(ts):
    s = int(ts - time.time())
    if s <= 0:
        return "now"
    d, r = divmod(s, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    if d:
        return "%dd%dh" % (d, h)
    if h:
        return "%dh%02dm" % (h, m)
    return "%dm" % m


def branch(cwd):
    try:
        if not cwd or not os.path.isdir(cwd):
            return None
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        r = subprocess.run(["git", "-C", cwd, "symbolic-ref", "--short", "-q", "HEAD"],
                           capture_output=True, text=True, timeout=1, env=env)
        b = r.stdout.strip()
        if b:
            return b
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=1, env=env)
        return r.stdout.strip() or None
    except Exception:
        return None


def history(path):
    """Transcript age, size and compaction count, cached per transcript.

    Age = since the transcript's first timestamp (spans compactions and resumes, resets
    on /clear). Only the bytes added since the last refresh are scanned.
    """
    if not path or not os.path.isfile(path):
        return None
    size = os.path.getsize(path)
    cdir = os.path.expanduser("~/.cache/claude-statusline")
    cfile = os.path.join(cdir, os.path.basename(path) + ".json")
    try:
        with open(cfile) as f:
            c = json.load(f)
        if c.get("path") != path or c.get("offset", 0) > size:
            c = {}
    except Exception:
        c = {}
    c["path"] = path
    off = c.get("offset", 0)
    if off < size:
        with open(path, "rb") as f:
            f.seek(off)
            chunk = f.read(size - off)
        end = chunk.rfind(b"\n") + 1  # whole lines only; the rest waits for the next refresh
        chunk = chunk[:end]
        if not c.get("start"):
            i = chunk.find(b'"timestamp":"')
            if i >= 0:
                ts = chunk[i + 13:i + 37].split(b'"')[0].decode()
                try:
                    c["start"] = calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
                except Exception:
                    pass
        c["compacts"] = c.get("compacts", 0) + chunk.count(b'"subtype":"compact_boundary"')
        c["offset"] = off + end
        try:
            os.makedirs(cdir, exist_ok=True)
            with open(cfile, "w") as f:
                json.dump(c, f)
        except Exception:
            pass
    if not c.get("start"):
        return None
    age = int(time.time() - c["start"])
    d, r = divmod(age, 86400)
    h, m = r // 3600, (r % 3600) // 60
    a = "%dd%dh" % (d, h) if d else ("%dh%02dm" % (h, m) if h else "%dm" % m)
    txt = "📜 %s · %.0fMB" % (a, size / 1048576.0) if size >= 1048576 else "📜 %s · %dkB" % (a, size // 1024)
    if c.get("compacts"):
        txt += " · %d×" % c["compacts"]
    return txt


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    parts = []

    model = g(data, "model", "display_name") or g(data, "model", "id")
    if model:
        parts.append(str(model))

    cwd = g(data, "workspace", "current_dir") or data.get("cwd")
    if cwd:
        s = os.path.basename(str(cwd).rstrip("/")) or "/"
        b = branch(str(cwd))
        parts.append(s + (" (%s)" % b if b else ""))

    # Context usage
    cw = data.get("context_window") or {}
    size = cw.get("context_window_size")
    pct = cw.get("used_percentage")
    used = cw.get("total_input_tokens")
    cu = cw.get("current_usage")
    if used is None and isinstance(cu, dict):
        used = sum(cu.get(k) or 0 for k in
                   ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    if pct is None and used is not None and size:
        pct = used * 100.0 / size
    if pct is not None:
        txt = "ctx %d%%" % round(pct)
        if used is None and size:
            used = pct * size / 100.0
        if used is not None and size:
            txt += " (%s/%s)" % (tok(used), tok(size))
        notice, warning, critical = tiers()
        if used is not None and used >= critical:
            txt = "\033[1;37;41m %s ⛔ COMPACT NOW \033[0m" % txt
        elif used is not None and used >= warning:
            txt = "\033[1;31m%s ⚠ compact\033[0m" % txt
        elif used is not None and used >= notice:
            txt = "\033[33m%s ⚠\033[0m" % txt
        parts.append(txt)
    elif size:
        parts.append("ctx 0%% (0/%s)" % tok(size))

    try:  # conversation backlog: age, transcript size, compactions
        h = history(data.get("transcript_path"))
        if h:
            parts.append(h)
    except Exception:
        pass

    # Plan usage
    rl = data.get("rate_limits") or {}
    plan = []
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        w = rl.get(key)
        if isinstance(w, dict) and w.get("used_percentage") is not None:
            t = "%s %d%%" % (label, round(w["used_percentage"]))
            if w.get("resets_at"):
                t += " (reset %s)" % until(w["resets_at"])
            plan.append(t)
    if plan:
        parts.append(" | ".join(plan))
    else:
        c = data.get("cost") or {}
        bits = []
        if c.get("total_cost_usd") is not None:
            bits.append("$%.2f" % c["total_cost_usd"])
        if c.get("total_duration_ms") is not None:
            m = int(c["total_duration_ms"] // 60000)
            bits.append("%dh%02dm" % divmod(m, 60) if m >= 60 else "%dm" % m)
        if bits:
            parts.append(" ".join(bits))

    try:  # scheduled jobs whose last run failed
        c = cron_segment()
        if c:
            parts.append(c)
    except Exception:
        pass

    sys.stdout.write(" | ".join(parts))


try:
    main()
except Exception:
    pass
