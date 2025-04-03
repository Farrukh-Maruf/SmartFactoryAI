# First, uninstall your current OpenCV installation
# pip uninstall opencv-python opencv-python-headless

# Then install OpenCV with GUI support
# pip install opencv-python

import cv2
import numpy as np
import sys

def stream_video_from_url(url):
    # Create a VideoCapture object
    cap = cv2.VideoCapture(url)
    
    # Check if the video source opened successfully
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return
    
    print(f"Successfully connected to video stream at: {url}")
    
    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Video resolution: {frame_width}x{frame_height}, FPS: {fps}")
    
    try:
        # Create a window - only after confirming video source is opened
        cv2.namedWindow('Video Stream', cv2.WINDOW_NORMAL)
        
        while True:
            # Read a frame from the video source
            ret, frame = cap.read()
            
            # If frame is not read correctly, break the loop
            if not ret:
                print("Error: Failed to receive frame. Stream may have ended.")
                break
            
            # Display the frame
            cv2.imshow('Video Stream', frame)
            
            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Release the video capture object and close windows
        cap.release()
        cv2.destroyAllWindows()
        print("Stream closed.")

if __name__ == "__main__":
    # Check if URL is provided as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Using your URL from the error message
        url = "http://localhost:8882/video"
        print("No URL provided. Using: http://localhost:8881/video")
        print("Usage: python script.py <url>")
    
    # Start streaming
    stream_video_from_url(url)