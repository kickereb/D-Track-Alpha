import cv2
from ultralytics import YOLO

# Initialize video capture with the default webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

# Optional: Set frame size
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Load the YOLOv8 NCNN model
model = YOLO("yolov8n_ncnn_model")  # Use the NCNN model

# Initialize variables for calculating average inference time
total_inference_time = 0
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Run YOLO model on the captured frame and store the results
    results = model(frame)

    # Increment frame count
    frame_count += 1

    # Get inference time in milliseconds and add to total
    inference_time = results[0].speed['inference']
    total_inference_time += inference_time

    # Calculate FPS
    fps = 1000 / inference_time if inference_time > 0 else 0
    text = f'FPS: {fps:.1f}'

    # Copy the frame to draw on
    annotated_frame = frame.copy()

    # Define font for the FPS text
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Draw the FPS text on the frame
    text_size = cv2.getTextSize(text, font, 1, 2)[0]
    text_x = annotated_frame.shape[1] - text_size[0] - 10  # 10 pixels from the right
    text_y = text_size[1] + 10  # 10 pixels from the top

    cv2.putText(annotated_frame, text, (text_x, text_y), font, 1,
                (255, 255, 255), 2, cv2.LINE_AA)

    # For each detection, draw a point at the midpoint of the bottom edge of the bounding box
    detections = results[0].boxes

    for box in detections:
        # Get bounding box coordinates
        x1, y1, x2, y2 = box.xyxy[0]  # x1, y1, x2, y2 as tensors
        # Convert tensors to integers
        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        # Calculate midpoint of the bottom edge
        mid_x = (x1 + x2) // 2
        mid_y = y2  # Bottom edge y-coordinate

        # Draw a circle at the midpoint
        cv2.circle(annotated_frame, (mid_x, mid_y), radius=5, color=(0, 255, 0), thickness=-1)

    # Display the resulting frame
    cv2.imshow("Camera", annotated_frame)

    # Exit the program if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Calculate average inference time after the loop ends
if frame_count > 0:
    average_inference_time = total_inference_time / frame_count
    print(f"Average Inference Time: {average_inference_time:.2f} ms over {frame_count} frames")
else:
    print("No frames were processed.")

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
