from huggingface_hub import HfApi
from pathlib import Path


api = HfApi()


ADAPTER_DIR = "adapters"

REPO_PREFIX = "codette"


def upload():

    for adapter in Path(ADAPTER_DIR).iterdir():

        repo = f"{REPO_PREFIX}-{adapter.name}"

        api.create_repo(repo_id=repo, exist_ok=True)

        api.upload_folder(
            repo_id=repo,
            folder_path=str(adapter),
            commit_message=f"Upload adapter {adapter.name}"
        )


if __name__ == "__main__":
    upload()