import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from datasets import load_dataset
import os

class HuggingFaceHelper:
    def __init__(self, model_path="./merged_model", dataset_path=None):
        self.model_path = model_path
        self.dataset_path = dataset_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path).to(self.device)

    def load_dataset(self):
        if self.dataset_path:
            dataset = load_dataset("json", data_files=self.dataset_path, split="train")
            return dataset.map(self.tokenize_function, batched=True)
        raise ValueError("Dataset path not provided.")

    def tokenize_function(self, examples):
        return self.tokenizer(examples["messages"], truncation=True, padding="max_length", max_length=512)

    def fine_tune(self, output_dir="./fine_tuned_model", epochs=3, batch_size=4):
        dataset = self.load_dataset()

        training_args = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            per_device_train_batch_size=batch_size,
            num_train_epochs=epochs,
            weight_decay=0.01,
            push_to_hub=True,
            hub_model_id="Raiff1982/codriao-finetuned"
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=self.tokenizer,
        )

        trainer.train()
        self.save_model(output_dir)

    def save_model(self, output_dir):
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        print(f"â Model saved to {output_dir} and uploaded to Hugging Face Hub.")
