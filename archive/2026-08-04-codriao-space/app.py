import gradio as gr
import sys
import asyncio
sys.path.append("/home/user/app/components")
from HuggingFaceHelper import HuggingFaceHelper
from AICoreAGIX_with_TB import AICoreAGIX
from codriao_web_cli import guardian_cli
import os
# os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import tensorflow as tf

# Limit GPU memory usage (if GPU exists)
gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    try:
        tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print("[TF] GPU memory growth config error: {e}")
# Initialize AI Core for TB analysis
ai_core = AICoreAGIX()

# Initialize Hugging Face training helper
helper = HuggingFaceHelper(model_path="Raiff1982/Codette")

async def diagnose_tb_async(image_file, audio_file):
    user_id = 1  # Placeholder user ID

    if image_file is None or audio_file is None:
        return "Please upload both a TB saliva image and a cough audio file."

    result = await ai_core.run_tb_diagnostics(image_file.name, audio_file.name, user_id)

    # Optional file cleanup
    try:
        os.remove(image_file.name)
        os.remove(audio_file.name)
    except:
        pass

    return (
        "**TB Risk Level:** {result['tb_risk']}\n\n"
        "**Image Result:** {result['image_analysis']['result']} "
        "(Confidence: {result['image_analysis']['confidence']:.2f})\n\n"
        "**Audio Result:** {result['audio_analysis']['result']} "
        "(Confidence: {result['audio_analysis']['confidence']:.2f})\n\n"
        "**Ethical Analysis:** {result['ethical_analysis']}\n\n"
        "**Explanation:** {result['explanation']}\n\n"
        "**Shareable Link:** {result['shareable_link']}"
    )

def diagnose_tb(image_file, audio_file):
    return asyncio.run(diagnose_tb_async(image_file, audio_file))

def upload_and_finetune(jsonl_file):
    if jsonl_file is None:
        return "Please upload a .jsonl file to fine-tune Codriao."

    save_path = "./training_data/{jsonl_file.name}"
    os.makedirs("training_data", exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(jsonl_file.read())

    # Trigger fine-tuning
    helper.dataset_path = save_path
    helper.fine_tune(output_dir="./codette_finetuned")

    try:
        os.remove(save_path)
    except:
        pass

    return " Fine-tuning complete! Model updated and stored."

def get_latest_model():
    return "Download the latest fine-tuned Codriao model here: https://huggingface.co/Raiff1982/codriao-finetuned"

# Gradio UI
demo = gr.TabbedInterface(
    [
        gr.Interface(
            fn=diagnose_tb,
            inputs=[
                gr.File(label="Upload TB Saliva Image"),
                gr.File(label="Upload Cough Audio File (.wav)")
            ],
            outputs="text",
            title="Codriao TB Risk Analyzer",
            description="Upload a microscopy image and cough audio to analyze TB risk with compassionate AI support."
        ),
        gr.Interface(
            fn=upload_and_finetune,
            inputs=[gr.File(label="Upload JSONL Training Data")],
            outputs="text",
            title="Codriao Fine-Tuning Trainer",
            description="Upload JSONL files to teach Codriao new knowledge."
        ),
        gr.Interface(
            fn=get_latest_model,
            inputs=[],
            outputs="text",
            title="Download Codriao's Fine-Tuned Model"
        )
    ],
    title="Codriao AI System",
    description="Train Codriao, run TB diagnostics, and download updated models."
)


if __name__ == "__main__":
    try:
        mode = input("Launch Codriao in [cli] or [web] mode? ").strip().lower()
        if mode == "cli":
            guardian_cli()
        else:
            demo.launch()
    finally:
        asyncio.run(ai_core.shutdown())