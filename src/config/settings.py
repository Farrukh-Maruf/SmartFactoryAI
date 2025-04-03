import os
from dotenv import load_dotenv

{    'port': int(os.getenv('RABBITMQ_PORT', 5672)),
    'username': os.getenv('RABBITMQ_USER', 'admin_user'),
    'password': os.getenv('RABBITMQ_PASS', '123456#'),
}
# RabbitMQ Configuration
RABBITMQ_CONFIG = {
    'host': os.getenv('RABBITMQ_HOST', '192.168.1.104'),
    'port': int(os.getenv('RABBITMQ_PORT', 5672)),
    'username': os.getenv('RABBITMQ_USER', 'nsu_user'),
    'password': os.getenv('RABBITMQ_PASS', '1298!$'),
}

# Node-RED Configuration
NODERED_ENDPOINT = os.getenv('NODERED_ENDPOINT', 'http://192.168.1.105:1880/ai-result')

# Queue Configuration
QUEUE_CONFIG = {
    'exchange': 'NSU_NODERED_FAN',
    'exchange_type': 'fanout',
    'queues': {
        'web_to_ai': 'WEB_TO_AI',   
        'nodered_to_ai': 'NODERED_TO_AI'
    }
}

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')