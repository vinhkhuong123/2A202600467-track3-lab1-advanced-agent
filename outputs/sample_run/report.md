# Lab 16 Benchmark Report

## Metadata
- Dataset: 100.json
- Mode: openai
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.9 | 0.93 | 0.03 |
| Avg attempts | 1 | 1.23 | 0.23 |
| Avg token estimate | 1741.07 | 2203.78 | 462.71 |
| Avg latency (ms) | 2530.26 | 3725.26 | 1195.0 |

## Failure modes
```json
{
  "react": {
    "none": 90,
    "wrong_final_answer": 10
  },
  "reflexion": {
    "none": 93,
    "wrong_final_answer": 7
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
