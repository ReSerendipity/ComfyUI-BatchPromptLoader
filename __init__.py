# Batch Prompt Loader
from .batch_prompt_loader import BatchPromptReaderWithClip

NODE_CLASS_MAPPINGS = {
    "BatchPromptReaderWithClip": BatchPromptReaderWithClip,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchPromptReaderWithClip": "批量提示词加载器 (Batch Prompt Loader)",
}
