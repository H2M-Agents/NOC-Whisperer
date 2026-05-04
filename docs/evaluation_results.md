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
| Initial reward | TBD |
| Final reward | TBD |
| Domain accuracy baseline | TBD |
| Domain accuracy after RLVR | TBD |
| Delta | TBD |
| Checkpoint | models/normalizer_final_locked/ |

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
| Initial reward | TBD |
| Final reward | TBD |
| Advisory compliance baseline | TBD |
| Advisory compliance after RLVR | TBD |
| Delta | TBD |
| Checkpoint | models/communications_final_locked/ |

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
| Root cause accuracy | TBD | TBD |
| Delta | TBD | TBD |

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
