from contextlib import asynccontextmanager
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import json
import os


class QAPair(BaseModel):
    question: str
    answer: str

class Infographic(BaseModel):
    category: str
    title: str
    description: str
    tags: List[str]
    img_url: str

class Label(BaseModel):
    infographic_title: str
    category: str
    tags: List[str]
    qa_pairs: List[Dict[str, str]] 
    labeled_by: str
    labeled_at: datetime

# Initialize data storage
lifespan_data = {}

def load_data_from_json():
    """Load data from JSON file"""
    try:
        data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'data.json')
        with open(data_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            return metadata["metadata"]
    except Exception as e:
        print(f"Error loading data: {e}")
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    lifespan_data["infographics"] = load_data_from_json()
    lifespan_data["labels"] = []
    yield
    lifespan_data.clear()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Infographics Labeling API"}


@app.get("/infographics")
async def get_infographics(category: Optional[str] = None):
    if category:
        return [info for info in lifespan_data["infographics"] if info["category"] == category]
    return lifespan_data["infographics"]


@app.get("/infographics/unlabeled")
async def get_unlabeled_infographics(category: Optional[str] = None):
    labeled_titles = set(label["infographic_title"] for label in lifespan_data["labels"])
    unlabeled = [info for info in lifespan_data["infographics"] 
                 if info["title"] not in labeled_titles]
    if category:
        unlabeled = [info for info in unlabeled if info["category"] == category]
    return unlabeled


@app.post("/infographics")
async def add_infographic(infographic: Infographic):
    lifespan_data["infographics"].append(infographic.model_dump())
    return {"message": "Infographic added successfully"}


@app.post("/labels")
async def add_label(label: Label):
    # Validate that each QA pair has both question and answer
    for qa in label.qa_pairs:
        if not qa.get("question") or not qa.get("answer"):
            raise HTTPException(
                status_code=400, 
                detail="Each QA pair must have both question and answer"
            )
    lifespan_data["labels"].append(label.model_dump())
    return {"message": "Label submitted successfully"}


@app.get("/labels", response_model=List[Label])
def get_labels(category: Optional[str] = Query(default=None)):
    if category and category != "All":
        filtered_labels = [label for label in lifespan_data["labels"] if label["category"] == category]
        return filtered_labels
    return lifespan_data["labels"]


@app.get("/categories")
async def get_categories():
    return list(set(info["category"] for info in lifespan_data["infographics"]))


@app.get("/category-stats")
async def get_category_stats():
    stats = {}
    for category in set(info["category"] for info in lifespan_data["infographics"]):
        total = len([info for info in lifespan_data["infographics"] if info["category"] == category])
        labeled = len([label for label in lifespan_data["labels"] if label["category"] == category])
        stats[category] = {
            "total": total,
            "labeled": labeled,
            "unlabeled": total - labeled
        }
    return stats


@app.get("/reload-data")
async def reload_data():
    """Endpoint to reload data from JSON file"""
    lifespan_data["infographics"] = load_data_from_json()
    lifespan_data["labels"] = []
    
    return {"message": "Data reloaded successfully", "infographics": lifespan_data["infographics"]}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
