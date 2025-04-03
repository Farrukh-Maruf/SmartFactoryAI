# run.py
import threading
import time
from src.core.ai_control_system import AIControlSystem
from src.web.app import app

def run_ai_system():
    """Run the AI control system in a separate thread."""
    ai_system = AIControlSystem()
    ai_system.run()

def run_web_server():
    """Run the Flask web server for visualization."""
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=True)

if __name__ == "__main__":
    # Start AI system in a separate thread
    ai_thread = threading.Thread(target=run_ai_system)
    ai_thread.daemon = True
    ai_thread.start()
    
    # Give the AI system time to initialize
    time.sleep(2)
    
    # Start the web server in the main thread
    run_web_server()

# from src.utils.logger import setup_logger

# logger = setup_logger(__name__)

# # Main function to run the application with uvicorn
# def run_fastapi_app():
#     import uvicorn
#     uvicorn.run("src.core.ai_control_system:app", host="0.0.0.0", port=8000, reload=True)

# if __name__ == "__main__":
#     run_fastapi_app()

# def main():
#     try:
#         ai_system = AIControlSystem()
#         ai_system.run()
#     except Exception as e:
#         logger.error(f"Main execution failed: {e}")
#         raise

# if __name__ == "__main__":
#     main()