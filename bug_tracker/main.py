from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional
from bson import ObjectId
import uvicorn
import os
import requests
from datetime import datetime, timedelta

app = FastAPI()

# MongoDB setup
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = MongoClient(mongodb_url)
db = client["bugtracker_db"]  # Use a specific DB

# Service URLs
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:5000")
FORUM_SERVICE_URL = os.getenv("FORUM_SERVICE_URL", "http://localhost:8004")

employee_collection = db["employee_collection"]
bug_collection = db["bug_collection"]
manager_collection = db["manager_collection"]
client_collection = db["client_collection"]

# Helper to serialize ObjectId
def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc

# Pydantic models
class Employee(BaseModel):
    employee_id: str
    name: str
    bugs_completed: int = 0
    bugs_pending: int = 0

class Bug(BaseModel):
    bug_id: str
    title: str
    description: str
    status: str = "Pending"

class Manager(BaseModel):
    manager_id: str
    name: str

class Client(BaseModel):
    client_id: str
    name: str

# Routes

@app.get("/")
async def root():
    return {"message": "Welcome to the Bug Tracker"}

# --------------------- CLIENT ---------------------

async def create_calendar_event_for_bug(bug: Bug):
    """Create a calendar event for a new bug"""
    event_data = {
        "title": f"Bug: {bug.title}",
        "start": datetime.now().isoformat(),
        "end": (datetime.now() + timedelta(days=7)).isoformat(),  # Default 7-day deadline
        "desc": bug.description,
        "allDay": False,
        "createdBy": "bug_tracker",
        "eventType": "bug",
        "referenceId": bug.bug_id,
        "status": bug.status
    }

    try:
        response = requests.post(f"{CALENDAR_SERVICE_URL}/api/events", json=event_data)
        if response.status_code == 200:
            print(f"Calendar event created for bug {bug.bug_id}")
        else:
            print(f"Failed to create calendar event: {response.text}")
    except Exception as e:
        print(f"Error creating calendar event: {str(e)}")

@app.post("/client/bugs/create")
async def create_bug(bug: Bug):
    bug_collection.insert_one(bug.model_dump())
    if bug_collection.find_one({"bug_id": bug.bug_id}):
        # Create calendar event for the new bug
        await create_calendar_event_for_bug(bug)
        return {"message": "Bug created successfully"}
    return {"message": "Bug creation failed"}

# --------------------- MANAGER ---------------------

@app.post("/manager/client/create")
async def create_client(client_data: Client):
    if client_collection.find_one({"client_id": client_data.client_id}):
        return {"message": "Client already exists"}
    client_collection.insert_one(client_data.model_dump())
    if client_collection.find_one({"client_id": client_data.client_id}):
        return {"message": "Client created successfully"}
    return {"message": "Client creation failed"}

@app.post("/manager/employee/create")
async def create_employee(employee: Employee):
    if employee_collection.find_one({"employee_id": employee.employee_id}):
        return {"message": "Employee already exists"}
    employee_collection.insert_one(employee.model_dump())
    return {"message": "Employee created successfully"}

@app.get("/manager/employees")
async def list_employees():
    return [serialize_doc(emp) for emp in employee_collection.find()]


@app.get("/manager/clients")
async def list_clients():
    return [serialize_doc(client) for client in client_collection.find()]

@app.post("/manager/bugs/assign")
async def assign_bug(bug_id: str, employee_id: str):
    if bug_collection.find_one({"bug_id": bug_id}):
        bug_collection.update_one(
            {"bug_id": bug_id},
            {"$set": {"employee_id": employee_id}}
        )
        employee_collection.update_one(
            {"employee_id": employee_id},
            {"$inc": {"bugs_pending": 1}}
        )
        return {"message": "Bug assigned successfully"}
    return {"message": "Bug assignment failed"}


@app.get("/manager/bugs")
async def list_bugs():
    return [serialize_doc(bug) for bug in bug_collection.find()]

# --------------------- EMPLOYEE ---------------------

@app.get("/employee/{employee_id}/bugs")
async def list_employee_bugs(employee_id: str):
    return [serialize_doc(bug) for bug in bug_collection.find({"employee_id": employee_id})]

@app.get("/employee/{employee_id}/bugs/completed")
async def list_completed_bugs(employee_id: str):
    return [serialize_doc(bug) for bug in bug_collection.find({"employee_id": employee_id, "status": "Completed"})]

@app.get("/employee/{employee_id}/bugs/pending")
async def list_pending_bugs(employee_id: str):
    return [serialize_doc(bug) for bug in bug_collection.find({"employee_id": employee_id, "status": "Pending"})]

@app.post("/employee/{employee_id}/bugs/update")
async def update_bug_status(employee_id: str, bug_id: str, status: str):
    bug = bug_collection.find_one({"bug_id": bug_id})
    if bug:
        bug_collection.update_one(
            {"bug_id": bug_id, "employee_id": employee_id},
            {"$set": {"status": status}}
        )
        employee_collection.update_one(
            {"employee_id": employee_id},
            {"$inc": {"bugs_completed": 1}}
        )

        # Update calendar event status
        try:
            response = requests.put(
                f"{CALENDAR_SERVICE_URL}/api/events/by-reference/{bug_id}",
                json={"status": status}
            )
            if response.status_code != 200:
                print(f"Failed to update calendar event status: {response.text}")
        except Exception as e:
            print(f"Error updating calendar event status: {str(e)}")

        return {"message": f"Bug {bug_id} updated to status {status}"}
    return {"message": "Bug not found"}

# --------------------- FORUM INTEGRATION ---------------------

@app.post("/bugs/{bug_id}/create-forum-topic")
async def create_forum_topic_for_bug(bug_id: str, title: str, description: str):
    """Create a forum topic for discussion about a specific bug"""
    bug = bug_collection.find_one({"bug_id": bug_id})
    if not bug:
        return {"message": "Bug not found"}

    try:
        # Prepare forum topic data
        topic_data = {
            "title": title or f"Discussion: Bug #{bug_id} - {bug['title']}",
            "description": description or f"This topic is for discussing bug #{bug_id}: {bug['description']}",
            "is_scheduled": 0  # Not scheduled by default
        }

        # Send request to forum service
        response = requests.post(f"{FORUM_SERVICE_URL}/topics/", json=topic_data)

        if response.status_code == 200:
            return {"message": "Forum topic created successfully", "topic": response.json()}
        else:
            return {"message": f"Failed to create forum topic: {response.text}"}
    except Exception as e:
        return {"message": f"Error creating forum topic: {str(e)}"}

# --------------------- MAIN ---------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
