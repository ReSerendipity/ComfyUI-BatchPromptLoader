"""
ComfyUI Batch Prompt Loader
A custom node for loading and encoding prompts from TXT files with 4 modes: fixed, increment, decrement, random.
"""
import os
import torch
import random as random_module
import json

_global_mode_state = {}

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
                    "control_after_generate": ["fixed", "increment", "decrement", "random"]
                }),
                "recursive": ("BOOLEAN", {
                    "default": True,
                    "label": "递归扫描子文件夹"
                }),
                "reverse_order": ("BOOLEAN", {
                    "default": False,
                    "label": "倒序排列文件"
                }),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            }
        }
    
    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "read_and_encode"
    OUTPUT_NODE = True
    CATEGORY = "batch_tools"
    
    def read_and_encode(self, clip, folder_path, current_number, recursive=True, reverse_order=False, extra_pnginfo=None, unique_id=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if os.path.isabs(folder_path):
            target_dir = folder_path
        else:
            target_dir = os.path.join(base_dir, folder_path)
        
        os.makedirs(target_dir, exist_ok=True)
        
        try:
            # 根据 recursive 参数选择扫描方式
            txt_files = []
            if recursive:
                # 递归扫描所有子文件夹中的 .txt 文件
                for root, dirs, files in os.walk(target_dir):
                    for f in files:
                        if f.endswith('.txt'):
                            rel_path = os.path.relpath(os.path.join(root, f), target_dir)
                            txt_files.append(rel_path)
            else:
                # 只读取根目录下的 .txt 文件
                all_files = os.listdir(target_dir)
                txt_files = [f for f in all_files if f.endswith('.txt')]
            
            # 排序
            txt_files.sort(key=lambda x: x.lower())
            
            # 倒序处理
            if reverse_order:
                txt_files.reverse()
        except Exception as e:
            raise Exception(f"Failed to read folder: {target_dir}\nError: {str(e)}")

            try:
                all_files = os.listdir(target_dir)
                txt_files_non_recursive = [f for f in all_files if f.endswith('.txt')]
                txt_files_non_recursive.sort(key=lambda x: x.lower())
                txt_files = txt_files_non_recursive
            except Exception as e:
                raise Exception(f"Failed to read folder: {target_dir}\nError: {str(e)}")
        
        if reverse_order:
            txt_files.reverse()
        
        if len(txt_files) == 0:
            raise Exception(f"Folder is empty: {target_dir}\n\nPlease add TXT prompt files")
        
        counter_file = os.path.join(base_dir, "user", "default", "batch_prompt_counter.json")
        try:
            if os.path.exists(counter_file) and os.path.getsize(counter_file) > 0:
                with open(counter_file, 'r', encoding='utf-8') as f:
                    counter_data = json.load(f)
            else:
                counter_data = {"last_index": 0}
        except:
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
            print(f"[BatchPromptLoader] Increment: {old_index} → {new_index} ({txt_files[new_index][:30]}...)")
        
        elif mode == "decrement":
            old_index = counter_data.get("last_index", effective_current_number)
            new_index = (old_index - 1) % len(txt_files)
            effective_index = new_index
            counter_data["last_index"] = new_index
            print(f"[BatchPromptLoader] Decrement: {old_index} → {new_index} ({txt_files[new_index][:30]}...)")
        
        elif mode == "random":
            effective_index = random_module.randint(0, len(txt_files) - 1)
            counter_data["last_index"] = effective_index
            print(f"[BatchPromptLoader] Random: {effective_index} ({txt_files[effective_index][:30]}...)")
        
        else:
            effective_index = effective_current_number % len(txt_files)
            counter_data["last_index"] = effective_index
            print(f"[BatchPromptLoader] Fixed: {effective_index} ({txt_files[effective_index][:30]}...)")
        
        try:
            os.makedirs(os.path.dirname(counter_file), exist_ok=True)
            with open(counter_file, 'w', encoding='utf-8') as f:
                json.dump(counter_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[BatchPromptLoader] Warning: Failed to save counter: {e}")
        
        selected_file = txt_files[effective_index]
        file_path = os.path.join(target_dir, selected_file)
        print(f"[BatchPromptLoader] ✓ [{effective_index + 1}/{len(txt_files)}] {selected_file}")
        
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
            
            return (conditioning,)
        
        except Exception as e:
            raise Exception(f"Failed to read file: {selected_file}\nError: {str(e)}")
