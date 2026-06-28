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
    
    env = os.environ.get("ENVIRONMENT", "development").lower()
    default_host = "0.0.0.0" if env == "production" else "127.0.0.1"
    host = os.environ.get("HOST", default_host)
    
    # Dynamic port configuration for production platforms (e.g. Render, Railway)
    port = int(os.environ.get("PORT", 8000))
    reload = env == "development"
    
    print(f"[Backend Runner] Setting PYTHONPATH to: {project_root}")
    print(f"[Backend Runner] Starting server on {host}:{port} (reload={reload}, env={env})")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload)
