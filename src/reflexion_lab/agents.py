from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .llm_runtime import actor_answer, evaluator, reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1

    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        
        for attempt_id in range(1, self.max_attempts + 1):
            # 1. Actor trả lời
            answer, actor_tokens, actor_latency = actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            
            # 2. Evaluator chấm điểm
            judge, eval_tokens, eval_latency = evaluator(example, answer)
            
            current_tokens = actor_tokens + eval_tokens
            current_latency = actor_latency + eval_latency
            
            reflection_obj = None
            
            # 3. Kiểm tra kết quả và thực hiện Reflection nếu cần
            final_answer = answer
            final_score = judge.score
            
            if judge.score == 1:
                trace = AttemptTrace(
                    attempt_id=attempt_id, 
                    answer=answer, 
                    score=judge.score, 
                    reason=judge.reason, 
                    token_estimate=current_tokens, 
                    latency_ms=current_latency
                )
                traces.append(trace)
                break
            
            # Nếu sai và là reflexion agent, tiến hành phản chiếu
            if self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                reflection_obj, reflect_tokens, reflect_latency = reflector(example, attempt_id, answer, judge)
                current_tokens += reflect_tokens
                current_latency += reflect_latency
                
                reflections.append(reflection_obj)
                reflection_memory.append(reflection_obj.next_strategy)
            
            trace = AttemptTrace(
                attempt_id=attempt_id, 
                answer=answer, 
                score=judge.score, 
                reason=judge.reason, 
                reflection=reflection_obj,
                token_estimate=current_tokens, 
                latency_ms=current_latency
            )
            traces.append(trace)

        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        
        # Xác định failure mode
        failure_mode = "none" if final_score == 1 else "wrong_final_answer"
        
        return RunRecord(
            qid=example.qid, 
            question=example.question, 
            gold_answer=example.gold_answer, 
            agent_type=self.agent_type, 
            predicted_answer=final_answer, 
            is_correct=bool(final_score), 
            attempts=len(traces), 
            token_estimate=total_tokens, 
            latency_ms=total_latency, 
            failure_mode=failure_mode, 
            reflections=reflections, 
            traces=traces
        )

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
