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

# Load the YOLOv8 model
model = YOLO("yolov8n.pt")

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

    # Output the visual detection data by drawing it on our camera preview window
    annotated_frame = results[0].plot()

    # Define font and position for the FPS text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 1, 2)[0]
    text_x = annotated_frame.shape[1] - text_size[0] - 10  # 10 pixels from the right
    text_y = text_size[1] + 10  # 10 pixels from the top

    # Draw the FPS text on the annotated frame
    cv2.putText(annotated_frame, text, (text_x, text_y), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

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
