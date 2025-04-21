from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Optional
import spacy
from dateparser.search import search_dates
import re
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp = spacy.load("en_core_web_sm")

FILLER_WORDS = {
    'uh', 'um', 'okay', 'so', 'like', 'yeah', 'oh', 'also', 'maybe', 'just',
    'kinda', 'sorta', 'i guess', 'you know', 'alright', 'hmm', 'uhm'
}

class TaskItem(BaseModel):
    task: str
    time: Optional[str]
    type: str

class UserInput(BaseModel):
    text: str

def clean_input(text: str) -> str:
    text = text.lower()
    for word in FILLER_WORDS:
        text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def split_input(text: str) -> List[str]:
    return [chunk.strip() for chunk in re.split(r'\b(?:and|then|,)\b', text, flags=re.IGNORECASE) if chunk.strip()]

def extract_tasks_with_times(chunk: str) -> List[TaskItem]:
    results = []
    found_dates = search_dates(chunk)

    if found_dates:
        seen_times = set()
        for date_text, time in found_dates:
            if time not in seen_times:
                seen_times.add(time)
                task_text = chunk.replace(date_text, '').strip(",. ").strip()
                full_task = f"{task_text} ({date_text.strip()})"
                results.append(TaskItem(task=full_task, time=time.isoformat(), type="calendar"))
    else:
        results.append(TaskItem(task=chunk.strip(), time=None, type="todo"))

    return results

@app.post("/analyze", response_model=List[TaskItem])
async def analyze(user_input: UserInput):
    cleaned = clean_input(user_input.text)
    chunks = split_input(cleaned)
    all_results = []

    for chunk in chunks:
        extracted = extract_tasks_with_times(chunk)
        all_results.extend(extracted)

    return all_results
