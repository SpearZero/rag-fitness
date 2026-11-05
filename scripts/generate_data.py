from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

load_dotenv()
openai_client = OpenAI()

class Exercise(BaseModel):
    id: str = Field(description="Unique identifier, e.g.'push-up-001'")
    exercise_name: str = Field(description="Name of the exercise")
    type_of_activity: str = Field(description="Strength, Cardio, Flexibility, etc.")
    type_of_equipment: str = Field(description="Dumbbells, Barbell, None (bodyweight), etc.")
    body_part: str = Field(description="Chest, Back, Legs, etc.")
    type: str = Field(description="Compound, Isolation, etc.")
    muscle_groups_activated: str = Field(description="Comma-separated list, e.g. 'Chest, Triceps, Shoulders'")
    instructions: str = Field(description="Detailed step-by-step instructions")

class ExerciseDataset(BaseModel):
    exercises: List[Exercise]

prompt = """
Generate a dataset of 50 diverse fitness exercises.
Cover different muscle groups, equipment types, and difficulty levels.
Include bodyweight exercises, free weights, and machine exercises.
""".strip()

response = openai_client.responses.parse(
    model="gpt-5.4-mini",
    input=[{"role": "user", "content": prompt}],
    text_format=ExerciseDataset,
)

dataset = response.output_parsed
df = pd.DataFrame([ex.model_dump() for ex in dataset.exercises])
df.to_csv("data/data.csv", index=False)
print(f"Generated {len(df)} exercises.")
