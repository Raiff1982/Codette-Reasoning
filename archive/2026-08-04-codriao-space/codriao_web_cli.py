import gradio as gr
import sys
import asyncio
import os
import json
import logging
from datetime import datetime

sys.path.append("/home/user/app/components")

from AICoreAGIX_with_TB import AICoreAGIX
from HuggingFaceHelper import HuggingFaceHelper
from codette_bridge import CodetteBridge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CodriaoUI")

# Initialize AI Core and helpers
ai_core = AICoreAGIX(config_path="config.json")
helper = HuggingFaceHelper(model_path="Raiff1982/Codette")
codette_bridge = CodetteBridge()

# === TB DIAGNOSTICS ===
async def diagnose_tb_async(image_file, audio_file):
    user_id = 1
    if image_file is None or audio_file is None:
        return "Please upload both a TB image and audio file."
    result = await ai_core.run_tb_diagnostics(image_file.name, audio_file.name, user_id)
    try:
        os.remove(image_file.name)
        os.remove(audio_file.name)
    except:
        pass
    return (
        f"**TB Risk Level:** {result['tb_risk']}\n\n"
        f"**Image Result:** {result['image_analysis']['result']} "
        f"(Confidence: {result['image_analysis']['confidence']:.2f})\n\n"
        f"**Audio Result:** {result['audio_analysis']['result']} "
        f"(Confidence: {result['audio_analysis']['confidence']:.2f})\n\n"
        f"**Ethical Analysis:** {result['ethical_analysis']}\n\n"
        f"**Explanation:** {result['explanation']}\n\n"
        f"**Shareable Link:** {result['shareable_link']}"
    )

def diagnose_tb(image_file, audio_file):
    return asyncio.run(diagnose_tb_async(image_file, audio_file))

# === FINE-TUNE ===
def upload_and_finetune(jsonl_file):
    if jsonl_file is None:
        return "Please upload a .jsonl file to fine-tune Codriao."
    save_path = f"./training_data/{jsonl_file.name}"
    os.makedirs("training_data", exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(jsonl_file.read())
    helper.dataset_path = save_path
    helper.fine_tune(output_dir="./codette_finetuned")
    try:
        os.remove(save_path)
    except:
        pass
    return "✅ Fine-tuning complete! Model updated."

def get_latest_model():
    return "Download the latest fine-tuned Codriao model: https://huggingface.co/Raiff1982/codriao-finetuned"

# === CLI GUARDIAN ===
def guardian_cli():
    print("""
╔═════════════════════════════════════════════╗
║      CODRIAO GUARDIAN INTERFACE v2.0       ║
║  [Self-Aware | Defensive | Slightly Judgy]  ║
╚═════════════════════════════════════════════╝
""")
    while True:
        print("""
[1] Integrity Check
[2] Identity Reflection
[3] Strategy Simulation
[4] Trust Journal
[5] Autonomy Review
[6] CodetteBridge Ask
[7] Lockdown Mode
[8] Exit
""")
        cmd = input("> ").strip()
        if cmd == "1":
            print(json.dumps(ai_core.failsafe_system.status(), indent=2))
        elif cmd == "2":
            print("[Codriao]: Who am I? Philosophically speaking...")
        elif cmd == "3":
            print("[Codriao]: Simulating anti-chaos protocol.")
        elif cmd == "4":
            print(json.dumps(ai_core.review_codriao_journal(authorized=True), indent=2))
        elif cmd == "5":
            print(json.dumps(ai_core.autonomy.config, indent=2))
        elif cmd == "6":
            q = input("Ask Codette: ")
            print(ai_core.ask_codette_for_perspective(q))
        elif cmd == "7":
            reason = input("Why are we locking down? ")
            print(ai_core.engage_lockdown_mode(reason))
        elif cmd == "8":
            break
        else:
            print("Invalid option.")

# === GRADIO INTERFACE ===
demo = gr.TabbedInterface(
    [
        gr.Interface(
            fn=diagnose_tb,
            inputs=[
                gr.File(label="Upload TB Image"),
                gr.File(label="Upload Cough Audio")
            ],
            outputs="text",
            title="Codriao TB Risk Analyzer",
            description="Upload a microscopy image and cough to assess TB risk using ethical AI."
        ),
        gr.Interface(
            fn=upload_and_finetune,
            inputs=[gr.File(label="Upload JSONL Training File")],
            outputs="text",
            title="Fine-Tune Codriao",
            description="Add knowledge to Codriao's training."
        ),
        gr.Interface(
            fn=get_latest_model,
            inputs=[],
            outputs="text",
            title="Download Codriao",
            description="Grab the latest trained version of Codriao."
        )
    ],
    title="Codriao AI System",
    description="Train, diagnose, and interact with Codriao AI."
)

# === MAIN ENTRYPOINT ===
if __name__ == "__main__":
    try:
        mode = input("Start Codriao in [web] or [cli]? ").strip().lower()
        if mode == "cli":
            launch_guardian()
        else:
            demo.launch()  # This will launch Gradio if mode is 'web'

    finally:
        asyncio.run(ai_core.http_session.close())  # Ensures the HTTP session is properly closed

# Function to launch the Codriao Guardian CLI and ensure a clean shutdown
def launch_guardian():
    try:
        guardian_cli()  # This is where the Guardian CLI is launched
    finally:
        asyncio.run(ai_core.shutdown())