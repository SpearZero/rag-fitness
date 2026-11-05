import pandas as pd
from tqdm.auto import tqdm
import random

from fitness_assistant.rag import index, search

df_question = pd.read_csv("data/ground-truth-retrieval.csv")
ground_truth = df_question.to_dict(orient="records")

def hit_rate(relevance_total):
    cnt = 0
    for line in relevance_total:
        if True in line:
            cnt += 1
    return cnt / len(relevance_total)

def mrr(relevance_total):
    total_score = 0.0
    for line in relevance_total:
        for rank in range(len(line)):
            if line[rank]:
                total_score += 1 / (rank + 1)
                break
    return total_score / len(relevance_total)

def evaluate(ground_truth, search_function):
    relevance_total = []
    for q in tqdm(ground_truth):
        doc_id = q["id"]
        results = search_function(q)
        relevance = [d["id"] == doc_id for d in results]
        relevance_total.append(relevance)
    return {
        "hit_rate": hit_rate(relevance_total),
        "mrr": mrr(relevance_total)
    }

print("기본 검색 전체 평가:", evaluate(ground_truth, lambda q: search(q["question"])))

df_validation = df_question[:80]
df_test = df_question[80:]

gt_val = df_validation.to_dict(orient="records")
gt_test = df_test.to_dict(orient="records")

def minsearch_search(query, boost=None):
    if boost is None:
        boost = {}

    results = index.search(
        query=query,
        filter_dict={},
        boost_dict=boost,
        num_results=10
    )
    return results

def simple_optimize(param_ranges, objective_function, n_iterations=10):
    best_params = None
    best_score = float("-inf")

    for _ in range(n_iterations):
        current_params = {}
        for field, (low, high) in param_ranges.items():
            current_params[field] = random.uniform(low, high)

        current_score = objective_function(current_params)

        if current_score > best_score:
            best_score = current_score
            best_params = current_params

    return best_params

param_ranges = {
    "exercise_name": (0.0, 3.0),
    "type_of_activity": (0.0, 3.0),
    "type_of_equipment": (0.0, 3.0),
    "body_part": (0.0, 3.0),
    "type": (0.0, 3.0),
    "muscle_groups_activated": (0.0, 3.0),
    "instructions": (0.0, 3.0),
}

def objective(boost_params):
    def search_function(q):
        return minsearch_search(q["question"], boost=boost_params)

    results = evaluate(gt_val, search_function)
    return results["hit_rate"]

best_params = simple_optimize(param_ranges, objective, n_iterations=20)
print("Best boost parameters:", best_params)

print("기본 검색 테스트 평가:", evaluate(gt_test, lambda q: search(q["question"])))
print(
    "최적 가중치 테스트 평가:",
    evaluate(
        gt_test,
        lambda q: minsearch_search(q["question"], boost=best_params),
    ),
)
