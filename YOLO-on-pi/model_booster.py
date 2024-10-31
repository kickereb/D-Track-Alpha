from ultralytics import YOLO

# Load the PyTorch model (replace 'yolov8n.pt' with your model if different)
model = YOLO("yolov8n.pt")

# Export the model to NCNN format
model.export(format="ncnn")
print('done')