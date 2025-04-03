# src/core/file_tracker.py
import os
import json
import threading
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

# Configuration
TRACKER_FILE = "last_processed_files.json"
MAX_TRACKED_FILES = 4  # Number of last files to track per task type

class FileTracker:
    """
    Tracks the most recently processed files for each task type.
    """
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.lock = threading.Lock()
        self.data = {
            'CASE': [],
            'BOX': [],
            'COVER': [],
            'FORDING': [],
            'FINAL': []
        }
        self._load_data()
    
    def _load_data(self):
        """Load tracked files data from the JSON file if it exists."""
        try:
            if os.path.exists(TRACKER_FILE):
                with self.lock:
                    with open(TRACKER_FILE, 'r') as f:
                        loaded_data = json.load(f)
                        # Ensure all required keys exist
                        for key in self.data.keys():
                            if key not in loaded_data:
                                loaded_data[key] = []
                        self.data = loaded_data
                self.logger.info("Loaded tracked files data from file")
            else:
                self._save_data()  # Create the file if it doesn't exist
                self.logger.info("Created new tracked files data file")
        except Exception as e:
            self.logger.error(f"Error loading tracked files data: {e}")
    
    def _save_data(self):
        """Save tracked files data to the JSON file."""
        try:
            with self.lock:
                with open(TRACKER_FILE, 'w') as f:
                    json.dump(self.data, f, indent=4)
            self.logger.debug("Saved tracked files data to file")
        except Exception as e:
            self.logger.error(f"Error saving tracked files data: {e}")
    
    def add_file(self, task_type: str, file_path: str, metadata: Optional[Dict] = None):
        """
        Add a new file to the tracker for a specific task type.
        
        :param task_type: Type of task (CASE, BOX, etc.)
        :param file_path: Path to the saved file
        :param metadata: Optional metadata about the file (status, timestamp, etc.)
        """
        if task_type not in self.data:
            self.logger.warning(f"Unknown task type: {task_type}")
            return
        
        if not os.path.exists(file_path):
            self.logger.warning(f"File does not exist: {file_path}")
            return
        
        # Default metadata if not provided
        if metadata is None:
            metadata = {}
        
        file_info = {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'timestamp': metadata.get('timestamp', ''),
            'status': metadata.get('status', 'UNKNOWN'),
            'task_type': task_type,
            'details': metadata.get('details', '')
        }
        
        with self.lock:
            # Add the new file at the beginning of the list
            self.data[task_type].insert(0, file_info)
            # Keep only the most recent files
            self.data[task_type] = self.data[task_type][:MAX_TRACKED_FILES]
            
        self._save_data()
        self.logger.info(f"Added file {file_path} to tracked files for {task_type}")
    
    def get_files(self, task_type: Optional[str] = None) -> Dict[str, List]:
        """
        Get the most recently processed files.
        
        :param task_type: Optional task type to filter results
        :return: Dictionary with task types and their recent files
        """
        with self.lock:
            if task_type:
                if task_type in self.data:
                    return {task_type: self.data[task_type]}
                return {task_type: []}
            return self.data
    
    def get_latest_files(self) -> Dict[str, Dict]:
        """
        Get the most recent file for each task type.
        
        :return: Dictionary with task types and their most recent file
        """
        result = {}
        with self.lock:
            for task_type, files in self.data.items():
                if files:
                    result[task_type] = files[0]
                else:
                    result[task_type] = None
        return result

# Create a singleton instance
file_tracker = FileTracker()