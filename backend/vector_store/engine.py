import torch
import open_clip
from PIL import Image
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class VectorEngine:
    def __init__(self, model_name="ViT-B-32", pretrained="laion2b_s34b_b79k", device="cpu"):
        """
        Initializes the CLIP model. 
        Defaults to CPU to strictly protect the 8GB VRAM limit for the LLaVA model later.
        """
        logger.info(f"Initializing OpenCLIP model {model_name} on {device}...")
        self.device = device
        
        # Load model and preprocess functions
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, 
            pretrained=pretrained,
            device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        
        logger.info("OpenCLIP model initialized successfully.")

    def embed_artifact(self, image_path: str, text_metadata: str):
        """
        Takes a micro-cropped ROI .png and its metadata, passing them through 
        the CLIP image and text encoders to create a joint embedding.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")
            
        logger.info(f"Embedding artifact: {image_path} with metadata: '{text_metadata}'")
        
        # Preprocess image
        image = Image.open(image_path).convert("RGB")
        image_input = self.preprocess(image).unsqueeze(0).to(self.device)
        
        # Preprocess text
        text_input = self.tokenizer([text_metadata]).to(self.device)
        
        # Disable gradient calculation for inference.
        # autocast is only enabled on CUDA; on CPU it is a no-op that also
        # generates deprecation warnings in PyTorch 2.3+.
        autocast_ctx = (
            torch.amp.autocast(device_type="cuda")
            if self.device == "cuda"
            else torch.no_grad()
        )
        with torch.no_grad(), autocast_ctx:
            image_features = self.model.encode_image(image_input)
            text_features = self.model.encode_text(text_input)
            
            # Normalize the features
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Create a joint multimodal embedding by averaging the normalized vectors
            joint_embedding = (image_features + text_features) / 2.0
            joint_embedding /= joint_embedding.norm(dim=-1, keepdim=True)
            
        return joint_embedding.cpu().numpy()
