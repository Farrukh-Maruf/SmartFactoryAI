import json
import os
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List

import pika
import requests

from src.config.settings import NODERED_ENDPOINT, QUEUE_CONFIG, RABBITMQ_CONFIG
from src.utils.logger import setup_logger

from .file_tracker import file_tracker
from .task_analyzer import TaskAnalyzer

# File access lock to prevent concurrent read/write operations
file_lock = threading.Lock()

# Global task processing lock - This ensures only one task is processed at a time
global_task_lock = threading.Lock()

# Order data file path
ORDER_DATA_FILE = "order_data.json"

# API endpoints
PING_API = "http://nsu.owon.kr/api/ai/ping"
UPLOAD_API = "http://nsu.owon.kr/api/ai/upload"

# PING_API = "http://192.168.1.104/api/ai/ping"
# UPLOAD_API = "http://192.168.1.104/api/ai/upload"

# Queue and exchange configuration
# NODE_RED_CONFIG = [
#     {"queue": "NODERED_TO_AI", "routing_key": "NODERED_TO_AI_KEY", "exchange": "NSU_NODERED_FAN", "exchange_type": "fanout"},  # case queue
#     {'queue': 'NODERED_TO_AI2', 'routing_key': 'NODERED_TO_AI_KEY2', 'exchange': 'NSU_NODERED_FAN2', 'exchange_type': 'fanout'},    # box
#     {'queue': 'NODERED_TO_AI3', 'routing_key': 'NODERED_TO_AI_KEY3', 'exchange': 'NSU_NODERED_FAN3', 'exchange_type': 'fanout'},    # cover
#     {'queue': 'NODERED_TO_AI4', 'routing_key': 'NODERED_TO_AI_KEY4', 'exchange': 'NSU_NODERED_FAN4', 'exchange_type': 'fanout'},    # folding & robot
# ]

NODE_RED_CONFIG = [
    {
        "queue": os.getenv("NODE_RED_CONFIG_QUEUE", "NODERED_TO_AI"),
        "routing_key": os.getenv("NODE_RED_CONFIG_ROUTING_KEY", "NODERED_TO_AI_KEY"),
        "exchange": os.getenv("NODE_RED_CONFIG_EXCHANGE", "NSU_NODERED_FAN"),
        "exchange_type": os.getenv("NODE_RED_CONFIG_EXCHANGE_TYPE", "fanout"),
    },
]


# Extract queue names for easier access
NODE_RED_QUEUES = [config["queue"] for config in NODE_RED_CONFIG]


class AIControlSystem:
    def __init__(self):
        """Initialize AI Control System"""
        print("init AIControlSystem")
        self.logger = setup_logger(__name__)

        # print(f'{RABBITMQ_CONFIG["host"]}')
        # print(f'{RABBITMQ_CONFIG["port"]}')

        # RabbitMQ connection parameters
        self.connection_params = pika.ConnectionParameters(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            credentials=pika.PlainCredentials(
                RABBITMQ_CONFIG["username"],
                RABBITMQ_CONFIG["password"],
            ),
        )

        self.nodered_endpoint = NODERED_ENDPOINT

        # Store Node-RED configuration
        self.node_red_config = NODE_RED_CONFIG

        # Task analysis mapping
        self.task_analysis_map = {
            "CASE": TaskAnalyzer.case_task_analysis,
            "BOX": TaskAnalyzer.box_task_analysis,
            "COVER": TaskAnalyzer.cover_task_analysis,
            "FORDING": TaskAnalyzer.folding_task_analysis,
            "FINAL": TaskAnalyzer.final_check_task_analysis,
        }
        self.task_analysis_map.setdefault("unknown_task", lambda _: {"status": "ERROR", "details": "Unknown task"})

        # Single global processing queue for all tasks
        self.global_processing_queue = Queue()

        # Flag to indicate if a task is currently being processed
        self.is_processing = False
        self.processing_lock = threading.Lock()

        # Task statuses for ping updates
        self.task_statuses = {
            "CASE": {"status": "IDLE", "index": 0},
            "BOX": {"status": "IDLE", "index": 0},
            "COVER": {"status": "IDLE", "index": 0},
            "FORDING": {"status": "IDLE", "index": 0},
            "FINAL": {"status": "IDLE", "index": 0},
        }

        # Status update lock
        self.status_lock = threading.Lock()

        # Create empty order data file if it doesn't exist
        self._ensure_order_data_file_exists()

    def _ensure_order_data_file_exists(self):
        """
        Create an empty order data file if it doesn't exist
        """
        if not os.path.exists(ORDER_DATA_FILE):
            with open(ORDER_DATA_FILE, "w") as file:
                json.dump({}, file)
            self.logger.info(f"Created empty order data file: {ORDER_DATA_FILE}")

    def connect_to_rabbitmq(self):
        """
        Establish connection to RabbitMQ server
        RabbitMQ server: WEB_TO_AI 접근
        """
        try:
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()

            # Declare WEB_TO_AI exchange and queue
            self.channel.exchange_declare(
                exchange=os.getenv("WEB_TO_AI_EXCHANGE", "NSU"),
                exchange_type=os.getenv("WEB_TO_AI_EXCHANGE_TYPE", "direct"),
            )
            self.channel.queue_declare(
                queue=os.getenv("WEB_TO_AI_QUEUE", "WEB_TO_AI"),
                durable=True,
            )
            self.channel.queue_bind(
                exchange=os.getenv("WEB_TO_AI_EXCHANGE", "NSU"),
                queue=os.getenv("WEB_TO_AI_QUEUE", "WEB_TO_AI"),
                routing_key=os.getenv("WEB_TO_AI_ROUTING_KEY", "WEB_TO_AI_KEY"),
            )

            # self.channel.exchange_declare(exchange="NSU_NODERED_FAN", exchange_type="fanout")
            # self.channel.queue_declare(queue="WEB_TO_AI", durable=True)
            # self.channel.queue_bind(exchange="NSU_NODERED_FAN", queue="WEB_TO_AI", routing_key="WEB_TO_AI_KEY")

            # Declare Node-RED exchanges and queues based on configuration
            for config in self.node_red_config:
                # Declare exchange
                self.channel.exchange_declare(
                    exchange=config["exchange"],
                    exchange_type=config["exchange_type"],
                )

                # Declare queue
                self.channel.queue_declare(
                    queue=config["queue"],
                    durable=True,
                )

                # Bind queue to exchange with routing key
                self.channel.queue_bind(
                    exchange=config["exchange"],
                    queue=config["queue"],
                    routing_key=config["routing_key"],
                )

                self.logger.info(f"Declared and bound queue {config['queue']} to exchange {config['exchange']}")

            self.logger.info("Connected to RabbitMQ successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def process_web_message(self, message_data: Dict[str, Any]):
        """
        Process and store messages from WEB_TO_AI queue

        :param message_data: JSON data received from web
        """
        try:
            # Validate required fields
            required_fields = ["ORDER_NO", "ITEM_CD", "ITEM_NM", "ITEM_CLASS", "BOM", "RECIPE"]
            for field in required_fields:
                if field not in message_data:
                    raise ValueError(f"Missing required field: {field}")

            # Save the order data as a JSON file with thread safety
            with file_lock:
                with open(ORDER_DATA_FILE, "w") as json_file:
                    json.dump(message_data, json_file, indent=4)

            self.logger.info(f"Updated order data: {message_data['ORDER_NO']}")

            # Log detailed information
            self.logger.info(
                f"Order details - Item: {message_data['ITEM_NM']}, " f"Class: {message_data['ITEM_CLASS']}, " f"BOM Count: {len(message_data['BOM'])}, " f"Recipe Count: {len(message_data['RECIPE'])}"
            )

        except Exception as e:
            self.logger.error(f"Error processing web message: {e}")
            raise

    def get_current_order_data(self) -> Dict[str, Any]:
        """
        Get the current order data from file

        :return: Current order data dictionary
        """
        try:
            with file_lock:
                # Check if file exists and has content
                if os.path.exists(ORDER_DATA_FILE) and os.path.getsize(ORDER_DATA_FILE) > 0:
                    with open(ORDER_DATA_FILE, "r") as json_file:
                        return json.load(json_file)
                else:
                    self.logger.warning("Order data file empty or not found")
                    return {}
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON in order data file")
            return {}
        except Exception as e:
            self.logger.error(f"Error reading order data file: {e}")
            return {}

    def update_task_status(self, task_type: str, status: str):
        """
        Update the status of a task type for ping updates

        :param task_type: Type of task (CASE, BOX, etc.)
        :param status: New status (IDLE, RUNNING, COMPLETED, ERROR)
        """
        with self.status_lock:
            if task_type in self.task_statuses:
                self.task_statuses[task_type]["status"] = status
                # Increment index for each status change
                self.task_statuses[task_type]["index"] += 1
                self.logger.info(f"Updated {task_type} status to {status}")

    def upload_file(self, file_path: str, task_type: str, details: str, order_no: str = "UNKNOWN") -> bool:
        """
        Upload a file to the API endpoint

        :param file_path: Path to the file to upload
        :param task_type: Type of task (CASE, BOX, etc.)
        :param order_no: Order number associated with the file
        :return: True if upload successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return False

            # Get file information for logging
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()
            file_type = ""

            # Identify file type for enhanced logging
            if file_extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
                file_type = "IMAGE"
            elif file_extension in [".mp4", ".avi", ".mov", ".wmv", ".flv"]:
                file_type = "VIDEO"
            else:
                file_type = "FILE"

            # Log upload attempt with detailed information
            self.logger.info(f"Uploading {file_type}: {file_path} ({file_size/1024:.2f} KB) for task {task_type}")

            with open(file_path, "rb") as file:
                # Prepare multipart/form-data fields according to API specification
                files = {"file": file}
                data = {
                    "AI_TASK": task_type,
                    "ORDER_NO": order_no,
                    "QC_CODE": details,
                }

                # Send POST request with multipart/form-data
                response = requests.post(UPLOAD_API, files=files, data=data)

                if response.status_code == 200:
                    success_message = f"Successfully uploaded {file_type} {file_path} for {task_type}, order: {order_no}"
                    self.logger.info(success_message)
                    return True
                else:
                    error_message = f"Failed to upload {file_type}: {response.status_code} - {response.text}"
                    self.logger.error(error_message)
                    return False

        except Exception as e:
            error_message = f"Error uploading file {file_path}: {e}"
            self.logger.error(error_message)
            return False

    def ping_status_worker(self):
        """
        Worker thread that sends periodic status updates to the API
        """
        self.logger.info("Started ping status worker thread")
        while True:
            try:
                # Current timestamp in the required format
                current_time = datetime.now().strftime("%Y-%m-%d")

                # Send individual ping for each task type
                with self.status_lock:
                    for task_type, status_info in self.task_statuses.items():
                        # Prepare ping data according to API specification
                        ping_data = {"AI_TASK": task_type, "TIME": current_time, "PING": True}

                        # Send ping to API
                        response = requests.post(PING_API, json=ping_data, headers={"Content-Type": "application/json"})

                        if response.status_code == 200:
                            # Log ping status with INFO level for better visibility
                            ping_message = f"Ping status update for {task_type}: {status_info['status']}"
                            # self.logger.info(ping_message)
                        else:
                            self.logger.warning(f"Ping status update for {task_type} failed: {response.status_code} - {response.text}")

            except Exception as e:
                self.logger.error(f"Error in ping status worker: {e}")

            # Sleep for 1 second before next ping (changed from 5 seconds)
            time.sleep(60)

    def process_task_analysis(self, task_request: Dict[str, Any]) -> Dict[str, str]:
        """
        Process specific task analysis based on task name

        :param task_request: Task analysis request dictionary
        :return: Processing results
        """
        task_name = task_request.get("START", "UNKNOWN_TASK")

        try:
            # Update task status to RUNNING
            self.update_task_status(task_name, "RUNNING")

            # Get the appropriate analysis method
            analysis_method = self.task_analysis_map.get(task_name, self.task_analysis_map["unknown_task"])

            # Read the current order data from file
            order_data = self.get_current_order_data()

            # Include current order data in analysis if available
            task_data = {"order_data": order_data, "task_request": task_request}

            # Process the task with the global lock to ensure only one task runs at a time
            self.logger.info(f"Starting task analysis for {task_name}")

            # Perform the specific task analysis
            analysis_result = analysis_method(task_data)
            # CASE, BOX, COVER, FOLDING, FINAL(ROBOT)

            self.logger.info(f"Completed task analysis for {task_name}")

            # Check if the result contains a saved file path and upload it : 이미지 저장장
            if "saved_file_path" in analysis_result and analysis_result["saved_file_path"]:
                # Add file to tracker for UI visualization
                file_metadata = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": analysis_result.get("status", "UNKNOWN"), "details": analysis_result.get("details", "")}
                file_tracker.add_file(task_name, analysis_result["saved_file_path"], file_metadata)
                if analysis_result["status"] == "NG":
                    # Upload file to API
                    upload_success = self.upload_file(analysis_result["saved_file_path"], task_name, analysis_result["details"])
                    if upload_success:
                        analysis_result["file_uploaded"] = True
                    else:
                        analysis_result["file_uploaded"] = False

            result = {
                "NAME": task_name,
                "RESULT": analysis_result.get("status", "OK" if analysis_result.get("status") == "COMPLETED" else "ERROR"),
                "ORDER_NO": order_data.get("ORDER_NO", "UNKNOWN"),
                "CONFIDENCE": analysis_result.get("confidence", "0%"),
                "DETAILS": analysis_result.get("details", "No details available"),
            }  # AI관제 -> NODERED : 데이터(result)

            # Update task status based on result: TASK 만 ERROR
            if result["RESULT"] == "OK":
                self.update_task_status(task_name, "COMPLETED")
            else:
                self.update_task_status(task_name, "ERROR")

            self.logger.info(f"Task analysis completed: {result}")
            return result

        except Exception as e:
            # Update task status to ERROR if an exception occurs
            self.update_task_status(task_name, "ERROR")

            self.logger.error(f"Error processing task analysis: {e}")
            return {"NAME": task_name, "RESULT": "ERROR", "ORDER_NO": "UNKNOWN", "CONFIDENCE": "0%", "DETAILS": f"Error: {str(e)}"}

    def send_result_to_node_red(self, result: Dict[str, Any]):
        """
        Send processing results to Node-RED via REST API

        :param result: Processing result dictionary
        """
        try:
            print(result)
            # Use the stored Node-RED endpoint
            response = requests.post(self.nodered_endpoint, json=result, timeout=5)
            response.raise_for_status()
            self.logger.info(f"Results sent to Node-RED successfully: {result}")

        except requests.RequestException as e:
            self.logger.error(f"Failed to send results to Node-RED: {e}")
            raise

    def global_task_worker(self):
        """
        Single worker thread that processes all tasks from the global queue
        This ensures only one task is processed at a time
        """
        self.logger.info("Started global task worker thread")
        while True:
            # Get task from the global queue
            task_request = self.global_processing_queue.get()

            try:
                with global_task_lock:
                    # Set processing flag to true
                    with self.processing_lock:
                        self.is_processing = True
                        task_type = task_request.get("START", "UNKNOWN_TASK")
                        self.logger.info(f"Processing task {task_type}")

                    # Process the task
                    result = self.process_task_analysis(task_request)

                    # Send result to Node-RED
                    self.send_result_to_node_red(result)

            except Exception as e:
                task_type = task_request.get("START", "UNKNOWN_TASK")
                self.logger.error(f"Error in global worker processing {task_type}: {e}")
                # Update task status to ERROR if an exception occurs
                self.update_task_status(task_type, "ERROR")

            finally:
                # Set processing flag to false
                with self.processing_lock:
                    self.is_processing = False

                # Mark the task as done
                self.global_processing_queue.task_done()
                self.logger.info(f"Completed task and ready for next")

    def start_worker_threads(self):
        """
        Start the global task worker thread and the ping status thread
        """
        # Start global task worker thread
        task_thread = threading.Thread(target=self.global_task_worker, daemon=True)
        task_thread.start()
        self.logger.info("Started global task worker thread")

        # Start ping status thread
        ping_thread = threading.Thread(target=self.ping_status_worker, daemon=True)
        ping_thread.start()
        self.logger.info("Started ping status worker thread")

    def consume_messages(self):
        """
        Consume messages from RabbitMQ queues
        """
        try:
            # Callback for WEB_TO_AI queue
            # TODO: queue 필요 (5개 서버) web_to_ai
            def web_to_ai_callback(ch, method, properties, body):
                try:
                    # Parse the incoming JSON message
                    web_data = json.loads(body)
                    self.logger.info(f"Received web data: {web_data['ORDER_NO']}")

                    # Process and store the web data
                    self.process_web_message(web_data)

                    # Acknowledge message
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    self.logger.error(f"Error processing web message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            # Set up consumer for WEB_TO_AI queue
            self.channel.basic_consume(queue="WEB_TO_AI", on_message_callback=web_to_ai_callback)

            # Set up consumers for all Node-RED queues
            for queue_config in self.node_red_config:
                queue_name = queue_config["queue"]

                # Define a callback for all NodeRED queues
                def create_nodered_callback(queue):
                    def callback(ch, method, properties, body):
                        try:
                            # Parse the incoming JSON message
                            task_request = json.loads(body)
                            task_type = task_request.get("START", "UNKNOWN_TASK")
                            self.logger.info(f"Received task request in {queue}: {task_type}")

                            # Check if we're already processing a task
                            with self.processing_lock:
                                if self.is_processing:
                                    self.logger.info(f"Currently processing another task. Task {task_type} will be queued.")
                                else:
                                    self.logger.info(f"No tasks currently being processed. Task {task_type} will start soon.")

                            # Add the task to the global processing queue
                            self.global_processing_queue.put(task_request)
                            self.logger.info(f"Task {task_type} added to global processing queue")

                            # Acknowledge message
                            ch.basic_ack(delivery_tag=method.delivery_tag)

                        except Exception as e:
                            self.logger.error(f"Error processing task request in {queue}: {e}")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                    return callback

                # Set up consumer for this queue
                self.channel.basic_consume(queue=queue_name, on_message_callback=create_nodered_callback(queue_name))
                self.logger.info(f"Set up consumer for {queue_name}")

            self.logger.info("Waiting for messages. To exit press CTRL+C")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.connection.close()
            self.logger.info("Message consuming stopped")

    def run(self):
        """
        Main method to run the AI control system
        """
        try:
            self.connect_to_rabbitmq()
            self.start_worker_threads()
            self.consume_messages()
        except Exception as e:
            self.logger.error(f"AI Control System failed: {e}")
            raise


# # For running directly
# if __name__ == "__main__":
#     control_system = AIControlSystem()
#     control_system.run()
