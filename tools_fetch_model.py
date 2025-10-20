from huggingface_hub import snapshot_download

# Download once so you can package the model for offline use
# TinyLlama chat model, small and instruction tuned
snapshot_download(
    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    local_dir="models/tinyllama-chat",
    local_dir_use_symlinks=False
)
print("Model downloaded into models/tinyllama-chat")
