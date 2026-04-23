import os
import json
import time
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, ACTOR_RUSHED_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("API_KEY"))
MODEL_NAME = "gpt-4o-mini"

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: List[str]) -> tuple[str, int, int]:
    start_time = time.time()
    
    context_text = "\n".join([f"Title: {c.title}\nText: {c.text}" for c in example.context])
    
    prompt = f"Question: {example.question}\n\nContext:\n{context_text}"
    if reflection_memory:
        reflections_str = "\n".join([f"- {r}" for r in reflection_memory])
        prompt += f"\n\nPrevious Reflections:\n{reflections_str}\n\nPlease learn from these and improve your answer."

    # Cách 3: Ở lần thử đầu tiên, dùng Prompt "vội vàng" và Temperature cao để dễ sai
    if attempt_id == 1 and agent_type == "reflexion":
        system_prompt = ACTOR_RUSHED_SYSTEM
        temp = 1.0
    else:
        system_prompt = ACTOR_SYSTEM
        temp = 0.0

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temp
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    answer = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens
    
    return answer, tokens, latency_ms

def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    start_time = time.time()
    
    prompt = f"Question: {example.question}\nGold Answer: {example.gold_answer}\nUser's Answer: {answer}"
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": EVALUATOR_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    result_json = json.loads(response.choices[0].message.content)
    judge = JudgeResult.model_validate(result_json)
    tokens = response.usage.total_tokens
    
    return judge, tokens, latency_ms

def reflector(example: QAExample, attempt_id: int, answer: str, judge: JudgeResult) -> tuple[ReflectionEntry, int, int]:
    start_time = time.time()
    
    prompt = f"Question: {example.question}\nIncorrect Answer: {answer}\nEvaluator Feedback: {judge.reason}"
    if judge.missing_evidence:
        prompt += f"\nMissing Evidence: {', '.join(judge.missing_evidence)}"
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": REFLECTOR_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    result_json = json.loads(response.choices[0].message.content)
    reflection = ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=result_json.get("failure_reason", ""),
        lesson=result_json.get("lesson", ""),
        next_strategy=result_json.get("next_strategy", "")
    )
    tokens = response.usage.total_tokens
    
    return reflection, tokens, latency_ms
