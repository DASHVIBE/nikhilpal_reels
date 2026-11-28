"""Voices (edge-tts), lip-sync envelopes, synthesized music (harmonium drone, santoor, suspense pulse) and effects, mixed to WAV."""
import os, math, random, subprocess, wave
import numpy as np
from .config import SR, FPS, VOICES
from .util import ffmpeg_exe


async def tts_all(items):
    import edge_tts
    for path, text, spk in items:
        if not os.path.exists(path):
            v, rate, pitch = VOICES[spk]
            await edge_tts.Communicate(text, v, rate=rate, pitch=pitch).save(path)

def decode(path):
    raw = subprocess.run([ffmpeg_exe(), "-v", "quiet", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    idx = np.where(np.abs(x) > 0.02)[0]
    if len(idx): x = x[max(0, idx[0] - 800): idx[-1] + 2500]
    act = np.abs(x) > 0.01
    rms = np.sqrt(np.mean(x[act] ** 2)) if act.any() else 1
    return x * (0.12 / rms)

def lip_env(x):
    hop = SR // FPS; n = len(x) // hop + 1
    r = np.array([np.sqrt(np.mean(x[i*hop:(i + 1)*hop] ** 2)) if i*hop < len(x) - 1 else 0 for i in range(n)])
    ref = np.percentile(r[r > 0], 90) if np.any(r > 0) else 1
    e = np.clip((r / ref - 0.15) / 0.85, 0, 1) ** 0.8
    return [round(float(v), 3) for v in e]

RNG = np.random.default_rng(21)

def tarr(d): return np.arange(int(d * SR)) / SR

def noise(d): return RNG.standard_normal(int(d * SR))

def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, len(x)); return y / (np.max(np.abs(y)) + 1e-9)

def add(buf, t0, sig, g=1.0):
    i = int(t0 * SR)
    if i < 0: sig = sig[-i:]; i = 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g

def reverb(x):
    ir_t = tarr(1.4); ir = noise(1.4) * np.exp(-ir_t / 0.32); ir[:int(0.02*SR)] = 0; ir /= np.sqrt(np.sum(ir**2))
    n = len(x) + len(ir); y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    return np.concatenate([x, np.zeros(len(ir))]) + 0.2 * y / (np.max(np.abs(y)) + 1e-9) * np.max(np.abs(x))

def tanpura(n):
    out = np.zeros(n); cache = {}
    for f in (110.0, 146.83, 73.42):
        t = tarr(3.4); s = np.zeros_like(t)
        for h in range(1, 15):
            s += (1 / h) * (1 + 0.5*np.sin(2*np.pi*0.6*t*h/3 + h)) * np.sin(2*np.pi*f*h*t*(1 + 0.0006*h))
        cache[f] = s * np.exp(-t / 1.5) * np.minimum(1, t / 0.01)
    seq = [110.0, 146.83, 146.83, 73.42]; t0 = 0.3; i = 0
    while t0 < n / SR: add(out, t0, cache[seq[i % 4]]); t0 += 0.78; i += 1
    return out / (np.max(np.abs(out)) + 1e-9)

SCALE = [293.66, 329.63, 369.99, 440, 493.88, 587.33, 659.26, 739.99, 880]

def bansuri(n, seed):
    rng = random.Random(seed); out = np.zeros(n); t0 = 1.2; idx = 5
    while t0 < n / SR - 1.5:
        d = rng.choice([0.45, 0.45, 0.9, 0.9, 1.35, 1.8, 2.7])
        idx = max(0, min(8, idx + rng.choice([-2, -1, -1, 0, 1, 1, 2]))); f = SCALE[idx]
        L = d + 0.25; tt = tarr(L)
        vib = 1 + 0.006*np.sin(2*np.pi*5.2*tt)*np.clip((tt - 0.25) / 0.3, 0, 1)
        ph = 2*np.pi*np.cumsum(f*vib) / SR
        tone = np.sin(ph) + 0.12*np.sin(2*ph) + 0.04*np.sin(3*ph) + 0.05*band(noise(L), f*0.9, f*2.5)
        add(out, t0, tone * np.minimum(1, tt / 0.07) * np.clip((L - tt) / 0.25, 0, 1))
        t0 += d
        if rng.random() < 0.18: t0 += rng.choice([0.9, 1.8])
    return out / (np.max(np.abs(out)) + 1e-9)

def pad(freqs, d):
    t = tarr(d + 1.5); s = np.zeros_like(t)
    for f in freqs:
        for det in (1.0, 1.004, 0.996): s += np.sin(2*np.pi*f*det*t) * 0.5 + 0.15*np.sin(4*np.pi*f*det*t)
    return s / (len(freqs) * 3) * np.minimum(1, t / 1.0) * np.clip((d + 1.5 - t) / 1.5, 0, 1)

def bell(f0=520, d=4.0):
    t = tarr(d); s = np.zeros_like(t)
    for r, a, dc in ((1, 1, 2.5), (2.0, 0.6, 2.0), (2.76, 0.5, 1.6), (3.9, 0.3, 1.2), (5.4, 0.2, 0.9), (6.8, 0.1, 0.7)):
        s += a * np.sin(2*np.pi*f0*r*t) * np.exp(-t / dc)
    return s * np.minimum(1, t / 0.003) / 2.7

def sweep(f0, f1, d, decay):
    t = tarr(d); f = np.linspace(f0, f1, len(t))
    return np.sin(2*np.pi*np.cumsum(f) / SR) * np.exp(-t*decay) * np.minimum(1, t / 0.003)

def chirp(d=0.12):
    t = tarr(d); f = 3300 + 1300*np.sin(2*np.pi*28*t) + 2000*t/d
    return np.sin(2*np.pi*np.cumsum(f) / SR) * np.hanning(len(t))

def harmonium(n, root=130.81):
    """Reedy drone (Sa + Pa + upper Sa) that breathes slowly, like a hand-pumped harmonium."""
    t = np.arange(n) / SR; out = np.zeros(n)
    for f, g in ((root, 1.0), (root * 1.5, 0.6), (root * 2, 0.45)):
        ph = 2*np.pi*f*t
        reed = sum(np.sin(h*ph + 0.3*h) / h**1.2 for h in range(1, 9))     # bright reed spectrum
        out += g * reed * (1 + 0.004*np.sin(2*np.pi*0.3*t))
    out *= 0.75 + 0.25*np.sin(2*np.pi*0.11*t)                               # bellows
    return out / (np.max(np.abs(out)) + 1e-9)

YAMAN = [261.63, 293.66, 329.63, 369.99, 392.0, 440.0, 493.88, 523.25, 587.33, 659.26]

def pluck(f, d, bright=0.5):
    """Karplus-Strong string: a santoor-like hammered note."""
    n = int(d * SR); p_ = max(2, int(SR / f)); buf = RNG.uniform(-1, 1, p_) * (0.6 + 0.4*bright)
    out = np.zeros(n); k = 0
    for i in range(n):
        out[i] = buf[k]; nxt = buf[(k + 1) % p_]
        buf[k] = 0.996 * 0.5 * (buf[k] + nxt); k = (k + 1) % p_
    return out * np.minimum(1, np.arange(n) / (0.002 * SR))

def santoor(n, seed):
    """Gentle tremolo phrases in raag Yaman over the drone."""
    rng = random.Random(seed); out = np.zeros(n); t0 = 1.0; idx = 4; cache = {}
    while t0 < n / SR - 2:
        idx = max(0, min(len(YAMAN) - 1, idx + rng.choice([-2, -1, -1, 1, 1, 2])))
        f = YAMAN[idx]
        if f not in cache: cache[f] = pluck(f, 1.6)
        reps = rng.choice([1, 1, 2, 4])                                      # santoor tremolo = fast repeats
        for r in range(reps): add(out, t0 + r * 0.09, cache[f], 0.8 if r == 0 else 0.45)
        t0 += rng.choice([0.36, 0.36, 0.72, 0.72, 1.08])
        if rng.random() < 0.15: t0 += 1.4
    return out / (np.max(np.abs(out)) + 1e-9)

def tick(d=0.03):
    tq = tarr(d); return band(noise(d), 2500, 6000) * np.exp(-tq * 160)

def thump(d=0.35):
    tq = tarr(d); return np.sin(2*np.pi*(52 + 30*np.exp(-tq*30))*tq) * np.exp(-tq*12) * np.minimum(1, tq / 0.003)


MAJ = [261.63, 293.66, 329.63, 392.0, 440.0, 523.25, 587.33, 659.26]


def bouncy(n, total, seed):
    """Comedy bed: a light plucked bass + skipping melody on a swing beat with a soft shaker."""
    rng = random.Random(seed); out = np.zeros(n); beat = 0.36; cache = {}
    def note(f, d=0.5, b=0.6):
        if (f, d) not in cache: cache[(f, d)] = pluck(f, d, b)
        return cache[(f, d)]
    bass = [130.81, 98.0, 110.0, 87.31]; idx = 3; t0 = 0.25; i = 0
    while t0 < total:
        if i % 2 == 0: add(out, t0, note(bass[(i // 8) % 4], 0.6, 0.3), 0.9)          # oom
        else: add(out, t0, tick(0.05), 0.25)                                            # pah (shaker)
        if rng.random() < 0.55:
            idx = max(0, min(len(MAJ) - 1, idx + rng.choice([-2, -1, 1, 1, 2])))
            add(out, t0 + (beat * 0.66 if rng.random() < 0.4 else 0), note(MAJ[idx], 0.4, 0.8), 0.45)
        t0 += beat; i += 1
    return out / (np.max(np.abs(out)) + 1e-9)


def boing(d=0.45):
    t = tarr(d); f = 180 + 260 * np.exp(-t * 7) * (1 + 0.35 * np.sin(2 * np.pi * 14 * t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * np.minimum(1, t / 0.004)


def rimshot():
    """ba-dum-tss: two drum hits and a cymbal, for the punchline"""
    out = np.zeros(int(1.6 * SR))
    tq = tarr(0.25); tom = lambda f: np.sin(2 * np.pi * f * tq) * np.exp(-tq * 18)
    add(out, 0.0, tom(180), 0.8); add(out, 0.16, tom(130), 0.8)
    tc = tarr(1.2); add(out, 0.36, band(noise(1.2), 5000, 12000) * np.exp(-tc * 3.5), 0.5)
    return out


def music_bed(kind, n, total, seed):
    """Background music: ticking clock + heartbeat pulse over a low drone (paheli), harmonium + santoor (katha),
    or a bouncy plucked tune (comedy)."""
    bed = np.zeros(n)
    if kind == "comedy":
        return bouncy(n, total, seed)
    if kind == "paheli":
        t0 = 0.5
        while t0 < total:
            add(bed, t0, tick(), 0.5); t0 += 0.5
        t0 = 0.2
        while t0 < total:
            add(bed, t0, thump(), 0.9); add(bed, t0 + 0.24, thump(), 0.6); t0 += 1.6
        return bed + harmonium(n, 110.0) * 0.25
    return bed + harmonium(n) * 0.4 + santoor(n, seed) * 0.6


def shot_sfx(sfx, bed, s, first, rng):
    """Sound effects for one shot: a whoosh on every cut plus scene ambience."""
    st, d, kd = s["start"], s["dur"], s["kind"]
    if not first:
        sw = band(noise(0.5), 900, 7000) * np.hanning(int(0.5 * SR)) * np.linspace(0.3, 1, int(0.5 * SR))
        add(sfx, st - 0.45, sw, 0.07)
    if kd in ("gali", "ghar", "dukaan"):                 # comedy: a boing when someone is shocked
        if s.get("mood") == "shock" or s.get("react") == "shock": add(sfx, st + 0.05, boing(), 0.35)
        if s.get("enter"): add(sfx, st + 0.05, sweep(500, 1400, 0.5, 3), 0.12)
    if kd == "darbar":                                   # deep drum hit
        add(sfx, st + 0.05, thump(), 0.4); add(sfx, st + 0.3, thump(), 0.3)
    if kd == "divine":                                   # warm chord + sparkle
        add(bed, st, pad([146.83, 220, 293.66, 369.99], d), 0.7)
        for j, f in enumerate([587.33, 659.26, 739.99, 880, 987.77, 1174.66]):
            add(sfx, st + 0.1 + j*0.06, sweep(f, f, 1.2, 3.5), 0.06)
    if kd in ("walk", "meet"):                           # birds + soft wind
        tb = 0.6
        while tb < d:
            add(sfx, st + tb, chirp(), 0.045); add(sfx, st + tb + 0.17, chirp(), 0.04); tb += rng.uniform(1.4, 3.2)
        add(sfx, st, band(noise(d), 200, 900) * np.minimum(1, tarr(d) / 0.5), 0.02)
    if kd == "walk" or (kd == "meet" and s.get("arrive")):   # footsteps
        tw, end = 0.1, (d if kd == "walk" else 2.8)
        while tw < end:
            tq = tarr(0.09); add(sfx, st + tw, band(noise(0.09), 60, 500) * np.exp(-tq*40), 0.07); tw += math.pi / 6.5


def build_audio(tl, voices, path, seed):
    """Mix voices, music and effects for a timeline and write a stereo WAV."""
    total = tl["total"]; n = int((total + 0.6) * SR)
    voice, sfx = np.zeros(n), np.zeros(n)
    for ph in tl["phrases"]:
        x = voices[ph["idx"]]
        add(voice, ph["start"], reverb(x) if ph["spk"] == "K" else x)
    bed = music_bed(tl.get("type"), n, total, seed)
    rng = random.Random(seed)
    for si, s in enumerate(tl["shots"]):
        shot_sfx(sfx, bed, s, si == 0, rng)
    last = tl["shots"][-1]
    if tl.get("type") == "comedy":
        add(sfx, 0.12, sweep(400, 1200, 0.35, 6), 0.25)                       # opening pop
        add(sfx, tl["phrases"][-1]["end"] + 0.1, rimshot(), 0.55)             # punchline: ba-dum-tss
    else:
        add(sfx, 0.12, bell(392, 5.0), 0.35)                             # opening temple bell (lower, longer)
        add(sfx, tl["phrases"][-1]["start"], pluck(523.25, 2.0), 0.5)    # last line: one santoor note
        add(sfx, last["start"] + last["narr_end"] + 0.4, bell(587, 3.0), 0.25)   # end card

    # duck the music under the voice, fade in/out, normalise
    a = np.abs(voice); k = int(0.25 * SR); cs = np.cumsum(np.concatenate([[0], a]))
    env = np.zeros(n); env[k//2: k//2 + n - k + 1] = (cs[k:] - cs[:-k]) / k
    bed *= 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    bed *= np.clip((total - np.arange(n) / SR) / 1.8, 0, 1) * np.minimum(1, np.arange(n) / SR / 0.8)
    mix = voice + bed * 0.13 + sfx * 0.6
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
