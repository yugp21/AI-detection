import torch
import librosa
import os
from PIL import Image
from flask import Flask, render_template, request
from transformers import (
    AutoImageProcessor, 
    AutoModelForImageClassification, 
    pipeline, 
    AutoFeatureExtractor, 
    AutoModelForAudioClassification
)

app = Flask(__name__)
model_id = "Organika/sdxl-detector"
processor = AutoImageProcessor.from_pretrained(model_id)
model = AutoModelForImageClassification.from_pretrained(model_id)
text_detector = pipeline("text-classification", model="Hello-SimpleAI/chatgpt-detector-roberta")
audio_model_id = "Gustking/wav2vec2-large-xlsr-deepfake-audio-classification"
audio_feature_extractor = AutoFeatureExtractor.from_pretrained(audio_model_id)
audio_model = AutoModelForAudioClassification.from_pretrained(audio_model_id)

def detect_ai_image(image_pil):
    """Detects if an image is AI generated using your original logic."""
    inputs = processor(images=image_pil, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
    probs = torch.nn.functional.softmax(logits, dim=-1)
    predicted_class = torch.argmax(probs, dim=-1).item()
    confidence = probs[0][predicted_class].item() * 100
    label = model.config.id2label[predicted_class]
    
    if any(keyword in label.lower() for keyword in ["artificial", "fake", "ai", "sdxl"]):
        return "Fake Image", int(confidence)
    else:
        return "Real Image", int(confidence)

def detect_ai_voice(audio_path):
    """Detects AI-generated voice using Wav2Vec2."""
    speech, sr = librosa.load(audio_path, sr=16000)
    inputs = audio_feature_extractor(speech, sampling_rate=16000, return_tensors="pt")
    
    with torch.no_grad():
        logits = audio_model(**inputs).logits
    
    probs = torch.nn.functional.softmax(logits, dim=-1)
    predicted_class = torch.argmax(probs, dim=-1).item()
    confidence = probs[0][predicted_class].item() * 100
    
    # Model label mapping
    label = audio_model.config.id2label[predicted_class].lower()
    
    # Most deepfake models use label '1' or 'fake' for AI
    if "fake" in label or "synthetic" in label or predicted_class == 1:
        status = "AI Generated Voice"
    else:
        status = "Human Voice"
        
    return status, int(confidence)

@app.route("/", methods=["GET", "POST"])
def home():
    result, confidence = None, None
    if request.method == "POST":
        if 'image' in request.files:
            file = request.files["image"]
            if file.filename != '':
                image = Image.open(file).convert("RGB")
                result, confidence = detect_ai_image(image)
    return render_template("index.html", result=result, confidence=confidence)

@app.route("/text_page", methods=["GET", "POST"])
def text_page():
    result, confidence = None, None
    if request.method == "POST":
        text_input = request.form.get("text_content")
        
        if text_input and len(text_input.strip()) > 20:
            prediction = text_detector(text_input)[0]
            label = prediction['label'].lower()
            score = prediction['score']
            
            if label == 'chatgpt' or 'fake' in label:
                result = "AI Generated"
            else:
                result = "Human Written"
                
            confidence = int(score * 100)
        elif text_input:
            result = "Error: Text too short for reliable analysis"
            confidence = 0
            
    return render_template("text_detector.html", result=result, confidence=confidence)

@app.route("/voice_page", methods=["GET", "POST"])
def voice_page():
    result, confidence = None, None
    if request.method == "POST":
        if 'voice' in request.files:
            file = request.files["voice"]
            if file.filename != '':
                temp_path = "temp_voice_upload.wav"
                file.save(temp_path)
                
                try:
                    result, confidence = detect_ai_voice(temp_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
    return render_template("voice_detector.html", result=result, confidence=confidence)

@app.route("/about")
def about():
    return render_template("about.html")
3
if __name__ == "__main__":
    app.run(debug=True)