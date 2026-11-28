"""All settings in one place: video size, paths, voices, speaker names and the story formats."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
STATE = os.path.join(ROOT, "state")
SPRITE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", OUT), "reel_sprites")   # character layer cache
os.makedirs(SPRITE_DIR, exist_ok=True)

# ---- video
W, H, FPS = 1080, 1920, 30
SS = 2              # everything is drawn at 2x and scaled down (smooth edges)
SR = 44100          # audio sample rate
GAP = 0.3           # pause between two lines of the same shot (s)
XF = 0.35           # crossfade between shots (s)

FONT_CAP = os.path.join(ROOT, "fonts", "Mukta-ExtraBold.ttf")    # captions, buttons
FONT_B = os.path.join(ROOT, "fonts", "Mukta-Bold.ttf")           # small text, tags
FONT_TITLE = os.path.join(ROOT, "fonts", "Bangers-Regular.ttf")  # title card, stickers, end card

# ---- channel look
CHANNEL_NAME = "NIKHIL PAL"          # small watermark in the top-right corner
SAFFRON, PLUM, TEAL, CREAM = (255, 156, 40), (44, 22, 58), (24, 140, 146), (252, 244, 226)

# ---- speakers: edge-tts voice, rate, pitch
VOICES = {
    "N": ("hi-IN-MadhurNeural", "-6%", "-3Hz"),    # narrator: a calm male storyteller
    "K": ("hi-IN-MadhurNeural", "-14%", "-9Hz"),   # Shri Krishna (gets a soft reverb)
    "A": ("hi-IN-MadhurNeural", "+5%", "+9Hz"),    # Arjun
    "P": ("hi-IN-MadhurNeural", "-4%", "-13Hz"),   # ordinary man (devotee, villager)
    "R": ("hi-IN-MadhurNeural", "-10%", "-18Hz"),  # Raja
    "C": ("hi-IN-MadhurNeural", "+8%", "+4Hz"),    # Chatur, the clever man
    "T": ("hi-IN-MadhurNeural", "+14%", "+12Hz"),  # Chintu: young, quick, cheeky
    "M": ("hi-IN-MadhurNeural", "-4%", "-16Hz"),   # Mama: older, heavy, old-school
    "Y": ("hi-IN-SwaraNeural", "+8%", "+4Hz"),     # Pinki: Chintu's sharp sister
}
# caption tag shown above a character's lines: (default name, colour). The narrator has no tag.
TAGS = {"K": ("Shri Krishna", (40, 96, 190)), "A": ("Arjun", (24, 118, 126)), "P": ("Bhakt", (82, 94, 152)),
        "R": ("Raja", (94, 38, 134)), "C": ("Chatur", (40, 130, 86)),
        "T": ("Chintu", (24, 140, 146)), "M": ("Mama", (176, 110, 30)), "Y": ("Pinki", (200, 60, 120))}
BLINK_OFF = dict(K=0.0, A=1.3, P=2.2, R=0.5, C=1.8, G=2.9, T=0.7, M=2.0, Y=1.1)   # so characters don't blink in sync

# ---- story formats. Adding a format = add an entry here + its scene(s) in scenes.py + a section in writer.PROMPT.
FORMATS = {
    "paheli": dict(
        parts=2, label="CHATUR KA NYAY",
        scenes=("darbar",), default_scene="darbar", speakers=("N", "R", "C"), named="C",   # p_name is shown as C's caption tag
    ),
    "devotional": dict(
        parts=3, label="BHAKT KATHA",
        scenes=("walk", "meet", "divine"), default_scene="meet", speakers=("N", "K", "A", "P"), named="P",
    ),
    "comedy": dict(
        parts=1, label="CHINTU AUR MAMA",
        scenes=("gali", "ghar", "dukaan"), default_scene="gali", speakers=("N", "T", "M", "Y"), named=None,
    ),
}
KINDS = tuple(FORMATS)                  # every format the engine can draw
KATHA_KINDS = ("paheli", "devotional")  # the daily katha slot takes turns between these
COMEDY_STYLES = ("doodle", "desi")      # comedy reels take turns between the two looks
# what each daily slot (IST, see reels/schedule.py) posts: two trending comedy reels and one katha part
SLOT_KIND = {"12:00": "comedy", "16:00": "comedy", "19:00": "katha"}
MOODS = ("sad", "neutral", "happy", "angry", "shock")
ICONS = ("gallows", "sword", "question", "tick", "cross", "coin", "door", "lamp", "crown", "clock")
