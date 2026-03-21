import gradio as gr
import torch
from inference import CodetteModelLoader, CodetteEngine


ADAPTERS = {
    "Newton": "newton",
    "DaVinci": "davinci",
    "Empathy": "empathy",
    "Philosophy": "philosophy",
    "Quantum": "quantum",
    "RC-XI": "consciousness",
    "Multi-Perspective": "multi_perspective",
    "Systems": "systems_architecture"
}


def create_chat_app():

    loader = CodetteModelLoader(
        adapters={
            "newton": "adapters/newton/final",
            "davinci": "adapters/davinci/final",
            "empathy": "adapters/empathy/final",
            "philosophy": "adapters/philosophy/final",
            "quantum": "adapters/quantum/final",
            "consciousness": "adapters/consciousness/final",
            "multi_perspective": "adapters/multi_perspective/final",
            "systems_architecture": "adapters/systems_architecture/final",
        }
    )

    loader.load_adapters()

    registry = {
        name: {
            "generation": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 512
            }
        }
        for name in loader.adapters
    }

    engine = CodetteEngine(loader, registry)

    # -----------------------------------------------------
    # CHAT HANDLER
    # -----------------------------------------------------

    def chat_stream(message, history, adapter, temp, top_p, max_tokens):

        messages = []

        for user, assistant in history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})

        messages.append({"role": "user", "content": message})

        if adapter == "All (synthesized)":

            responses = engine.multi_perspective(
                messages,
                list(loader.adapters.keys())
            )

            reply = responses

            history.append((message, reply))

            yield history

            return

        adapter_key = ADAPTERS[adapter]

        loader.set_active_adapter(adapter_key)

        prompt = loader.format_messages(messages)
        inputs = loader.tokenize(prompt)

        streamer = engine.stream_generate(
            inputs,
            temperature=temp,
            top_p=top_p,
            max_tokens=max_tokens
        )

        response = ""

        for token in streamer:

            response += token

            yield history + [(message, response)]

        history.append((message, response))

    # -----------------------------------------------------
    # COMPARISON HANDLER
    # -----------------------------------------------------

    def compare(prompt, adapters):

        outputs = {}

        messages = [{"role": "user", "content": prompt}]

        for name in adapters:

            adapter_key = ADAPTERS[name]

            result = engine.generate(messages, adapter_key)

            outputs[name] = result

        return outputs

    # -----------------------------------------------------
    # STATUS PANEL
    # -----------------------------------------------------

    def get_status():

        device = loader.model.device

        if torch.cuda.is_available():

            mem = torch.cuda.memory_allocated() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3

            gpu_info = f"{mem:.2f}GB / {total:.2f}GB"

        else:

            gpu_info = "CPU"

        return {
            "Base Model": loader.base_model_name,
            "Active Adapter": loader.active_adapter,
            "Loaded Adapters": list(loader.adapters.keys()),
            "Device": str(device),
            "GPU Memory": gpu_info,
        }

    # -----------------------------------------------------
    # UI LAYOUT
    # -----------------------------------------------------

    with gr.Blocks(theme=gr.themes.Soft(), title="Codette") as app:

        gr.Markdown("# Codette Multi-Perspective AI")

        with gr.Tabs():

            # -------------------------------------------------
            # CHAT TAB
            # -------------------------------------------------

            with gr.Tab("Chat"):

                chatbot = gr.Chatbot(height=500)

                adapter = gr.Dropdown(
                    choices=list(ADAPTERS.keys()) + ["All (synthesized)"],
                    value="Multi-Perspective",
                    label="Reasoning Perspective"
                )

                with gr.Row():

                    temperature = gr.Slider(
                        0.0,
                        1.5,
                        value=0.7,
                        label="Temperature"
                    )

                    top_p = gr.Slider(
                        0.0,
                        1.0,
                        value=0.9,
                        label="Top P"
                    )

                    max_tokens = gr.Slider(
                        64,
                        2048,
                        value=512,
                        step=64,
                        label="Max Tokens"
                    )

                msg = gr.Textbox(
                    placeholder="Ask Codette something...",
                    lines=2
                )

                msg.submit(
                    chat_stream,
                    [msg, chatbot, adapter, temperature, top_p, max_tokens],
                    chatbot
                )

            # -------------------------------------------------
            # COMPARE TAB
            # -------------------------------------------------

            with gr.Tab("Compare"):

                prompt = gr.Textbox(label="Prompt")

                adapters = gr.CheckboxGroup(
                    choices=list(ADAPTERS.keys()),
                    label="Adapters to Compare",
                    value=["Newton", "DaVinci"]
                )

                output = gr.JSON()

                run = gr.Button("Run Comparison")

                run.click(
                    compare,
                    [prompt, adapters],
                    output
                )

            # -------------------------------------------------
            # STATUS TAB
            # -------------------------------------------------

            with gr.Tab("Status"):

                status_output = gr.JSON()

                refresh = gr.Button("Refresh")

                refresh.click(
                    get_status,
                    None,
                    status_output
                )

    return app