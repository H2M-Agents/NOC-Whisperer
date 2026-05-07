# NOC Whisperer — Evaluation Results

> This file is updated after each training job and evaluation run.
> Final numbers reported in Week 16 presentation.

---

## Training Results

### Normalizer Agent — SFT (Session 12)
| Metric | Value |
|---|---|
| Base model | Qwen/Qwen2.5-7B-Instruct |
| Initial loss | 3.896 |
| Final loss | 0.541 |
| Token accuracy (end of training) | 80.9% |
| Training time | 7 minutes |
| Average train loss | 0.917 |
| GPU | RTX 4060 Ti 16GB |
| Epochs | 3 |
| Batch size | 1 (grad_accum=4, effective=4) |
| Quantization | 4-bit NF4 via bitsandbytes |
| Checkpoint | checkpoints/normalizer_sft_final/ |

### Normalizer Agent — RLVR (Session 14)
| Metric | Value |
|---|---|
| Base checkpoint | checkpoints/normalizer_sft_final/ |
| Final train loss | 0.034 |
| Training time | 77 minutes (4646 seconds) |
| Total steps | 400 |
| Epochs | 2 |
| GPU | RTX 4090 |
| Initial reward | 0.200 |
| Final reward | 0.350 (last step average) |
| Model saved | models/normalizer_final_locked/ |

### Communications Agent — SFT (Session 16)
| Metric | Value |
|---|---|
| Base model | Qwen/Qwen2.5-7B-Instruct |
| Initial loss | 3.001 |
| Final loss | 0.250 |
| Average train loss | 1.071 |
| Token accuracy (end of training) | 94.2% |
| Training time | 57 seconds |
| GPU | RTX 4090 |
| Epochs | 3 |
| Batch size | 1 (grad_accum=4, effective=4) |
| Quantization | 4-bit NF4 via bitsandbytes |
| Checkpoint | checkpoints/communications_sft_final/ |

### Communications Agent — RLVR (Session 18)
| Metric | Value |
|---|---|
| Base checkpoint | checkpoints/communications_sft_final/ |
| Final train loss | -0.001 |
| Training time | 52 minutes (3137 seconds) |
| Total steps | 160 |
| Epochs | 2 |
| GPU | RTX 4090 |
| Initial reward | 0.854 |
| Final reward | 0.896 |
| Baseline compliance | 0.8646 |
| Final compliance | 0.8646 |
| Delta | 0.000 |
| Note | Delta=0 expected: SFT already strong at 94.2% accuracy.<br>Completions hit max_length=256 during RLVR — truncation affects compliance measurement.<br>Training reward 0.85-0.92 confirms strong advisory generation within token budget. |
| Model saved | models/communications_final_locked/ |

---

## Evaluation Results (Week 15 — Session 24)

### Normalizer Agent
| Metric | Base | SFT | RLVR |
|---|---|---|---|
| Domain accuracy | TBD | TBD | TBD |
| Severity accuracy | TBD | TBD | TBD |

### Correlation Agent (DSPy)
| Metric | Baseline | Optimized |
|---|---|---|
| Root cause accuracy | 100.0% (BaselineCorrelator) | 96.7% (gpt-oss-20b) |
| Bootstrap traces | — | 8 |
| Val set size | — | 30 examples |
| Delta | — | -3.3% vs baseline |
| Model | — | gpt-oss-20b on SV cluster |
| Compiled program | — | dspy_programs/alerts_to_incident_compiled.json |

Baseline 100% reflects BaselineCorrelator heuristic mode which uses ground truth labels directly. Optimized 96.7% reflects actual LLM inference on unseen val examples — this is the meaningful accuracy number for demo day.

### Communications Agent
| Metric | Base | RLVR |
|---|---|---|
| Advisory compliance | TBD | TBD |
| Delta | TBD | TBD |

### Latency
| Stage | Mean ms |
|---|---|
| Normalize | TBD |
| Triage | TBD |
| Correlate | TBD |
| Store | TBD |
| End-to-end | TBD |
| Target | < 2000ms |

---

## Notes
- All TBD values filled in as training jobs complete
- Final numbers presented in Week 16 hackathon
- Honest reporting — including any metrics that miss target
