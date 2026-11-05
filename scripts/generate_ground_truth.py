import json
import pandas as pd
from tqdm.auto import tqdm
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_client = OpenAI()

prompt1_template = """
You are a fitness expert generating evaluation questions.
For the exercise below, generate 2 questions that a user might ask.
Return the result as a JSON array with objects containing 'id' and 'question' fields.

Exercise: {exercise_name}
Activity type: {type_of_activity}
Equipment: {type_of_equipment}
Body part: {body_part}
Muscle groups: {muscle_groups_activated}
Instructions: {instructions}
""".strip()

df = pd.read_csv('data/data.csv', keep_default_na=False)

results = []

for _, row in tqdm(df.iterrows(), total=len(df)):
    prompt = prompt1_template.format(**row.to_dict())
    response = openai_client.responses.create(
        model="gpt-5.4-mini",
        input=[{"role": "user", "content": prompt}]
    )
    questions = json.loads(response.output_text)
    for q in questions:
        q["id"] = row["id"]
        results.append(q)

df_questions = pd.DataFrame(results)
df_questions.to_csv("data/ground-truth-retrieval.csv", index=False)