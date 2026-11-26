# Costs

Actually paid: **$0**. The numbers below are measured from `runs.jsonl`. List-price equivalents use the rates in the second table.

## Free tiers as actually found (date: ___)

| Service | Limit found | Notes |
|---|---|---|
| Gemini API (TTS) | | requests/day, requests/minute |
| Cloudflare Workers AI | | neurons/day, about N images |
| Kaggle GPU | | hours/week, session limit |

## Per stage (measured)

| Stage | Model | Calls | Mean latency (s) | GPU min | List-price rate | Equivalent $ |
|---|---|---|---|---|---|---|
| narration | Gemini TTS | | | – | $__/1M audio tokens | |
| keyframes | FLUX schnell (CF) | | | – | ~$0.0011/image | |
| shots | Wan 2.2 TI2V-5B (T4) | | | | ~$0.35/T4-hour | |
| music | ACE-Step 1.5 (T4) | | | | ~$0.35/T4-hour | |
| assemble | FFmpeg (local) | – | | – | $0 | 0 |
| **Total** | | | | | | |

Compute these from the log with:

```bash
python -c "import json,collections as c;d=c.defaultdict(list);[d[r['stage']].append(r) for r in map(json.loads,open('runs.jsonl',encoding='utf-8'))];[print(k,len(v),round(sum(x.get('latency_s',0) for x in v)/len(v),1),round(sum(x.get('gpu_minutes',0) for x in v),1),round(sum(x.get('cost_usd_equiv',0) for x in v),4)) for k,v in d.items()]"
```

## Frontier comparison (if you had access)

| Same shot | Model | Latency | Cost | Blind preference (n=) |
|---|---|---|---|---|
