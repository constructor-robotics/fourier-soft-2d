"""
File: items.py
Description: [Brief description of the file's purpose]
Author: Arturo Gomez-Chavez
Creation Date: 30.06.2025
Institution/Organization: Constructor University GmbH
Contributors/Editors:
License: MIT License - See LICENSE.MD file for details
Contact & Support:
- Email: [support@example.com]
"""

from fastapi import APIRouter
from typing import List  # Add this import
from app.schemas import Item, ItemCreate

router = APIRouter()

# Temporary in-memory storage
fake_items_db = []

@router.post("/", response_model=Item)
def create_item(item: ItemCreate):
    fake_item = Item(id=len(fake_items_db) + 1, **item.dict())
    fake_items_db.append(fake_item)
    return fake_item

@router.get("/", response_model=List[Item])
def read_items():
    return fake_items_db

@router.get("/{item_id}", response_model=Item)
def read_item(item_id: int):
    for item in fake_items_db:
        if item.id == item_id:
            return item
    return {"error": "Item not found"}