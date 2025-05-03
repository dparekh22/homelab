#!/bin/bash
# Start Uvicorn in background
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start bot.py
python bot.py