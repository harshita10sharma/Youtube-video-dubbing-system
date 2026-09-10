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
   |                       the source video, speeding up clips that overrun
   |                       their segment (data/audio/dubbed_audio.wav)
   v
[7] video_merger.py     -> ffmpeg copies the original video stream and mixes
   |                       in the new audio track as AAC, without re-encoding
   |                       video (data/output/dubbed_video.mp4)
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
| Speech synthesis | [edge-tts](https://github.com/rany2/edge-tts) (`en-US-AriaNeural`) |
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
python app.py
```

You will be prompted for a YouTube URL:

```
Enter YouTube URL: https://www.youtube.com/watch?v=...
```

The final dubbed video is written to `data/output/dubbed_video.mp4`.

## Language Detection

The source language is never hardcoded. `transcriber.py` uses
Faster-Whisper's built-in language detection during transcription, and that
detected language code drives which translation backend is used.

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

`tts_engine.py` generates one English audio clip per translated segment using
Microsoft Edge's neural TTS (`en-US-AriaNeural`), a free, natural-sounding
voice. Each clip is saved independently so a failure on one segment does not
block the rest.

## Timestamp Alignment

`merger.py` builds a silent audio track the length of the source video and
overlays each TTS clip at its original segment's start time. If a generated
clip is longer than the time available before the next segment starts, it is
sped up (up to 1.35x, using pydub's crossfaded `speedup`) to fit without
overlapping into the next segment; if it still doesn't fit, it is truncated.
This is a practical, timestamp-preserving approach — it does not guarantee
frame-perfect lip sync, since TTS output duration naturally differs from the
original speech duration.

## Final Video Generation

`video_merger.py` combines the original video with the generated English
audio track using FFmpeg: the video stream is copied unchanged (`-c:v copy`,
no re-encoding), and the new audio is encoded as AAC. `-shortest` caps the
output at the shorter of the two streams.

## Output Location

- Transcript: `data/transcripts/transcript.json`
- Translated transcript: `data/transcripts/translated.json`
- Per-segment TTS clips: `data/audio/tts/`
- Assembled English audio track: `data/audio/dubbed_audio.wav`
- **Final dubbed video: `data/output/dubbed_video.mp4`**

None of these runtime artifacts are committed to the repository (see
`.gitignore`) since they are large, regenerable outputs.

## Colab Chatterbox Reference

`Colab_notebook/Chatterbox_Production_Integration_Test.ipynb` is a separate,
previously validated Colab pipeline that used Chatterbox TTS with a reference
voice sample to produce a higher-fidelity dub of a Hindi TEDx talk, including
voice-timbre matching to the original speaker. It demonstrates that the same
download → transcribe → translate → synthesize → align → mux architecture
produces a good result with a different TTS backend. It is kept as a
reference artifact and is not part of the local pipeline in this repository,
which uses Edge TTS as recommended by the assignment.

## Known Limitations

- Generated speech duration does not always match the original segment
  duration exactly; segments that run long are sped up (capped at 1.35x) or
  truncated rather than perfectly time-stretched, so timing is close but not
  frame-accurate.
- A single fixed English voice (`en-US-AriaNeural`) is used for the entire
  video; the system does not distinguish between multiple speakers or clone
  the original speaker's voice locally (this exists only in the separate
  Colab Chatterbox reference).
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
├── app.py                       # Pipeline entry point
├── requirements.txt
├── src/
│   ├── downloader.py             # yt-dlp video download
│   ├── audio_extractor.py        # ffmpeg audio extraction
│   ├── transcriber.py            # Faster-Whisper transcription + language detection
│   ├── translator.py             # Translation routing + segment merging
│   ├── indic_translator.py       # IndicTrans2 backend for Indic languages
│   ├── tts_engine.py             # Edge TTS speech synthesis
│   ├── merger.py                 # Timestamp-based audio timeline alignment
│   ├── video_merger.py           # ffmpeg audio/video muxing
│   ├── ffmpeg_utils.py           # Shared ffmpeg/ffprobe path resolution
│   └── logger.py                 # Timestamped console logging
├── data/                         # Runtime artifacts (git-ignored)
│   ├── videos/
│   ├── audio/
│   ├── transcripts/
│   └── output/
└── Colab_notebook/
    └── Chatterbox_Production_Integration_Test.ipynb   # Chatterbox reference pipeline
```
