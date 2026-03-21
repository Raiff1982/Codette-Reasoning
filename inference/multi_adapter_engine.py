class CodetteEngine:

    def __init__(self, loader, registry):

        self.loader = loader
        self.registry = registry

    def generate(self, messages, adapter):

        self.loader.set_active_adapter(adapter)

        prompt = self.loader.format_messages(messages)
        inputs = self.loader.tokenize(prompt)

        params = self.registry[adapter]["generation"]

        output = self.loader.model.generate(
            **inputs,
            max_new_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature", 0.7),
            top_p=params.get("top_p", 0.9),
            repetition_penalty=params.get("repetition_penalty", 1.1)
        )

        text = self.loader.tokenizer.decode(
            output[0],
            skip_special_tokens=True
        )

        return text

    def multi_perspective(self, messages, adapters):

        outputs = {}

        for adapter in adapters:
            outputs[adapter] = self.generate(messages, adapter)

        return self._synthesize(messages, outputs)

    def _synthesize(self, messages, responses):

        combined = "\n\n".join(
            f"{name.upper()}:\n{text}"
            for name, text in responses.items()
        )

        synthesis_messages = messages + [
            {
                "role": "system",
                "content": "Combine the perspectives into a single answer."
            },
            {
                "role": "user",
                "content": combined
            }
        ]

        return self.generate(synthesis_messages, "multi_perspective")