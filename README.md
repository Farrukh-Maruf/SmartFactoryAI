# Smart Factory AI
A project to integrate AI control systems for smart factories. This project uses RabbitMQ for task messaging, Node-RED for result endpoints, and a configurable logging system.

## Table of Contents
- [Hardware Connection](#hardware-connection)
- [Setup](#setup)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Running the Project](#running-the-project)
- [Project Structure](#project-structure)
---

## Hardware Connection
0. Machine Vision Camera Connection:
   ```
   1. Connect the Vieworks cameras to the SmartFactoryAI server PC
   2. Run the Vieworks dedicated application to verify camera connections
   3. Check the IP address and port settings for each camera
   4. Configure the camera settings as follows:
      - Exposure Time
      - Gain
      - Trigger Mode
      - Image Format
   5. Capture test images to verify cameras are functioning properly
   ```

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/otabek-olimjonov/SmartFactoryAI.git
   cd smart_factory_ai
   ```

2. Copy `.env.sample` to `.env` and replace the necessary environment variables:
   ```bash
   cp .env.sample .env
   ```
   Open `.env` and configure the following:
   ```
   RABBITMQ_HOST=localhost       # RabbitMQ server address
   RABBITMQ_PORT=5672           # RabbitMQ port
   RABBITMQ_USER=admin_user     # RabbitMQ username
   RABBITMQ_PASS=123456#        # RabbitMQ password
   NODERED_ENDPOINT=http://localhost:1880/ai-result  # Node-RED endpoint for results
   LOG_LEVEL=INFO               # Logging level (e.g., INFO, DEBUG, ERROR)
   ```

## Dependencies
Install the required dependencies using `pip`:
```bash
pip install -r requirements.txt
```
> **Note:** Ensure you have Python 3.8+ installed.

## Running the Project
To start the project, run the following command:
```bash
python main.py
```
The application will:
- Connect to RabbitMQ for task messaging.
- Process tasks using the AI control system.
- Send results to the configured Node-RED endpoint.
- Log events based on the configured log level.

## Project Structure
```
smart_factory_ai/
├── README.md              # Documentation
├── app.log                # Log file
├── main.py                # Entry point of the application
├── requirements.txt       # Python dependencies
├── src/
│   ├── config/
│   │   └── settings.py    # Configuration management
│   ├── core/
│   │   ├── ai_control_system.py   # Core logic for AI control
│   │   └── task_analyzer.py       # Analyzes tasks for AI processing
│   ├── tasks/
│   │   ├── box.py                 # Box-related task logic
│   │   ├── case.py                # Case-related task logic
│   │   ├── cover.py               # Cover-related task logic
│   │   ├── final_check.py         # Final check logic
│   │   └── folding.py             # Folding task logic
│   └── utils/
│       └── logger.py      # Logging utility
├── test.py                # Test script
└── tests/                 # Placeholder for tests
```

## Notes
- Ensure RabbitMQ and Node-RED are running on the specified hosts before starting the project.
- Modify `src/config/settings.py` if additional configurations are required.
- Refer to the camera manufacturer's technical support if you encounter issues with Vieworks camera settings.
