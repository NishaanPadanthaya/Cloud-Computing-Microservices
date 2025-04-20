from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional
from bson import ObjectId
import uvicorn
import os

app = FastAPI()

# MongoDB setup
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = MongoClient(mongodb_url)
db = client["bugtracker_db"]  # Use a specific DB

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

@app.post("/client/bugs/create")
async def create_bug(bug: Bug):
    bug_collection.insert_one(bug.model_dump())
    if bug_collection.find_one({"bug_id": bug.bug_id}):
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
    bug_collection.update_one(
        {"bug_id": bug_id, "employee_id": employee_id},
        {"$set": {"status": status}}
    )
    employee_collection.update_one(
        {"employee_id": employee_id},
        {"$inc": {"bugs_completed": 1}}
    )
    return {"message": f"Bug {bug_id} updated to status {status}"}

# --------------------- MAIN ---------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
