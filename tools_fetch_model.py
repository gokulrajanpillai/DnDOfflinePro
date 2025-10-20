from huggingface_hub import snapshot_download

# Download once so you can package the model for offline use
# This writes files into models/distilgpt2
snapshot_download(
    repo_id="distilgpt2",
    local_dir="models/distilgpt2",
    local_dir_use_symlinks=False
)

print("Model downloaded into models/distilgpt2")
