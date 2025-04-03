import json
import os
import time
from typing import Any, Dict, Optional
from uuid import uuid4

import cv2
import easyocr
import numpy as np
from pyzbar.pyzbar import decode
from ultralytics import YOLO

from src.utils.camera import GalaxyCamera
from src.utils.logger import setup_logger

# Ensure the directory exists
SAVE_DIR = "./saved_frames"
SAVE_DIRS = [
    r"Z://",
    r"Y://",
    r"X://",
]
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

logger = setup_logger(__name__)


def save_video(frames, task_name: str, camera_id: int, fps: float = 30.0, extension="mp4") -> str:
    # Generate a unique file name using UUID
    unique_id = str(uuid4())
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Default to MP4 with H264 codec which is browser-compatible
    fourcc = cv2.VideoWriter_fourcc(*"H264")
    filename = f"{task_name}_{camera_id}_{timestamp}_{unique_id}.{extension}"
    file_path = os.path.join(SAVE_DIR, filename)

    # Set up dimensions for the video
    height, width = frames[0].shape[:2]

    # Try to create the VideoWriter with H264 codec
    out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

    # If H264 isn't available, try alternatives
    if not out.isOpened():
        # Try DIVX with AVI container (these are compatible)
        extension = "avi"
        fourcc = cv2.VideoWriter_fourcc(*"DIVX")
        filename = f"{task_name}_{camera_id}_{timestamp}_{unique_id}.{extension}"
        file_path = os.path.join(SAVE_DIR, filename)
        out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))
        logger.info("Using DIVX codec with AVI container")

        # If DIVX fails too, try MJPG with AVI
        if not out.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            filename = f"{task_name}_{camera_id}_{timestamp}_{unique_id}.{extension}"
            file_path = os.path.join(SAVE_DIR, filename)
            out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))
            logger.info("Using MJPG codec with AVI container")

    # Write frames to video file
    for frame in frames:
        out.write(frame)

    # Release the VideoWriter
    out.release()

    # Log the saved video
    logger.info(f"Saved video {task_name} to {file_path}")

    return file_path


def save_frame(frame, task_name: str, camera_id: int, extension="jpg") -> str:
    # Generate a unique file name using UUID
    unique_id = str(uuid4())
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{task_name}_{camera_id}_{timestamp}_{unique_id}.{extension}"

    file_path = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(file_path, frame)
    
    for save_d in SAVE_DIRS:
        d_file_path = os.path.join(save_d, filename)
        # Save the frame
        cv2.imwrite(d_file_path, frame)

    # Log the saved image
    logger.info(f"Saved {task_name} frame to {file_path}")

    return file_path


class TaskAnalyzer:
    """
    Comprehensive task analyzer with methods for different inspection tasks
    """

    __folding_value = None

    @staticmethod
    def _init_camera(camera_id: int = 1) -> Optional[cv2.VideoCapture]:
        """
        Initialize the camera and load the corresponding order data from a JSON file.

        :param camera_id: Camera device ID (default is 1 for primary camera)
        :param order_no: Order number to load the corresponding JSON data
        :return: VideoCapture object or None if camera initialization fails and current order data
        """
        # TODO: Initialize camera
        # 카메라 접속 IP
        camera = GalaxyCamera(1)
        # camera = cv2.VideoCapture(f"http://localhost:888{camera_id}/video")
        if not camera.isOpened():
            return None, None

        order_file_path = f"order_data.json"
        if os.path.exists(order_file_path):
            with open(order_file_path, "r") as json_file:
                current_order_data = json.load(json_file)
                return camera, current_order_data
        else:
            return camera, None  # No file found for the given order_no

        return camera, None

    @staticmethod
    def _read_qr_code(frame: np.ndarray) -> Optional[str]:
        """
        Read QR code from a frame

        :param frame: Image frame from camera
        :return: Decoded QR code text or None if no QR code found
        """
        # Convert frame to grayscale for better QR code detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Decode QR codes in the frame
        qr_codes = decode(gray)

        if qr_codes:
            # Return the text from the first detected QR code
            return qr_codes[0].data.decode("utf-8")
        return None

    @staticmethod
    def _perform_ocr(frame: np.ndarray) -> Optional[str]:
        """
        Perform OCR on the frame with Korean language support

        :param frame: Image frame from camera
        :return: Detected text or None if no text found
        """
        try:

            reader = easyocr.Reader(["ko"])  # 'en' stands for English
            # Use easyocr to extract text from the image
            result = reader.readtext(frame)

            # Print the result
            for detection in result:
                text = detection[1]  # The detected text
                # print(text)

            return text if text else None

        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            return None

    @staticmethod
    def _analyze_color_coverage(frame: np.ndarray, color: str) -> tuple[float, np.ndarray]:
        """
        Analyze the coverage of a specific color in the frame

        :param frame: Input frame
        :param color: Color to analyze ('yellow' or 'red')
        :return: Tuple of (coverage percentage, mask)
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        if color == "yellow":
            # Adjusted range for deeper yellows (amber tones)
            lower = np.array([10, 100, 100])  # Adjusted lower bound for deeper yellows
            upper = np.array([40, 255, 255])  # Upper bound for yellow

            # Create mask for yellow
            mask = cv2.inRange(hsv, lower, upper)
        else:  # red
            # Adjusted ranges for red
            lower1 = np.array([0, 150, 50])  # Low saturation, dark red
            upper1 = np.array([10, 255, 150])  # Light red to dark red
            lower2 = np.array([170, 150, 50])  # Dark red hue
            upper2 = np.array([180, 255, 150])  # Dark red hue range

            # Create masks for both red ranges and combine
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)

        # Calculate the coverage percentage
        coverage = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])

        return coverage, mask

    @staticmethod
    def _detect_dominant_color(frame: np.ndarray) -> str:
        """
        Detects the dominant color (red, green, blue, or no_color) in a given frame.

        :param frame: The input frame as a numpy array (from OpenCV).
        :return: A string representing the dominant color: 'red', 'green', 'blue', or 'no_color'.
        """
        # Calculate the average color for each channel (Red, Green, Blue)
        # OpenCV stores images in BGR format, so we adjust accordingly
        blue_avg, green_avg, red_avg = np.mean(frame, axis=(0, 1))  # BGR order in OpenCV

        # Check which color channel is dominant and return the corresponding color
        if green_avg > red_avg and green_avg > blue_avg:
            return "green"
        elif red_avg > green_avg and red_avg > blue_avg:
            return "red"
        elif blue_avg > red_avg and blue_avg > green_avg:
            return "blue"
        else:
            return "no_color"

    @staticmethod
    def case_task_analysis(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        camera_id = 1
        timeout = task_data.get("timeout", 10) if task_data else 10
        result = {"task_name": "case_task", "status": "NG", "confidence": "0%", "details": "Q002"}  # Default error code

        camera, current_order_data = TaskAnalyzer._init_camera(camera_id)
        if not camera:
            result["details"] = "Q002"
            return result

        frames = []
        try:
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                ret, frame = camera.read()
                if not ret:
                    continue

                frames.append(frame)
                qr_text = TaskAnalyzer._read_qr_code(frame)

                if qr_text == current_order_data["BOM"][2]["ITEM_NM"]:
                    result["status"] = "OK"
                    result["confidence"] = "95%"
                    result["details"] = "OK"  # Changed to OK for success
                    # saved_video_path = save_video(frames, "case_task", camera_id)
                    saved_video_path = save_frame(frame, "case_task", camera_id)
                    result["saved_file_path"] = saved_video_path
                    break

                time.sleep(0.1)

            if result["status"] == "NG":
                # saved_video_path = save_video(frames, "case_task", camera_id)
                saved_video_path = save_frame(frame, "case_task", camera_id)
                result["saved_file_path"] = saved_video_path

        except Exception as e:
            result["details"] = "Q002"
            logger.error(f"Case task error: {str(e)}")
        finally:
            camera.release()

        return result

    @staticmethod
    def box_task_analysis(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        camera_id = task_data.get("camera_id", 2) if task_data else 2
        result = {"task_name": "box_task", "status": "NG", "confidence": "0%", "details": "Q014"}  # Default error

        camera, current_order_data = TaskAnalyzer._init_camera(camera_id)
        if not camera:
            return result

        try:
            ret, frame = camera.read()
            if not ret:
                return result

            frame = cv2.resize(frame, (640, 480))
            saved_frame_path = save_frame(frame, "box_task", camera_id)
            result["saved_file_path"] = saved_frame_path

            # Check QR code first
            qr_text = TaskAnalyzer._read_qr_code(frame)

            logger.info(qr_text)

            # Try OCR if QR fails
            ocr_text = TaskAnalyzer._perform_ocr(frame)

            logger.info(ocr_text)

            # If both fail, check for box color
            box_color = TaskAnalyzer._detect_dominant_color(frame)

            logger.info(box_color)

            ocr_text_map = {"BIG BOX": "대형", "MIDDLE BOX": "중형"}

            color_map = {"BIG BOX": "red", "MIDDLE BOX": "blue"}

            box_type = current_order_data["BOM"][1]["ITEM_NM"]

            # if qr_text == box_type and ocr_text == ocr_text_map[box_type] and box_color == color_map[box_type]:

            if box_color == "no_color":
                result["status"] = "NG"
                result["confidence"] = "0%"
                result["details"] = "Q014"
                return result

            elif qr_text.lower() != box_type.lower():
                result["status"] = "NG"
                result["confidence"] = "0%"
                result["details"] = "Q012"
                return result

            elif ocr_text != ocr_text_map[box_type]:
                result["status"] = "NG"
                result["confidence"] = "0%"
                result["details"] = "Q013"
                return result

            elif box_color != color_map[box_type]:
                result["status"] = "NG"
                result["confidence"] = "0%"
                result["details"] = "Q011"
                return result

            else:
                result["status"] = "OK"
                result["confidence"] = "95%"
                result["details"] = "OK"
                return result

        except Exception as e:
            logger.error(f"Box task error: {str(e)}")
        finally:
            camera.release()

        return result

    @staticmethod
    def cover_task_analysis(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        camera_id = task_data.get("camera_id", 3) if task_data else 3
        result = {"task_name": "cover_task", "status": "NG", "confidence": "0%", "details": "Q022", "saved_file_path": ""}  # Initialize with empty string

        camera, current_order_data = TaskAnalyzer._init_camera(camera_id)
        if not camera:
            result["details"] = f"Failed to initialize camera {camera_id}"
            return result

        try:
            ret, frame = camera.read()
            if not ret:
                result["details"] = "Failed to capture frame"
                return result

            # Save the frame to disk
            saved_frame_path = save_frame(frame, "cover_task", camera_id)
            # Store the path in the result dictionary
            result["saved_file_path"] = saved_frame_path

            # Analyze color coverage
            yellow_coverage, _ = TaskAnalyzer._analyze_color_coverage(frame, "yellow")
            red_coverage, _ = TaskAnalyzer._analyze_color_coverage(frame, "red")
            total_coverage = yellow_coverage + red_coverage

            if total_coverage >= task_data.get("color_threshold", 0.15):
                result["status"] = "OK"
                result["confidence"] = f"{min(total_coverage * 100, 100):.1f}%"
                colors_detected = []
                if yellow_coverage >= task_data.get("color_threshold", 0.15) / 2:
                    colors_detected.append("yellow")
                if red_coverage >= task_data.get("color_threshold", 0.15) / 2:
                    colors_detected.append("red")
                result["details"] = colors_detected
            else:
                result["details"] = "Q022"

        except Exception as e:
            result["details"] = f"Error during cover color analysis: {str(e)}"
            logger.error(f"Cover analysis error: {str(e)}")

        finally:
            camera.release()

        print(result["details"], current_order_data["BOM"][2]["ITEM_NM"])

        final_result = {}  # Create a new dictionary for the final result

        if isinstance(result["details"], list) and len(result["details"]) > 0:
            if result["details"][0] == "yellow" and current_order_data["BOM"][2]["ITEM_NM"] == "C":
                final_result = {
                    "task_name": "cover_task",
                    "status": "OK",
                    "confidence": result["confidence"],
                    "details": "OK",
                    "saved_file_path": result["saved_file_path"],  # Preserve the saved file path
                }

            elif result["details"][0] == "red" and (current_order_data["BOM"][2]["ITEM_NM"] == "B" or current_order_data["BOM"][2]["ITEM_NM"] == "A"):
                final_result = {
                    "task_name": "cover_task",
                    "status": "OK",
                    "confidence": result["confidence"],
                    "details": "OK",
                    "saved_file_path": result["saved_file_path"],  # Preserve the saved file path
                }
            else:
                if result["confidence"] != "0%":
                    final_result = {
                        "task_name": "cover_task",
                        "status": "NG",
                        "confidence": result["confidence"],
                        "details": "Q021",
                        "saved_file_path": result["saved_file_path"],  # Preserve the saved file path
                    }
                    return final_result

        # If no specific case was matched, return the original result
        return result if not final_result else final_result

    @staticmethod
    def folding_task_analysis(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:

        TaskAnalyzer.__folding_value = None

        camera_id = 1
        model_path = "src/models/best.pt"
        result = {
            "task_name": "folding_task",
            "status": "NG",
            "confidence": "0%",
            "details": "Q034",
        }  # Default error

        camera, current_order_data = TaskAnalyzer._init_camera(camera_id)
        if not camera:
            return result

        try:
            model = YOLO(model_path)
            if not model:
                return result

            ret, frame = camera.read()
            if not ret:
                return result

            saved_frame_path = save_frame(frame, "folding_task", camera_id)
            result["saved_file_path"] = saved_frame_path

            results = model(frame)
            # Extract the first detected object and its class name
            if len(results) > 0:
                # Get the first result (first image)
                first_result = results[0]

            # Check if any objects were detected
            if len(first_result.boxes) > 0:
                # Get the first detected object
                first_box = first_result.boxes[0]

                # Get the class ID (integer)
                class_id = int(first_box.cls[0].item())

                # Get the class name (string)
                class_name = first_result.names[class_id]

                if class_name == "OK":

                    confidence = float(results[0].boxes[0].conf.item())
                    result["status"] = "OK"
                    result["confidence"] = f"{confidence * 100:.1f}%"
                    result["details"] = "OK"
                    # TODO: gloval 변수 저장
                    TaskAnalyzer.__folding_value = None
                    return result
                else:
                    result["status"] = "NG"
                    result["confidence"] = f"0%"
                    result["details"] = "NG"
                    # TODO: gloval 변수 저장
                    TaskAnalyzer.__folding_value = "NG"
                    return result
            else:
                result["status"] = "NG"
                result["confidence"] = f"0%"
                result["details"] = "Q034"
                # TODO: gloval 변수 저장
                TaskAnalyzer.__folding_value = "NG"
                return result

        except Exception as e:
            logger.error(f"Folding task error: {str(e)}")
        finally:
            camera.release()

        return result  # TODO: result variable saving

    @staticmethod
    def final_check_task_analysis(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """robot
        Final comprehensive task analysis
        Uses single frame capture.

        :param task_data: Optional task-specific data
        :return: Analysis result dictionary
        """
        camera_id = 1

        # Initialize result dictionary
        result = {"task_name": "final_check_task", "status": "NG", "confidence": "0%", "details": "Final check analysis not started"}

        # Initialize camera
        camera, current_order_data = TaskAnalyzer._init_camera(camera_id)
        if not camera:
            result["details"] = f"Failed to initialize camera {camera_id}"
            return result

        try:
            # Capture single frame
            ret, frame = camera.read()
            if not ret:
                result["details"] = "Failed to capture frame"
                return result

            # Save the captured frame as an image
            saved_frame_path = save_frame(frame, "final_check_task", camera_id)
            # 추후 모델 적용 예정

            # TODO: last folding result
            # folding 이 OK 이거나 NG 이거나 상관없이 Robot Image 전송
            if TaskAnalyzer.__folding_value is not None:
                result["status"] = "OK"
                result["confidence"] = "96%"
                result["details"] = "OK"
                result["saved_file_path"] = saved_frame_path
                return result

            else:
                result["status"] = "NG"
                result["confidence"] = "0%"
                result["details"] = "NG"
                result["saved_file_path"] = saved_frame_path
                # TODO: robot result - 현재 모두 OK, NG 시 robot 이미지
                return result
            
        except Exception as e:
            result["details"] = f"Error during final check: {str(e)}"
            logger.error(f"Final check error: {str(e)}")

        finally:
            # Always release the camera
            camera.release()

        return result
