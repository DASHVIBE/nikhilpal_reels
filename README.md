# Nikhil Pal Reels 🎬

Roz **3 Hindi cartoon Shorts** apne aap bante hain aur YouTube par **12 PM, 4 PM aur 7 PM (IST)** publish hote hain.
GitHub Actions par chalta hai, laptop on rakhne ki zaroorat nahi.

- **12 PM aur 4 PM: Chintu Aur Mama** (`comedy`): us din ke trending topic par ek poora mazedaar reel (30-45 s).
  Chintu (shaitaan bhanja), Mama (kanjoos, jugaadu), Pinki (tez behen). Do look baari-baari:
  **doodle** (grey kagaz, bada safed sar, dandi body) aur **desi** (wahi chehre, rang bhare kurte aur gali/ghar/dukaan).
- **Subah ~4:30 baje trend research**: Claude web par dekhta hai aaj India me kya chal raha hai (mausam, tyohar, match,
  sale, viral trend) aur din ke comedy topic chunta hai (`state/trends.json`). Politics, dharm, haadse, asli log: kabhi nahi.
- **7 PM: katha**, series mein roz ek part:
  - **Chatur Ka Nyay** (`paheli`): darbar ka jaasoosi case (chori, jhootha daava, bantwara). Part 1 mein case + suraag,
    Part 2 mein Chatur ki chaal aur faisla. 2 parts.
  - **Bhakt Katha** (`devotional`): asli bhakton ki kathayein (Pundalik, Sudama, Vidur ...) aur Mahabharat ke anjaane raaz,
    Krishna-Arjun ke saath. 2-3 parts.
  - Ek series khatam hote hi agli dusre format ki.
- Claude pehle web par asli katha / lok kahani dhoondhta hai, phir poori series ek saath likhta hai.
  `references/avoid.md` mein likhi kahaniyan Claude kabhi nahi banata.
- 2D cartoon animation, Hindi awaaz, captions, music: sab code se banta hai, koi paid service nahi.

## Channel ka look
Katha: flat vector cartoon (lambe side-profile characters, mukut, pagdi, rang bhare kapde). Comedy: doodle aur desi doodle.
Backgrounds: shaam/neela-marble palette, mard narrator, neeche plum caption box, kone me saffron hook ribbon,
Bangers titles, iris transition, harmonium + santoor music, kone me `NIKHIL PAL` watermark (`config.CHANNEL_NAME`).

## Roz kya hota hai

```
Subah 4 baje ke baad pehla run: aaj ki trend research (state/trends.json)
Har ghante GitHub check karta hai: koi slot (12 PM / 4 PM / 7 PM) 3 ghante mein hai ya chhoot gaya?  ── haan ──►
  ├─ 12 PM / 4 PM: aaj ke agle trending topic par Claude se comedy reel (doodle aur desi baari-baari)
  ├─ 7 PM: state/series.json mein chal rahi katha ka agla part?  ── nahi ──► Claude se nayi series (sab parts)
  ├─ awaaz (edge-tts) → animation → reel.mp4
  ├─ video check (reels/qa.py): fail ho to upload NAHI, agle ghante dobara koshish
  ├─ YouTube upload, 3 ghante baad publish (12 PM / 4 PM / 7 PM)
  └─ state/ commit (history, series, aur fail hua ho to last_error.txt)
```
Claude fail ho jaye to `samples/` ki series use hoti hai (har format ki 2: Sardi Mein Nahana, Teen Shaadi Ek Din,
Pundalik Ki Eent, Barbarik Ka Sheesh Daan, Jaadui Lakdi Ka Nyay, Thaili Kiski?), taaki us din ki video na chhoote. Claude ki adhoori script dobara likhwayi jaati hai.
YouTube secrets na hon to scheduled run chupchaap ruk jaata hai (fail email nahi aata).

## Upload se pehle video check
Har video banne ke baad `reels/qa.py` asli mp4 ko jaanchta hai, sab sahi ho tabhi upload hota hai:
- **Picture:** 1080x1920, 30 fps, saare frame maujood (kuch kata ya chhoota nahi), koi kaali ya ruki hui tasveer nahi.
- **Awaaz:** audio track poora, aawaz na bahut dheemi na phati hui, beech me lambi khamoshi nahi, har caption ke
  waqt bolne wale ki awaaz sach me sunai deti hai.
- **Script:** har line video me aayi, har line ki awaaz poori (na kati na kheenchi), captions aur title khaali nahi.
- Awaaz me gadbad ho to awaaz dobara bana kar ek baar aur render hota hai. Phir bhi fail ho to video upload nahi
  hoti, run laal (fail) dikhta hai aur agla ghanta dobara koshish karta hai.
- Nateeja run ke page par **"Video check: PASS/FAIL"** me dikhta hai, aur `qa.json` video ke saath Artifacts me.

## Code ka naksha (`reels/`)

| File | Kaam |
|---|---|
| `config.py` | **Saari settings**: video size, voices, caption names, aur dono formats ke rules |
| `pipeline.py` | Roz ka run: slot ke hisaab se comedy ya katha → render → upload → state save |
| `qa.py` | Upload se pehle video check: frames, awaaz, captions, kuch chhoota to nahi |
| `trends.py` | Subah ki trend research (Claude + web search) → `state/trends.json` |
| `comedy.py` | Comedy ke characters (Chintu, Mama, Pinki), dono look, gali / ghar / dukaan |
| `writer.py` | Claude ko prompt + JSON schema; poori series likhwata hai |
| `timeline.py` | Script ko render-ready banata hai: camera, mood, awaaz, timing |
| `render.py` | Har frame jodta hai (shot + overlays) aur ffmpeg se mp4 banata hai |
| `scenes.py` | Backgrounds aur shots: jungle (walk, meet, divine), darbar |
| `vector.py` | Katha ke characters, flat vector look (side profile): Krishna, Arjun, bhakt, Raja, Chatur, sipahi |
| `characters.py` | Purane ink characters (ab sirf zameen par parchhai ke liye) |
| `canvas.py` | Flat "ink" cartoon canvas (motti outline + cel shadow) + sprite cache |
| `overlays.py` | Captions, title card, end card, hook bar, sticker, icon cards |
| `audio.py` | Awaaz, lip-sync, music (harmonium, santoor, paheli me tik-tik + dhadkan), sound effects |
| `youtube.py` | YouTube upload |
| `util.py` | Chhote helpers (easing, curves, drawing pen) |

Script ka format (Claude jo JSON likhta hai) `writer.py` mein `SCHEMA` hai. Example: `samples/nyay_01.json`.

## One-time setup

### 1. Claude (kahani likhne ke liye)
**A) Claude Pro/Max subscription se (recommended)**
1. Laptop terminal mein: `npm install -g @anthropic-ai/claude-code` phir `claude setup-token`
2. Browser mein login → Allow → terminal mein token aayega (1 saal valid).
3. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:
   `CLAUDE_CODE_OAUTH_TOKEN` = wo token

**B) Claude API key se (pay-as-you-go):** secret `ANTHROPIC_API_KEY`. Ye set ho to isi ko priority milti hai.

### 2. YouTube upload permission
1. https://console.cloud.google.com par project banaiye, **YouTube Data API v3** enable kijiye.
2. **Google Auth Platform**: External app, scopes `youtube.upload` + `youtube.readonly`,
   Branding mein home page / privacy policy links, phir **Audience → Publish app → In production**.
   (Testing mode mein token 7 din mein expire ho jata hai.)
3. **Clients → Create client → Desktop app** → JSON download (repo ke bahar rakhiye).
4. `pip install google-auth-oauthlib` phir `python scripts/get_youtube_token.py "<json ka path>"`
5. Jo 3 values aayengi unhe GitHub Secrets mein daaliye: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

> ⚠️ Keys aur `client_secret.json` kabhi commit mat kijiye, chat mein mat bhejiye.

### 3. Test
GitHub → **Actions → Daily Reel → Run workflow**: pehle `upload = false` (video Artifacts mein milegi), phir `true`.

**Check workflow:** har code push par GitHub saare samples ka preview banata hai (Actions → Check → `previews` artifact).
Wo laal (fail) ho to code me kuch toota hai.

**YouTube audit:** naye API projects ki videos **Private** rehti hain jab tak
[API audit](https://support.google.com/youtube/contact/yt_api_form) approve na ho. Tab tak Studio mein Public kar dijiye.

## Apni kahaniyan aur style
`references/` dekhiye: `stories/paheli/` ya `stories/devotional/` mein `.txt` file daaliye, wo pehle use hogi.
`style.md` mein likhe notes Claude har baar padhta hai.

## Laptop par chalana
```
pip install -r requirements.txt
python -m reels.pipeline --script samples/nyay_01.json --part 1 --no-upload   # video: out/reel.mp4
python -m reels.pipeline --script samples/nyay_01.json --part 2 --preview     # sirf preview image
```

## Kuch badalna ho to
| Kya | Kahan |
|---|---|
| Post ke time (slots) | `reels/schedule.py` → `SLOTS` |
| Kahani ka style / rules | `writer.py` → `FORMAT_TEXT`, `RULES` |
| Voices, caption names | `config.py` |
| Naya format (jaise Ramayan) | `config.FORMATS` + scene `scenes.py` mein + characters `characters.py` mein + `writer.FORMAT_TEXT` |
| Claude kyun fail hua | `state/last_error.txt` |
