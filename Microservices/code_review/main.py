from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import requests
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum
from pymongo import MongoClient

app = FastAPI()
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        response = requests.get(
            "http://localhost:5001/users/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# MongoDB setup
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = MongoClient(mongodb_url)
db = client.code_review_db

# Models
class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"

class CodeReview(BaseModel):
    id: str
    title: str
    description: str
    code_snippet: str
    author_id: str
    reviewer_id: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    comments: List[str] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class User(BaseModel):
    id: str
    username: str
    email: str
    role: str  # "developer" or "reviewer"
    created_at: datetime = datetime.now()

# Add calendar service integration
async def create_calendar_event(review_data: dict):
    try:
        calendar_service_url = "http://calendar-service:5000/api/events/code-review"
        response = requests.post(calendar_service_url, json=review_data)
        return response.json()
    except Exception as e:
        print(f"Failed to create calendar event: {e}")
        return None

# Routes
@app.post("/reviews/", response_model=CodeReview)
async def create_review(review: CodeReview, user=Depends(verify_token)):
    if user["role"] not in ["developer", "reviewer"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    review_dict = review.model_dump()
    review_dict["author_id"] = user["id"]
    db.reviews.insert_one(review_dict)

    # Create calendar event
    calendar_event = await create_calendar_event({
        "review_id": review_dict["id"],
        "title": review_dict["title"],
        "description": review_dict["description"],
        "status": review_dict["status"]
    })

    return {**review_dict, "calendar_event": calendar_event}

@app.get("/reviews/", response_model=List[CodeReview])
async def get_reviews(status: Optional[ReviewStatus] = None):
    query = {} if status is None else {"status": status}
    reviews = list(db.reviews.find(query))
    return reviews

@app.get("/reviews/{review_id}", response_model=CodeReview)
async def get_review(review_id: str):
    review = db.reviews.find_one({"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@app.put("/reviews/{review_id}", response_model=CodeReview)
async def update_review(review_id: str, review: CodeReview, user=Depends(verify_token)):
    if user["role"] != "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer access required")

    # Ensure the review ID matches the path parameter
    if review.id != review_id:
        raise HTTPException(status_code=400, detail="Review ID mismatch")

    # Check if review exists
    existing_review = db.reviews.find_one({"id": review_id})
    if not existing_review:
        raise HTTPException(status_code=404, detail="Review not found")

    review_dict = review.model_dump()
    review_dict["updated_at"] = datetime.now()

    db.reviews.update_one(
        {"id": review_id},
        {"$set": review_dict}
    )
    return review_dict

@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    result = db.reviews.delete_one({"id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully"}

@app.post("/users/", response_model=User)
async def create_user(user: User):
    # Check if user with same ID exists
    if db.users.find_one({"id": user.id}):
        raise HTTPException(status_code=400, detail="User with this ID already exists")

    user_dict = user.model_dump()
    db.users.insert_one(user_dict)
    return user_dict

@app.get("/users/", response_model=List[User])
async def get_users(role: Optional[str] = None):
    query = {} if role is None else {"role": role}
    users = list(db.users.find(query))
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user: User):
    # Ensure the user ID matches the path parameter
    if user.id != user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")

    # Check if user exists
    existing_user = db.users.find_one({"id": user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_dict = user.model_dump()
    db.users.update_one(
        {"id": user_id},
        {"$set": user_dict}
    )
    return user_dict

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

