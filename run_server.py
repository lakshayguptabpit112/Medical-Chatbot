import os
import sys

os.chdir("C:/Users/laksh/OneDrive/Desktop/Medical-Chatbot-Clean")
sys.path.insert(0, "C:/Users/laksh/OneDrive/Desktop/Medical-Chatbot-Clean")

import uvicorn

if __name__ == "__main__":
    print("Starting Medical-Chatbot server on http://127.0.0.1:8003 ...", flush=True)
    uvicorn.run("main:app", host="127.0.0.1", port=8003, log_level="info")
