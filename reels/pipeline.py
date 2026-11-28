"""
Daily run:  pick what this slot posts -> write or continue the script -> render -> YouTube upload -> save state.

Every day (see config.SLOT_KIND): two comedy reels built on the morning's trend research (state/trends.json, looks
alternate doodle <-> desi) and one katha part. A katha series has 2-3 parts, one part per day; when it ends the next one
is the other katha format (paheli <-> devotional). The active series lives in state/series.json.

    python -m reels.pipeline                                            # daily run (needs the secrets in env)
    python -m reels.pipeline --no-upload                                # test: render today's part, upload nothing
    python -m reels.pipeline --script samples/nyay_01.json --part 2 --preview
"""
import os, sys, json, glob, shutil, argparse, random, datetime as dt
from .config import ROOT, OUT, STATE, FORMATS, KINDS, KATHA_KINDS, COMEDY_STYLES, SLOT_KIND
from . import timeline, render, writer, youtube, qa, trends as trendmod

HISTORY = os.path.join(STATE, "history.json")        # every uploaded video
SERIES = os.path.join(STATE, "series.json")          # {"active": series + "next" part index, "last_kind": ...}
LAST_ERROR = os.path.join(STATE, "last_error.txt")   # why Claude failed last time (committed with the state)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def log(*a): print(*a, flush=True)


def load(path, default):
    try: return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError): return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def as_series(d):
    """A file is either a series {parts:[...]} or a single reel; always return a series."""
    return d if d.get("parts") else dict(series_title=d.get("yt_title", "")[:30], type=d.get("type", "devotional"), parts=[d])


def sample_series(kind, history):
    """Backup when Claude fails: a sample series of this kind, preferring one not posted yet."""
    pool = [as_series(load(p, {})) for p in sorted(glob.glob(os.path.join(ROOT, "samples", "*.json")))]
    pool = [s for s in pool if s.get("type") == kind] or [s for s in pool if s.get("type") in KATHA_KINDS]
    used = {h.get("series") for h in history}
    return random.choice([s for s in pool if s.get("series_title") not in used] or pool)


def warn(title, msg):
    if os.environ.get("GITHUB_ACTIONS"):   # shown on the run's summary page
        msg = msg[:900].replace("%", "%25").replace("\r", "").replace("\n", "%0A")
        print(f"::warning title={title}::{msg}", flush=True)


def new_series(kind, today, history, yt, topic=""):
    trends = writer.trending(yt)
    log(f"writing a new {kind} series ({len(trends)} trending titles)" + (f", topic: {topic.splitlines()[0]}" if topic else ""))
    try:
        series = writer.write_series(kind, today.strftime("%d %B %Y, %A"), trends, [h.get("title", "") for h in history],
                                     [h["story"] for h in history if h.get("story")], topic)
        if series.get("_story"): log("based on owner story:", series["_story"])
        if os.path.exists(LAST_ERROR): os.remove(LAST_ERROR)
    except Exception as e:
        log("Claude failed, using a sample series:", repr(e))
        warn("Claude script failed, sample used", repr(e))
        open(LAST_ERROR, "w", encoding="utf-8").write(f"{dt.datetime.now(IST):%Y-%m-%d %H:%M} IST\n{e}\n")
        series = dict(sample_series(kind, history), _sample=True)
    return dict(series, next=0)


def comedy_reel(today, history, yt):
    """A one-part comedy 'series' on the next unused trend topic, in the look that is due."""
    n = sum(1 for h in history if h.get("type") == "comedy")
    ti, topic = trendmod.next_topic()
    series = new_series("comedy", today, history, yt, topic)
    style = COMEDY_STYLES[n % len(COMEDY_STYLES)]
    for p in series["parts"]: p.setdefault("style", style)
    if not series.get("_sample"): series["_topic"] = ti
    return series


def quality_check(mp4, tl, voices, script, voice_dir, out_mp4):
    """Check the finished reel. A text-to-speech glitch is fixed by making the voices again and rendering once more.
    -> (report, mp4, tl, voices)"""
    for attempt in (1, 2):
        rep = qa.check(mp4, tl, voices, script)
        save(os.path.join(OUT, "qa.json"), rep)
        log(f"QA {'PASS' if rep['ok'] else 'FAIL'}: " + "; ".join(rep["notes"]))
        for f in rep["fails"]: log("  x", f)
        if rep["ok"] or attempt == 2 or not rep["voice_bad"]:
            break
        log("making the voices again and rendering once more")
        shutil.rmtree(voice_dir, ignore_errors=True)
        tl, voices = timeline.build_timeline(script, voice_dir)
        mp4 = render.render(tl, voices, out_mp4, log=log)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:                                       # shown on the run page
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Video check: {'✅ PASS' if rep['ok'] else '❌ FAIL (not uploaded)'}\n\n{script.get('yt_title', '')}\n\n")
            f.write("".join(f"- {n}\n" for n in rep["notes"]) + "".join(f"- ❌ {x}\n" for x in rep["fails"]) + "\n")
    return rep, mp4, tl, voices


def todays_part(a, state, history, today, yt):
    """-> (series, part index, from_state)."""
    if a.script:
        series = as_series(load(a.script, {}))
        return series, max(0, min(a.part, len(series["parts"])) - 1), False
    want = a.type if a.type in KINDS else SLOT_KIND.get(a.slot, "katha")
    if want == "comedy":
        return comedy_reel(today, history, yt), 0, False
    series = state.get("active")
    if a.type in KATHA_KINDS and series and series.get("type") != a.type:
        series = None                                           # a different format was asked for
    if not series or series.get("next", 0) >= len(series.get("parts", [])):
        last = state.get("last_kind")
        if a.type in KATHA_KINDS: kind = a.type
        elif last in KATHA_KINDS: kind = KATHA_KINDS[(KATHA_KINDS.index(last) + 1) % len(KATHA_KINDS)]      # take turns
        else: kind = KATHA_KINDS[0]
        series = new_series(kind, today, history, yt)
        state["active"] = series
        save(SERIES, state)          # saved on test runs too, so the next real run posts this same Part 1
    return series, series["next"], True


def main():
    for st in (sys.stdout, sys.stderr):      # Hindi text on a Windows console
        try: st.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", default="auto", help="auto / " + " / ".join(KINDS) + " (forces a new series of that format)")
    ap.add_argument("--script", help="render a local script/series JSON instead of the series state")
    ap.add_argument("--part", type=int, default=1, help="with --script: which part")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--preview", action="store_true", help="only render a contact sheet")
    ap.add_argument("--post-time", default="now", help="publish time IST, HH:MM, or 'now' (see reels/schedule.py)")
    ap.add_argument("--slot", default="extra", help="which daily slot this video fills (recorded in the history)")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    today = dt.datetime.now(IST).date()
    history = load(HISTORY, [])
    state = load(SERIES, {"active": None, "last_kind": None})
    yt = None if a.no_upload else youtube.client()

    series, idx, from_state = todays_part(a, state, history, today, yt)
    kind, n = series.get("type", KINDS[0]), len(series["parts"])
    part = series["parts"][idx]
    badge = (part.get("label") or FORMATS[kind]["label"]).upper()
    script = timeline.clean_script(dict(part, type=kind, label=f"{badge} · PART {idx + 1}/{n}" if n > 1 else badge))
    save(os.path.join(OUT, "script.json"), dict(part, type=kind))
    log(f"{series.get('series_title')!r} part {idx + 1}/{n} ({kind}): {script['yt_title']!r}, {len(script['shots'])} shots")

    voice_dir = os.path.join(OUT, "voice")
    tl, voices = timeline.build_timeline(script, voice_dir)
    log(f"timeline {tl['total']:.1f}s, {len(tl['phrases'])} lines")
    if a.preview:
        render.preview(tl, os.path.join(OUT, "preview.jpg")); log("preview ->", os.path.join(OUT, "preview.jpg")); return
    out_mp4 = os.path.join(OUT, "reel.mp4")
    mp4 = render.render(tl, voices, out_mp4, log=log)
    log("rendered ->", mp4)
    rep, mp4, tl, voices = quality_check(mp4, tl, voices, script, voice_dir, out_mp4)
    if not rep["ok"]:                                 # never put a broken reel online; the next hourly run tries again
        warn("Video check failed, not uploaded", "; ".join(rep["fails"]))
        sys.exit("video check failed: " + "; ".join(rep["fails"]))

    if a.no_upload:
        log("test run: nothing uploaded, this part stays queued"); return
    if yt is None: sys.exit("YouTube secrets missing (YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN)")
    publish = None                                   # None = public right away
    if a.post_time != "now":
        hh, mm = map(int, a.post_time.split(":"))
        publish = dt.datetime(today.year, today.month, today.day, hh, mm, tzinfo=IST).astimezone(dt.timezone.utc)
    vid, status = youtube.upload(yt, mp4, script["yt_title"], script["yt_description"], script.get("tags", []), publish)
    log(f"uploaded https://youtube.com/shorts/{vid} ({status})")

    entry = dict(date=str(today), slot=a.slot, type=kind, series=series.get("series_title"), part=f"{idx + 1}/{n}",
                 title=script["yt_title"], seconds=round(tl["total"], 1), video_id=vid)
    if series.get("_story"): entry["story"] = series["_story"]
    if kind == "comedy": entry["style"] = part.get("style")
    save(HISTORY, (history + [entry])[-200:])
    if series.get("_topic") is not None: trendmod.mark_used(series["_topic"])
    if from_state:
        series["next"] = idx + 1
        if series["next"] >= n: state.update(active=None, last_kind=kind)    # series finished
        else: state["active"] = series
        save(SERIES, state)


if __name__ == "__main__":
    main()
