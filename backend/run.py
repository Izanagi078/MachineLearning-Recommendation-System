import os
import sys
import uvicorn

if __name__ == "__main__":
    # Get the project root folder (parent of backend/)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    
    # Append to sys.path
    sys.path.append(project_root)
    
    # Set PYTHONPATH environment variable so Uvicorn reloader subprocesses inherit it
    os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")
    
    print(f"[Backend Runner] Setting PYTHONPATH to: {project_root}")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
