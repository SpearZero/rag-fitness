import json
import pandas as pd
from tqdm.auto import tqdm

from fitness_assistant.rag import rag, llm

df_question = pd.read_csv("data/ground-truth-retrieval.csv")

prompt2_template = """
You are an expert evaluator for a RAG system.
Your task is to analyze the relevance of the generated answer to the given question.
Based on the relevance of the generated answer, you will classify it
as 'NON_RELEVANT', 'PARTLY_RELEVANT', or 'RELEVANT'.

Here is the data for evaluation:

Question: {question}
Generated Answer: {answer_llm}

Please analyze the content and context of the generated answer in relation to the question
and provide your evaluation in parsable JSON without using code blocks:

{{
  'Relevance': 'NON_RELEVANT' | 'PARTLY_RELEVANT' | 'RELEVANT',
  'Explanation': '[Provide a brief explanation for your evaluation]'
}}
""".strip()

df_sample = df_question.sample(n=20, random_state=1)
sample = df_sample.to_dict(orient="records")

evaluations = []

for record in tqdm(sample):
    question = record["question"]
    answer_llm = rag(question)["answer"]

    prompt = prompt2_template.format(
        question=question,
        answer_llm=answer_llm
    )

    evaluation, _ = llm(prompt)
    evaluation = json.loads(evaluation)

    evaluations.append((record, answer_llm, evaluation))

df_eval = pd.DataFrame(evaluations, columns=["record", "answer", "evaluation"])
df_eval["id"] = df_eval.record.apply(lambda d: d["id"])
df_eval["question"] = df_eval.record.apply(lambda d: d["question"])
df_eval["relevance"] = df_eval.evaluation.apply(lambda d: d["Relevance"])
df_eval["explanation"] = df_eval.evaluation.apply(lambda d: d["Explanation"])

print(df_eval.relevance.value_counts(normalize=True))

df_eval.to_csv("data/rag-eval-gpt-5.4-mini.csv", index=False)
