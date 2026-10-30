"""Grid-search the filler settings against an AssemblyAI disfluency transcript.

  uv run python -I scripts/sweep_fillers.py <audio> <assemblyai.json> <probs-cache.npy>

The transcript is the --transcript file written by eval_fillers.py; the probs cache is written on
first run (about 3 min of CPU for 22 min of audio) and reused after. "clipped_words" counts cuts
taking >= 80 ms and >= 30% of a non-filler word, the same rule as eval_fillers.py.
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import podcast_light_edit as p
audio, transcript, cache = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
if cache.exists():
    probs = np.load(cache)
else:
    probs = p.filler_probs(p.resample(p.decode(audio, p.SR), p.SR, p.UHM_SR), 'uhm-web-fp16.onnx'); np.save(cache, probs)
t = json.loads(transcript.read_text())
F = {"um","uh","hmm","mm","er","ah"}
W = [(w['start']/1000, w['end']/1000, w['text'].lower().strip('.,?!-')) for w in t['words']]
ref = [w for w in W if w[2] in F]; oth = [w for w in W if w[2] not in F]
ov = lambda a0,a1,b0,b1: min(a1,b1)-max(a0,b0)
for cls in (["uh","um","hmm"], ["uh","um","hmm","other"]):
  for thr in (0.4,0.5,0.6,0.7):
    for pad in (0.0,0.03):
      for mn in (0.08,0.12,0.16):
        score = probs[:, [p.UHM_LABELS[c] for c in cls]].sum(1)
        cuts = [(s*0.02-pad, e*0.02+pad) for s,e in p.merge_spans(score>=thr, 0.02, 0.06, mn)]
        rec = np.mean([any(ov(r[0],r[1],a,b)>0 for a,b in cuts) for r in ref])
        prec = np.mean([any(ov(a,b,r[0],r[1])>0 for r in ref) for a,b in cuts]) if cuts else 0
        clip = sum(any(ov(a,b,w[0],w[1]) >= max(0.08, 0.3*(w[1]-w[0])) for w in oth) for a,b in cuts)
        print(f"{'+other' if len(cls)>3 else 'base':6} thr={thr} pad={pad} min={mn} cuts={len(cuts):3} recall={rec:.2f} prec={prec:.2f} clipped_words={clip}")
