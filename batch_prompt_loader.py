"""
ComfyUI Batch Prompt Loader - Enhanced Version
A custom node for loading and encoding prompts from TXT files with advanced features:
- Recursive scanning, wildcard filtering, skip exists, metadata output, preview display
- External log recording: records which prompt files have been processed, and auto-skips them next run

All user-supplied paths (folder_path / log_folder / output_folder) are confined to the
ComfyUI root directory to prevent path traversal.
"""
import os
import torch
import random as random_module
import json
import fnmatch
import time

_global_mode_state = {}
_log_cleared_this_session = False


def _confine_to_base(base_dir, user_path, label):
    """Resolve a user-supplied path and verify it stays inside base_dir.

    Mitigates path traversal: absolute paths pointing outside the ComfyUI root and
    relative paths escaping via '..' are rejected. Symlinks are resolved via realpath.
    """
    base_real = os.path.normcase(os.path.realpath(base_dir))
    if os.path.isabs(user_path):
        candidate = user_path
    else:
        candidate = os.path.join(base_dir, user_path)
    candidate_real = os.path.normcase(os.path.realpath(candidate))
    if candidate_real != base_real and not candidate_real.startswith(base_real + os.sep):
        raise Exception(
            f"[BatchPromptLoader] '{label}' must resolve to a location inside the ComfyUI directory.\n"
            f"Resolved path: {candidate_real}\nAllowed base: {base_real}"
        )
    return candidate_real


def _sanitize_log_name(rel_path):
    """Convert a relative prompt path into a safe log filename (replacing separators and illegal chars)."""
    name = rel_path.replace('\\', '_').replace('/', '_')
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name


def _load_log(log_dir, source_dir):
    """Read the set of already-processed prompt files matching the current source directory."""
    processed = set()
    if not os.path.isdir(log_dir):
        return processed
    try:
        for fn in os.listdir(log_dir):
            if not fn.endswith('.json'):
                continue
            try:
                with open(os.path.join(log_dir, fn), 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                if entry.get('source_dir') == source_dir and entry.get('prompt_file'):
                    processed.add(entry['prompt_file'])
            except Exception:
                continue
    except Exception as e:
        print(f"[BatchPromptLoader] Warning: failed to read log: {e}")
    return processed


def _write_log(log_dir, source_dir, prompt_file, index, total_count):
    """Record a processed prompt file (one JSON per file, so entries can be deleted selectively)."""
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_name = _sanitize_log_name(prompt_file) + '.json'
        entry = {
            "prompt_file": prompt_file,
            "source_dir": source_dir,
            "index": index,
            "total_count": total_count,
            "processed_at": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(os.path.join(log_dir, log_name), 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BatchPromptLoader] Warning: failed to write log: {e}")


class BatchPromptReaderWithClip:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "clip": ("CLIP",),
                "folder_path": ("STRING", {
                    "default": "input/batch_prompts",
                    "multiline": False,
                    "label": "Folder Path"
                }),
                "current_number": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999999,
                    "step": 1,
                    "control_after_generate": ["fixed", "increment", "decrement", "random"],
                    "label": "Current Index"
                }),
                "recursive": ("BOOLEAN", {
                    "default": True,
                    "label": "Recursive Scan"
                }),
                "reverse_order": ("BOOLEAN", {
                    "default": False,
                    "label": "Reverse Order"
                }),
                "file_pattern": ("STRING", {
                    "default": "*.txt",
                    "multiline": False,
                    "label": "Filename Pattern (wildcard)"
                }),
                "output_folder": ("STRING", {
                    "default": "output/",
                    "multiline": False,
                    "label": "Output Folder (skip check)"
                }),
                "enable_logging": ("BOOLEAN", {
                    "default": False,
                    "label": "Enable Logging (skip processed)"
                }),
                "log_folder": ("STRING", {
                    "default": "user/default/batch_prompt_logs",
                    "multiline": False,
                    "label": "Log Folder (external, clearable)"
                }),
                "clear_log_on_start": ("BOOLEAN", {
                    "default": False,
                    "label": "Clear Log On Session Start"
                }),
            },
            "optional": {
                "skip_exists": ("BOOLEAN", {
                    "default": False,
                    "label": "Skip Existing Images"
                }),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("CONDITIONING", "STRING", "INT", "INT")
    RETURN_NAMES = ("conditioning", "filename", "index", "total_count")
    FUNCTION = "read_and_encode"
    OUTPUT_NODE = True
    CATEGORY = "batch_tools"

    def read_and_encode(self, clip, folder_path, current_number, recursive=True, reverse_order=False,
                        file_pattern="*.txt", output_folder="output/", skip_exists=False,
                        enable_logging=False, log_folder="user/default/batch_prompt_logs", clear_log_on_start=False,
                        extra_pnginfo=None, unique_id=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Confine user-supplied paths to the ComfyUI root (path traversal protection)
        target_dir = _confine_to_base(base_dir, folder_path, "folder_path")

        if not os.path.exists(target_dir):
            raise Exception(
                f"[BatchPromptLoader] Folder does not exist: {target_dir}\n\n"
                f"Please check the 'folder_path' value."
            )

        if not os.path.isdir(target_dir):
            raise Exception(
                f"[BatchPromptLoader] Not a directory: {target_dir}\n\n"
                f"Please make sure this is a valid folder."
            )

        try:
            txt_files = []

            pattern_lower = file_pattern.lower().strip()
            if not pattern_lower or pattern_lower == '*.txt':
                search_pattern = '*.txt'
                required_ext = '.txt'
            else:
                search_pattern = pattern_lower
                if '*' in search_pattern:
                    ext_part = search_pattern.split('*', 1)[-1]
                    required_ext = ext_part if ext_part else '.txt'
                else:
                    required_ext = '.txt'

            if recursive:
                for root, dirs, files in os.walk(target_dir):
                    for f in files:
                        if fnmatch.fnmatch(f.lower(), search_pattern.lower()):
                            if required_ext and not f.lower().endswith(required_ext):
                                continue
                            rel_path = os.path.relpath(os.path.join(root, f), target_dir)
                            txt_files.append(rel_path)
            else:
                all_files = os.listdir(target_dir)
                for f in all_files:
                    if fnmatch.fnmatch(f.lower(), search_pattern.lower()):
                        if required_ext and not f.lower().endswith(required_ext):
                            continue
                        txt_files.append(f)

            txt_files.sort(key=lambda x: x.lower())

            if reverse_order:
                txt_files.reverse()

        except Exception as e:
            raise Exception(f"[BatchPromptLoader] Failed to read folder: {target_dir}\n\nError: {str(e)}")

        if len(txt_files) == 0:
            raise Exception(
                f"[BatchPromptLoader] No matching files in folder: {target_dir}\n\n"
                f"Search pattern: {search_pattern}\n\n"
                f"Please add matching TXT files or adjust the filename pattern."
            )

        # External logging: skip already-processed prompt files
        log_dir = None
        if enable_logging:
            log_dir = _confine_to_base(base_dir, log_folder, "log_folder")

            global _log_cleared_this_session
            if clear_log_on_start and not _log_cleared_this_session:
                try:
                    if os.path.isdir(log_dir):
                        for fn in os.listdir(log_dir):
                            if not fn.endswith('.json'):
                                continue
                            # Only remove log files previously written by this node
                            log_path = os.path.join(log_dir, fn)
                            try:
                                with open(log_path, 'r', encoding='utf-8') as lf:
                                    data = json.load(lf)
                                if isinstance(data, dict) and 'prompt_file' in data:
                                    os.remove(log_path)
                            except Exception:
                                continue
                    _log_cleared_this_session = True
                    print("[BatchPromptLoader] Cleared log folder (first run this session)")
                except Exception as e:
                    print(f"[BatchPromptLoader] Warning: failed to clear log: {e}")

            processed_files = _load_log(log_dir, os.path.normpath(target_dir))
            if processed_files:
                remaining = [f for f in txt_files if f not in processed_files]
                print(f"[BatchPromptLoader] Log filter: skipped {len(txt_files) - len(remaining)} "
                      f"processed file(s), {len(remaining)} remaining")
                if not remaining:
                    print("[BatchPromptLoader] All prompts already processed "
                          "(clear the log folder to start over)")
                    empty_cond = [[torch.zeros(1, 1, 2816), {"pooled_output": torch.zeros(1, 2816)}]]
                    return (empty_cond, "ALL_DONE", 0, 0)
                txt_files = remaining

        counter_file = os.path.join(base_dir, "user", "default", "batch_prompt_counter.json")
        try:
            if os.path.exists(counter_file) and os.path.getsize(counter_file) > 0:
                with open(counter_file, 'r', encoding='utf-8') as f:
                    counter_data = json.load(f)
            else:
                counter_data = {"last_index": 0}
        except Exception:
            counter_data = {"last_index": 0}

        mode = "fixed"
        effective_current_number = current_number

        if isinstance(current_number, (list, tuple)) and len(current_number) >= 2:
            effective_current_number = current_number[0]
            mode = current_number[1]
        elif isinstance(current_number, dict) and 'mode' in current_number:
            mode = current_number['mode']
            effective_current_number = current_number.get('value', 0)

        if mode == "increment":
            old_index = counter_data.get("last_index", effective_current_number)
            new_index = (old_index + 1) % len(txt_files)
            effective_index = new_index
            counter_data["last_index"] = new_index
            print(f"[BatchPromptLoader] Increment: {old_index} -> {new_index} "
                  f"({txt_files[new_index][:30]}...)")

        elif mode == "decrement":
            old_index = counter_data.get("last_index", effective_current_number)
            new_index = (old_index - 1) % len(txt_files)
            effective_index = new_index
            counter_data["last_index"] = new_index
            print(f"[BatchPromptLoader] Decrement: {old_index} -> {new_index} "
                  f"({txt_files[new_index][:30]}...)")

        elif mode == "random":
            effective_index = random_module.randint(0, len(txt_files) - 1)
            counter_data["last_index"] = effective_index
            print(f"[BatchPromptLoader] Random: {effective_index} "
                  f"({txt_files[effective_index][:30]}...)")

        else:
            effective_index = effective_current_number % len(txt_files)
            counter_data["last_index"] = effective_index
            print(f"[BatchPromptLoader] Fixed: {effective_index} "
                  f"({txt_files[effective_index][:30]}...)")

        try:
            os.makedirs(os.path.dirname(counter_file), exist_ok=True)
            with open(counter_file, 'w', encoding='utf-8') as f:
                json.dump(counter_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[BatchPromptLoader] Warning: Failed to save counter: {e}")

        selected_file = txt_files[effective_index]
        file_path = os.path.join(target_dir, selected_file)

        # Skip images that already exist in the output folder
        if skip_exists and output_folder.strip():
            out_base = _confine_to_base(base_dir, output_folder.rstrip('/').rstrip('\\'), "output_folder")
            base_name = os.path.splitext(os.path.basename(selected_file))[0]
            possible_extensions = ['.png', '.jpg', '.jpeg', '.webp']
            file_exists = False

            for ext in possible_extensions:
                check_path = os.path.join(out_base, f"{base_name}{ext}")
                if os.path.exists(check_path):
                    file_exists = True
                    print(f"[BatchPromptLoader] Skipped existing: {base_name}{ext}")
                    break

            if file_exists:
                if enable_logging:
                    _write_log(log_dir, os.path.normpath(target_dir), selected_file,
                               effective_index, len(txt_files))
                empty_cond = [[torch.zeros(1, 1, 2816), {"pooled_output": torch.zeros(1, 2816)}]]
                return (empty_cond, f"SKIPPED:{selected_file}", effective_index, len(txt_files))

        preview_msg = f"[{effective_index + 1}/{len(txt_files)}] {selected_file}"
        print(f"[BatchPromptLoader] {preview_msg}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            positive = ""
            negative = ""
            section = None

            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue

                lower_line = line.lower()
                if lower_line.startswith('positive:'):
                    section = 'positive'
                    positive = line[9:].strip()
                elif lower_line.startswith('negative:'):
                    section = 'negative'
                    negative = line[9:].strip()
                elif section == 'positive':
                    positive += (' ' if positive else '') + line
                elif section == 'negative':
                    negative += (' ' if negative else '') + line

            if not positive and content.strip():
                positive = content.strip()
            if not negative:
                negative = ""

            with torch.no_grad():
                tokens_positive = clip.tokenize(positive)
                tokens_negative = clip.tokenize(negative)

                cond_positive, pooled_positive = clip.encode_from_tokens(tokens_positive, return_pooled=True)
                cond_negative, pooled_negative = clip.encode_from_tokens(tokens_negative, return_pooled=True)

                if cond_positive.dim() == 2:
                    cond_positive = cond_positive.unsqueeze(0)
                if cond_negative.dim() == 2:
                    cond_negative = cond_negative.unsqueeze(0)

                if pooled_positive is None:
                    pooled_positive = torch.zeros(1, 2816)
                elif pooled_positive.dim() == 1:
                    pooled_positive = pooled_positive.unsqueeze(0)

                if pooled_negative is None:
                    pooled_negative = torch.zeros(1, 2816)
                elif pooled_negative.dim() == 1:
                    pooled_negative = pooled_negative.unsqueeze(0)

                conditioning = [[cond_positive, {"pooled_output": pooled_positive}]]

            if enable_logging:
                _write_log(log_dir, os.path.normpath(target_dir), selected_file,
                           effective_index, len(txt_files))

            return (
                conditioning,
                selected_file,           # filename
                effective_index,         # index (0-based)
                len(txt_files)           # total_count
            )

        except Exception as e:
            raise Exception(f"Failed to read file: {selected_file}\nError: {str(e)}")
