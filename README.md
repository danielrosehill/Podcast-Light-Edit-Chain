# Podcast Light Edit Chain

A one-command light edit for solo spoken-word recordings (voice notes, podcast monologues) to make them fit to publish:

1. **Cut fillers.** [Uhm](https://huggingface.co/desert-ant-labs/uhm) (Desert Ant Labs, ONNX, CPU) labels every 20 ms frame as `uh` / `um` / `hmm` / `and` / `other` / not-filler straight from the audio, with no ASR. Runs of filler frames are cut, and the joins get 10 ms equal-power crossfades.
2. **Shorten long pauses.** An energy gate (adaptive: 10 dB over the room floor) runs on the de-filled audio. Pauses over 0.8 s are shortened to 0.5 s, and shorter pauses are left alone.
3. **EQ fitted to the voice.** The script computes the octave-band long-term spectrum of the speech frames and fits a straight line (in log-frequency) through it. Bumps and dips against that line, which are mostly mic and room colouration, are corrected by 60%, capped at ±3 dB. The line itself is the voice and is left alone. Then an 80 Hz high-pass, a gentle 2.5:1 compressor and a light de-esser.
4. **Loudness.** Two-pass ffmpeg `loudnorm` to -16 LUFS / -1.5 dBTP, exported as a 128 kbps mono MP3.

Every cut lands in `<out>.edits.json` (start, end, kind, label/confidence), together with the fitted preset and the exact ffmpeg filter chain, so an edit can be audited or replayed.

## Run

Needs `uv`, `ffmpeg`, `ffprobe`. The Uhm weights (51 MB) download from Hugging Face on first run.

```bash
uv sync
uv run python podcast_light_edit.py notes.mp3                       # -> notes.edited.mp3 + notes.edited.mp3.edits.json
uv run python podcast_light_edit.py notes.mp3 --dry-run             # detect and write the edit list only
uv run python podcast_light_edit.py notes.mp3 --save-preset presets/me.json   # keep the fitted EQ
uv run python podcast_light_edit.py next.mp3 --preset presets/me.json         # reuse it
```

Main options: `--filler-threshold` (0.6), `--min-filler` (0.12 s), `--filler-pad` (0), `--fillers uh,um,hmm`, `--max-silence` (0.8 s), `--keep-silence` (0.5 s), `--silence-db` (fixed gate instead of adaptive), `--eq-strength` (0.6), `--eq-max` (3 dB), `--lufs` (-16), `--no-fillers` / `--no-silence` / `--no-eq`, `--probs <file.npy>` (caches Uhm output so re-tuning skips the 3-minute detection pass).

Speed: on a 16-thread laptop CPU (no GPU), detection took about 3 minutes for 22.5 minutes of audio, and the whole run about 3.5 minutes.

## Demo: 2026-10-30, a 22.5-minute voice note for the Hebrish podcast

Source: one solo recording, phone-quality, outdoors, English with some Hebrew. Measured on 2026-10-30:

| | Value |
|---|---|
| Duration | 22:30 → 21:04 (-6.4%) |
| Fillers cut | 79 spans, 42.7 s |
| Pauses shortened | 71, 41.6 s removed (gate -31.1 dBFS, adaptive) |
| Loudness | -21.0 LUFS before normalisation → -16.7 LUFS out |
| Fitted EQ | -3.0 dB @ 500 Hz, -1.7 dB @ 2 kHz, +2.3 dB @ 8 kHz (1-octave bells) |

Files: [`demo/2026-10-30-edits.json`](demo/2026-10-30-edits.json) (every cut), [`demo/2026-10-30-filler-eval.json`](demo/2026-10-30-filler-eval.json), [`presets/daniel-voice.json`](presets/daniel-voice.json) (the fitted preset with its band profile).

### How good is the filler detection?

The reference is AssemblyAI (`universal`, `disfluencies: true`) on the original file, which tagged 98 fillers (62 "um", 35 "uh", 1 "ah") with word timestamps. [`scripts/eval_fillers.py`](scripts/eval_fillers.py) scores a cut list against that reference, and [`scripts/sweep_fillers.py`](scripts/sweep_fillers.py) grid-searches the settings. A real word counts as clipped when a cut takes at least 80 ms and at least 30% of it.

| Setting | Cuts | Recall | Precision | Real words clipped |
|---|---:|---:|---:|---:|
| thr 0.4, pad 30 ms | 118 | 0.84 | 0.69 | 41 |
| thr 0.5, pad 30 ms (first try) | 101 | 0.76 | 0.74 | 27 |
| **thr 0.6, pad 0, min 0.12 s (default)** | **79** | **0.68** | **0.85** | **10** |
| thr 0.7, pad 0 | 62 | 0.52 | 0.84 | 5 |

The default favours precision: for a file going public, a leftover "um" costs less than a clipped word. Precision is a lower bound, because AssemblyAI misses some fillers itself (for example a short "m" at 0:21 that it transcribes as a word). Adding Uhm's `other` class raises recall by about 0.08 but clips roughly twice as many words, so it is off by default.

Listening check: not done by a human yet. The numbers above are the only verification so far.

## Caveats

- Uhm is trained on English. Hebrew filler sounds ("eh", "ze") are not targeted, and its other languages are untested.
- **Uhm licence:** the [Desert Ant Labs Source-Available License 1.0](https://license.desertant.com/1.0), free for most apps, with a commercial licence required at scale. This repo does not redistribute the weights: they are fetched from Hugging Face at run time. The code here is MIT.
- The EQ fit assumes one speaker and one mic per file.
- The silence gate needs a recording with some real pauses. On a continuously noisy file, pass `--silence-db`.

## Also packaged as

A skill in the [audio-production Claude Code plugin](https://github.com/danielrosehill/Claude-Audio-Production-Plugin) (`light-edit`), which runs this script end to end.

## Licence

MIT (code). Model weights: see above.
