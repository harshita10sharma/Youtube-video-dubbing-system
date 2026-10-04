# Automated Video Dubbing System

A Python pipeline that takes a YouTube video in any spoken language and produces
an English-dubbed version: the same video, with the original speech transcribed,
translated to English, and re-spoken in a synthesized English voice, aligned back
onto the original timeline.

## Objective

Given a YouTube URL (in German, French, Hindi, or any other language), the system:

1. Downloads the source video.
2. Transcribes its speech and automatically detects the source language.
3. Translates the transcript into natural English.
4. Synthesizes English speech from the translation.
5. Places the generated speech on the original timestamps.
6. Replaces the original audio track with the English audio.
7. Saves the final dubbed MP4 to disk.

Progress is printed to the terminal at every stage.

## Architecture / Pipeline

```
YouTube URL
   |
   v
[1] downloader.py      -> yt-dlp downloads the video (data/videos/source.mp4)
   |
   v
[2] audio_extractor.py -> ffmpeg extracts a 16kHz mono WAV (data/audio/original.wav)
   |
   v
[3] transcriber.py     -> Faster-Whisper transcribes speech and detects the
   |                      source language (data/transcripts/transcript.json)
   v
[4] translator.py      -> Indic languages route through indic_translator.py
   |                      (IndicTrans2); everything else uses deep-translator's
   |                      GoogleTranslator. Timestamps are preserved
   |                      (data/transcripts/translated.json)
   v
[5] tts_engine.py       -> Edge TTS synthesizes one English audio clip per
   |                       translated segment (data/audio/tts/seg_NNNN.mp3)
   v
[6] merger.py           -> pydub places each clip at its original segment's
   |                       start timestamp on a silent timeline the length of
   |                       the source video, borrowing the silent gap or
   |                       speeding up (atempo) clips that overrun
   |                       (data/audio/dubbed_audio.wav)
   v
[7] video_merger.py     -> ffmpeg copies the original video stream and mixes
   |                       in the new audio track as AAC (loudness-
   |                       normalised), video not re-encoded
   |                       (data/output/final_dubbed_video.mp4)
   v
Final dubbed video
```

`app.py` orchestrates all seven steps in order and prints progress, timing, and
the final output path.

## Technologies Used

| Stage | Tool |
|---|---|
| Download | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Audio extraction / muxing | [FFmpeg](https://ffmpeg.org/) |
| Transcription + language detection | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| Translation (Indic languages) | [IndicTrans2](https://github.com/AI4Bharat/IndicTrans2) via IndicTransToolkit |
| Translation (all other languages) | [deep-translator](https://github.com/nidhaloff/deep-translator) (Google Translate backend) |
| Speech synthesis | [edge-tts](https://github.com/rany2/edge-tts) (`en-US-AriaNeural`); optional [Chatterbox](https://github.com/resemble-ai/chatterbox) voice cloning |
| Timeline alignment | [pydub](https://github.com/jiaaro/pydub) |

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`requirements.txt` covers the core pipeline. `IndicTransToolkit` (used only for
Indic-language translation) requires a C++ build toolchain on Windows
(Microsoft Visual C++ Build Tools) to install. If you only need to dub
non-Indic-language videos, you can skip installing it — the rest of the
pipeline runs without it; the code lazily imports IndicTransToolkit only when
an Indic language is actually detected.

### FFmpeg setup

FFmpeg and ffprobe must be available for both the pipeline's own subprocess
calls and libraries it depends on (yt-dlp, pydub) that shell out to them
independently. `src/ffmpeg_utils.py` resolves both executables once:

1. It first looks for `ffmpeg`/`ffprobe` on the system `PATH`.
2. If either is missing, it falls back to a known local install directory and
   also adds that directory to the process `PATH`, so third-party libraries
   that look up `ffmpeg`/`ffprobe` by name (rather than accepting an explicit
   path) can find them too.

For the most reliable setup, install FFmpeg and add its `bin` directory to
your system `PATH` directly.

## Usage

```bash
python app.py                                   # prompts for a YouTube URL
python app.py --url "https://www.youtube.com/watch?v=..."
python app.py --video data/videos/source.mp4 --resume   # reuse earlier work

# Voice cloning (GPU): clones the speaker heard in the video automatically
python app.py --video data/videos/source.mp4 --tts-backend chatterbox

# ...or clone a specific voice sample instead
python app.py --video data/videos/source.mp4 --tts-backend chatterbox \
    --reference-voice data/audio/reference.wav

# Web interface (paste a URL, confirm the voice sample, get the video)
pip install gradio
python web_app.py
```

The final dubbed video is written to `data/output/final_dubbed_video.mp4`.
Logs are also appended to `logs/pipeline.log`. Run the tests with
`python -m pytest`.

## Language Detection

The source language is never hardcoded. `transcriber.py` uses
Faster-Whisper's built-in language detection during transcription, and that
detected language code drives which translation backend is used.

The Whisper model adapts to the hardware: `large-v3` on a GPU (much better
for Hindi and other Indian languages) and `small` on CPU. Set the
`WHISPER_MODEL` environment variable to override. If IndicTrans2 cannot load
(for example an incompatible `transformers` version), translation falls back
to Google Translate instead of failing; the Colab notebook pins
`transformers==4.46.3` for this reason.

## Translation Architecture

`translator.py` first merges short, fragmented Whisper segments into
sentence-level chunks (bounded by a maximum gap and duration) so the
translator has enough context to produce natural phrasing rather than
translating isolated fragments. It then checks whether the detected language
is one of the Indic languages IndicTrans2 supports:

- **Indic languages** (Hindi, Tamil, Bengali, and others listed in
  `src/indic_translator.py`) are translated with the IndicTrans2 model
  (`ai4bharat/indictrans2-indic-en-dist-200M`).
- **All other languages** are translated with `deep-translator`'s
  `GoogleTranslator`, with retry handling and periodic checkpointing to
  `data/transcripts/translated.json` so progress survives an interruption.

Original segment timestamps are preserved through translation.

## TTS Architecture

`tts_engine.py` generates one English audio clip per translated segment. Two
backends are available:

- `edge` (default): Microsoft Edge neural TTS (`en-US-AriaNeural`), free and
  runs on any machine.
- `chatterbox`: voice cloning from a reference WAV (GPU recommended). Retries
  once on failure and frees GPU memory between clips.

### Choosing the voice to clone

The reference voice comes from the video itself (`voice_reference.py`). It
measures loudness in 100 ms frames, scores every 12-second window for mostly
continuous speech with steady loudness (music, applause and crowd noise make
loudness jump), and cuts the three best non-overlapping windows from the
original video at 24 kHz. This takes about a second and needs no model.

- Command line: the best sample is used automatically.
- Web interface (`web_app.py`): the user listens to the samples, picks one
  (or uploads their own), and presses one button to create the dubbed video.

One voice is used for the whole video; multiple speakers are not separated.

Each clip is saved independently so a failure on one segment does not block
the rest, and with `--resume` existing clips are reused.

## Timestamp Alignment

`merger.py` builds a silent audio track the length of the source video and
overlays each TTS clip at its original segment's start time. The fitting
rules live in `timing.py` and are tried in order so words are never cut off
unnecessarily:

1. The clip fits its own segment: unchanged.
2. The clip may use the silent gap before the next segment starts: unchanged.
3. Still too long: sped up with ffmpeg's pitch-preserving `atempo` filter,
   capped at 1.5x.
4. Still too long after the cap: trimmed with a short fade-out (last resort).

A timing report (clips sped up / trimmed) is logged. This preserves
timestamps but does not guarantee frame-perfect lip sync, since TTS duration
naturally differs from the original speech.

## Final Video Generation

`video_merger.py` combines the original video with the generated English
audio track using FFmpeg: the video stream is copied unchanged (`-c:v copy`,
no re-encoding), and the new audio is encoded as AAC. The audio is loudness-normalised to -16 LUFS so clips of varying level sound
consistent, and `-shortest` caps the output at the shorter of the two streams.

## Output Location

- Transcript: `data/transcripts/transcript.json`
- Translated transcript: `data/transcripts/translated.json`
- Per-segment TTS clips: `data/audio/tts/`
- Assembled English audio track: `data/audio/dubbed_audio.wav`
- **Final dubbed video: `data/output/final_dubbed_video.mp4`**
- Log: `logs/pipeline.log`

None of these runtime artifacts are committed to the repository (see
`.gitignore`) since they are large, regenerable outputs.

## Running on Google Colab (voice cloning)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/harshita10sharma/Youtube-video-dubbing-system/blob/main/Colab_notebook/Dubbing_Pipeline_Colab.ipynb)

`Colab_notebook/Dubbing_Pipeline_Colab.ipynb` runs this repository on a free
Colab T4 GPU: it clones the repo, installs dependencies and starts the web
interface (`web_app.py`) with a public link. The user pastes a YouTube URL,
listens to the speaker voice samples found in the video, confirms one, and
receives the dubbed video. A command-line cell is included as an alternative.

Everyone who opens the notebook uses **their own** Colab GPU session; nothing
runs on the author's account. YouTube sometimes blocks downloads from Colab,
so the web page also accepts an uploaded video file.

`Colab_notebook/Chatterbox_Production_Integration_Test.ipynb` is the earlier,
self-contained experiment that produced a voice-cloned dub of a Hindi TEDx
talk. It is kept as a reference; its timeline step truncated clips to their
segment length (70 of 90 segments differed by more than 1 s), which the
`timing.py` rules above replace.

## Known Limitations

- Generated speech duration does not always match the original segment
  duration; clips borrow silent gaps or are sped up (capped at 1.5x), so
  timing is close but not frame-accurate.
- A single fixed English voice (`en-US-AriaNeural`) is used for the entire
  video; the system does not distinguish between multiple speakers or clone
  the original speaker's voice unless the Chatterbox backend is used.
- Translation quality for non-Indic languages depends on Google Translate via
  `deep-translator`; it is generally accurate for meaning but is a
  general-purpose translator rather than one tuned to any specific language
  pair.
- IndicTrans2 translation requires `IndicTransToolkit`, which needs a C++
  build toolchain to install on Windows.

## Testing / Results

The full pipeline was validated end-to-end on a short public video
(`https://www.youtube.com/watch?v=jNQXAC9IVRw`, 19 seconds, English source)
to confirm every stage — download, extraction, transcription with language
detection, translation, TTS, timeline alignment, and muxing — runs cleanly
before longer runs were attempted. Additional runs on longer, non-English
source videos (a ~30 minute and a ~2 hour video) were performed as part of
the project submission; see the submission package for those source videos,
outputs, and processing times.

## Project Structure

```
Youtube-video-dubbing-system/
├── app.py                       # Pipeline entry point (CLI) and stage functions
├── web_app.py                   # Gradio interface: URL -> confirm voice -> dubbed video
├── requirements.txt
├── tests/                       # pytest unit tests
├── src/
│   ├── downloader.py             # yt-dlp video download
│   ├── audio_extractor.py        # ffmpeg audio extraction
│   ├── transcriber.py            # Faster-Whisper transcription + language detection
│   ├── translator.py             # Translation routing + segment merging
│   ├── indic_translator.py       # IndicTrans2 backend for Indic languages
│   ├── tts_engine.py             # Edge TTS / Chatterbox speech synthesis
│   ├── timing.py                 # Rules for fitting clips into time slots
│   ├── voice_reference.py        # Finds clean speaker samples for voice cloning
│   ├── languages.py              # Language-code tables (no heavy imports)
│   ├── merger.py                 # Timestamp-based audio timeline alignment
│   ├── video_merger.py           # ffmpeg audio/video muxing
│   ├── ffmpeg_utils.py           # Shared ffmpeg/ffprobe path resolution
│   └── logger.py                 # Console + file logging
├── data/                         # Runtime artifacts (git-ignored)
│   ├── videos/
│   ├── audio/
│   ├── transcripts/
│   └── output/
└── Colab_notebook/
    ├── Dubbing_Pipeline_Colab.ipynb                    # GPU runner for this repo
    └── Chatterbox_Production_Integration_Test.ipynb   # Earlier Chatterbox experiment
```
