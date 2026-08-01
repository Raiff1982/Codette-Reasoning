"""
Gradio chat/image demo.

Recovered from app.txt.
"""

# This Gradio app allows users to interact with a chatbot that can generate text and images based on user prompts.
import gradio as gr
import numpy as np
from transformers_js import pipeline  # Corrected import to use transformers_js instead of transformers_js_py

# Define the available models
AVAILABLE_MODELS = {
    "GPT-2": "gpt2",
    "DALL-E": "dalle-mini/dalle-mini-1.3B"
}

# Initialize the text generation pipeline
text_generator = pipeline("text-generation", model=AVAILABLE_MODELS["GPT-2"])

# Initialize the image generation pipeline
image_generator = pipeline("image-generation", model=AVAILABLE_MODELS["DALL-E"])

# Function to generate text
def generate_text(prompt, model):
    np.random.seed(42)  # Set a seed for reproducibility
    if model == "GPT-2":
        return text_generator(prompt, max_length=50, num_return_sequences=1)[0]['generated_text']
    else:
        return "Model not supported for text generation"

# Function to generate images
def generate_image(prompt, model):
    if model == "DALL-E":
        image = image_generator(prompt, num_inference_steps=50, guidance_scale=7.5).images[0]
        return image
    else:
        return "Model not supported for image generation"

# Create the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Chatbot with Text and Image Generation")
    
    with gr.Tab("Text Generation"):
        text_prompt = gr.Textbox(label="Enter your text prompt")
        text_model = gr.Radio(choices=list(AVAILABLE_MODELS.keys()), label="Choose a model", value="GPT-2")
        text_output = gr.Textbox(label="Generated Text")
        text_button = gr.Button("Generate Text")
        text_button.click(generate_text, inputs=[text_prompt, text_model], outputs=text_output)
    
    with gr.Tab("Image Generation"):
        image_prompt = gr.Textbox(label="Enter your image prompt")
        image_model = gr.Radio(choices=list(AVAILABLE_MODELS.keys()), label="Choose a model", value="DALL-E")
        image_output = gr.Image(label="Generated Image")
        image_button = gr.Button("Generate Image")
        image_button.click(generate_image, inputs=[image_prompt, image_model], outputs=image_output)

# Launch the interface
demo.launch(show_error=True)