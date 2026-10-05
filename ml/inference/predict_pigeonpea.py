import torch
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

MODEL_PATH = Path("models/best_pigeonpea_disease_final_efficientnet_b0.pth")

def load_model():
    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=False
    )

    classes = checkpoint["classes"]

    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(
        model.classifier[1].in_features,
        len(classes)
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    return model, classes


transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])


def predict(image_path):
    model, classes = load_model()

    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        output = model(image_tensor)
        probabilities = torch.softmax(output, dim=1)

    confidence, predicted_index = torch.max(probabilities, 1)

    predicted_class = classes[predicted_index.item()]
    confidence_value = confidence.item() * 100

    print("\n==============================")
    print("   TurSathi AI Prediction")
    print("==============================")
    print(f"Image      : {image_path}")
    print(f"Prediction : {predicted_class}")
    print(f"Confidence : {confidence_value:.2f}%")
    print("==============================\n")


if __name__ == "__main__":
    image_path = input("Enter Tur leaf image path: ").strip().strip('"')

    if not Path(image_path).exists():
        print("ERROR: Image file not found.")
    else:
        predict(image_path)
