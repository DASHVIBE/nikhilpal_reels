"""Quality check of a finished reel, run after rendering and before anything is uploaded.

Checks the file itself (one ffmpeg pass over the real mp4) and the script/voices that went into it:
  video   size 1080x1920, 30 fps, every frame present, length = timeline, no black or frozen stretch
  audio   audio track present and as long as the video, loud enough, not clipping, no long silence,
          voice audible in the mp4 during every caption
  voices  every line has a voice clip, not empty, not cut short or stretched (seconds per word)
  script  every line of the script made it into the timeline, captions and titles present, yt_title fits

check() -> report dict; report["ok"] is False if anything failed. report["voice_bad"] lists voice clips worth
re-making (text-to-speech glitches are the most common fixable failure).
"""
import re, subprocess
import numpy as np
from .config import W, H, FPS, SR
from .util import ffmpeg_exe

MEAN_DB = (-32.0, -12.0)      # whole-reel loudness window
MAX_DB = -0.3                 # above this the audio clips
SILENCE_S = 2.5               # longest allowed silence (not counting the last 2 s)
BLACK_S = 0.6                 # longest allowed black stretch (the final fade is 0.4 s)
FREEZE_S = 3.0                # longest allowed frozen picture
SEC_PER_WORD = (0.18, 1.1)    # spoken Hindi: about 0.35-0.6 s per word


def probe(mp4):
    """One decode pass: stream info, frame count, black/frozen/silent stretches, loudness."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostats", "-i", mp4,
           "-vf", f"blackdetect=d={BLACK_S}:pix_th=0.06,freezedetect=n=0.0008:d={FREEZE_S}",
           "-af", f"silencedetect=n=-45dB:d={SILENCE_S},volumedetect", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    info = dict(log=err)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0
    m = re.search(r"Video: .*?(\d{3,5})x(\d{3,5}).*?([\d.]+) fps", err)
    info["size"], info["fps"] = ((int(m[1]), int(m[2])), float(m[3])) if m else ((0, 0), 0.0)
    info["audio"] = bool(re.search(r"Stream #\S+.*Audio:", err))
    info["black"] = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    info["freeze"] = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    info["silence"] = [(float(a), float(b)) for a, b in
                       re.findall(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+)", err)]
    m = re.search(r"mean_volume: (-?[\d.]+) dB", err); info["mean_db"] = float(m[1]) if m else -99.0
    m = re.search(r"max_volume: (-?[\d.]+) dB", err); info["max_db"] = float(m[1]) if m else -99.0
    frames = re.findall(r"frame=\s*(\d+)", err)
    info["frames"] = int(frames[-1]) if frames else 0
    return info


def mp4_audio(mp4):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", mp4, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def db(x): return 20 * np.log10(max(1e-9, float(np.sqrt(np.mean(np.square(x)))) if len(x) else 1e-9))


def check(mp4, tl, voices, script):
    fails, notes, voice_bad = [], [], []
    total = tl["total"]

    # ---- script -> timeline: nothing dropped
    want = sum(len(s.get("phrases", [])) for s in script["shots"])
    if len(tl["phrases"]) != want or len(voices) != want:
        fails.append(f"lines missing: script {want}, timeline {len(tl['phrases'])}, voices {len(voices)}")
    if len(tl["shots"]) != len(script["shots"]):
        fails.append(f"shots missing: script {len(script['shots'])}, timeline {len(tl['shots'])}")
    for k, ph in enumerate(tl["phrases"]):
        if not ph["text"].replace("*", "").strip(): fails.append(f"line {k + 1}: empty caption")
        if ph["end"] > total - 1.0: fails.append(f"line {k + 1}: ends too close to the end of the reel")
        if k and ph["start"] < tl["phrases"][k - 1]["end"] - 0.01: fails.append(f"line {k + 1}: overlaps the line before")
    for key in ("title1", "end_text"):
        if not (tl.get(key) or "").strip(): fails.append(f"{key} is empty")
    yt = script.get("yt_title", "")
    if not yt.strip() or len(yt) > 100: fails.append(f"yt_title empty or longer than 100 characters ({len(yt)})")

    # ---- voice clips: present, not cut, not stretched
    hindi = [hi for s in script["shots"] for _, hi, _ in s["phrases"]]
    for k, (v, hi) in enumerate(zip(voices, hindi)):
        sec, words = len(v) / SR, max(1, len(hi.split()))
        if sec < 0.4 or db(v) < -40:
            fails.append(f"line {k + 1}: voice is empty or silent ({sec:.2f}s)"); voice_bad.append(k)
        elif not SEC_PER_WORD[0] <= sec / words <= SEC_PER_WORD[1]:
            fails.append(f"line {k + 1}: voice {sec:.1f}s for {words} words, looks cut or stretched"); voice_bad.append(k)

    # ---- the real file
    info = probe(mp4)
    if info["size"] != (W, H): fails.append(f"video size {info['size']}, expected {(W, H)}")
    if abs(info["fps"] - FPS) > 0.5: fails.append(f"frame rate {info['fps']}, expected {FPS}")
    nf = int(total * FPS)
    if abs(info["frames"] - nf) > 2: fails.append(f"frames {info['frames']}, expected {nf} (frames dropped or cut)")
    if abs(info["duration"] - total) > 0.6: fails.append(f"length {info['duration']:.1f}s, expected {total:.1f}s")
    if not info["audio"]: fails.append("no audio track")
    for a, b in info["black"]:
        if a < total - 1.0: fails.append(f"black picture {a:.1f}-{b:.1f}s")
    for a in info["freeze"]:
        if a < total - 1.0: fails.append(f"picture frozen from {a:.1f}s")
    for a, b in info["silence"]:
        if a < total - 2.0: fails.append(f"silence {a:.1f}-{b:.1f}s")
    if not MEAN_DB[0] <= info["mean_db"] <= MEAN_DB[1]: fails.append(f"loudness {info['mean_db']} dB outside {MEAN_DB}")
    if info["max_db"] > MAX_DB: fails.append(f"audio clips (peak {info['max_db']} dB)")

    # ---- voice really audible in the mp4 during every caption (louder than the music around it)
    au = mp4_audio(mp4)
    if info["audio"] and len(au) < (total - 0.5) * SR: fails.append(f"audio is shorter than the video ({len(au) / SR:.1f}s)")
    if len(au):
        bed = db(au[int(max(0, tl["phrases"][0]["start"] - 1.4) * SR): int(max(0.2, tl["phrases"][0]["start"] - 0.2) * SR)])
        for k, ph in enumerate(tl["phrases"]):
            seg = au[int(ph["start"] * SR): int(ph["end"] * SR)]
            lv = db(seg)
            if lv < -36 or (bed > -60 and lv < bed + 3):
                fails.append(f"line {k + 1}: voice not audible in the video ({lv:.0f} dB)")
    notes.append(f"{info['duration']:.1f}s, {info['frames']} frames, {info['size'][0]}x{info['size'][1]} @ {info['fps']:g} fps, "
                 f"loudness {info['mean_db']} dB, peak {info['max_db']} dB, {len(tl['phrases'])} lines, {len(tl['shots'])} shots")
    return dict(ok=not fails, fails=fails, notes=notes, voice_bad=sorted(set(voice_bad)))
