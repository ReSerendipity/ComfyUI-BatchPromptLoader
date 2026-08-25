"""
ComfyUI Batch Prompt Loader - Enhanced Version
A custom node for loading and encoding prompts from TXT files with advanced features:
- Recursive scanning, wildcard filtering, skip exists, metadata output, preview display
- External log recording: records which prompt files have been processed, and auto-skips them next run
"""
import os
import torch
import random as random_module
import json
import fnmatch
import time

_global_mode_state = {}
_log_cleared_this_session = False


def _sanitize_log_name(rel_path):
    """将相对路径转为安全的日志文件名（替换路径分隔符和非法字符）"""
    name = rel_path.replace('\\', '_').replace('/', '_')
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name


def _load_log(log_dir, source_dir):
    """读取日志文件夹中匹配当前来源目录的已处理文件集合"""
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
        print(f"[BatchPromptLoader] Warning: 读取日志失败: {e}")
    return processed


def _write_log(log_dir, source_dir, prompt_file, index, total_count):
    """将已处理的提示词文件写入日志（每个文件一个 JSON，便于选择性删除）"""
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
        print(f"[BatchPromptLoader] Warning: 写入日志失败: {e}")

class BatchPromptReaderWithClip:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "clip": ("CLIP",),
                "folder_path": ("STRING", {
                    "default": "input/batch_prompts",
                    "multiline": False,
                    "label": "文件夹路径"
                }),
                "current_number": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999999,
                    "step": 1,
                    "control_after_generate": ["fixed", "increment", "decrement", "random"],
                    "label": "当前编号"
                }),
                "recursive": ("BOOLEAN", {
                    "default": True,
                    "label": "递归扫描子文件夹"
                }),
                "reverse_order": ("BOOLEAN", {
                    "default": False,
                    "label": "倒序排列文件"
                }),
                "file_pattern": ("STRING", {
                    "default": "*.txt",
                    "multiline": False,
                    "label": "文件名过滤 (通配符)"
                }),
                "output_folder": ("STRING", {
                    "default": "output/",
                    "multiline": False,
                    "label": "输出目录 (用于跳过检查)"
                }),
                "enable_logging": ("BOOLEAN", {
                    "default": False,
                    "label": "启用日志记录 (跳过已处理)"
                }),
                "log_folder": ("STRING", {
                    "default": "user/default/batch_prompt_logs",
                    "multiline": False,
                    "label": "日志文件夹 (外置可清除)"
                }),
                "clear_log_on_start": ("BOOLEAN", {
                    "default": False,
                    "label": "会话启动时清空日志"
                }),
            },
            "optional": {
                "skip_exists": ("BOOLEAN", {
                    "default": False,
                    "label": "跳过已存在的图片"
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
        
        if os.path.isabs(folder_path):
            target_dir = folder_path
        else:
            target_dir = os.path.join(base_dir, folder_path)
        
        # 优化 3: 增强错误提示 - 先检查路径是否存在
        if not os.path.exists(target_dir):
            raise Exception(f"[错误] 路径不存在：{target_dir}\n\n请检查 folder_path 是否正确。")
        
        if not os.path.isdir(target_dir):
            raise Exception(f"[错误] 路径不是文件夹：{target_dir}\n\n请确保这是一个有效的目录。")
        
        try:
            txt_files = []
            
            # 解析文件模式
            pattern_lower = file_pattern.lower().strip()
            if not pattern_lower or pattern_lower == '*.txt':
                search_pattern = '*.txt'
                required_ext = '.txt'
            else:
                search_pattern = pattern_lower
                # 提取扩展名（如 *.prompt.txt -> .prompt.txt）
                if '*' in search_pattern:
                    ext_part = search_pattern.split('*', 1)[-1]
                    required_ext = ext_part if ext_part else '.txt'
                else:
                    required_ext = '.txt'
            
            if recursive:
                # 递归扫描所有子文件夹
                for root, dirs, files in os.walk(target_dir):
                    for f in files:
                        # 优化 2: 通配符过滤
                        if fnmatch.fnmatch(f.lower(), search_pattern.lower()):
                            if required_ext and not f.lower().endswith(required_ext):
                                continue
                            rel_path = os.path.relpath(os.path.join(root, f), target_dir)
                            txt_files.append(rel_path)
            else:
                # 只读取根目录
                all_files = os.listdir(target_dir)
                for f in all_files:
                    if fnmatch.fnmatch(f.lower(), search_pattern.lower()):
                        if required_ext and not f.lower().endswith(required_ext):
                            continue
                        txt_files.append(f)
            
            # 排序
            txt_files.sort(key=lambda x: x.lower())
            
            # 倒序处理
            if reverse_order:
                txt_files.reverse()
                
        except Exception as e:
            raise Exception(f"[错误] 读取文件夹失败：{target_dir}\n\n错误信息：{str(e)}")
        
        # 优化 3: 空文件夹检测
        if len(txt_files) == 0:
            raise Exception(f"[错误] 文件夹中没有匹配的文件：{target_dir}\n\n搜索模式：{search_pattern}\n\n请添加对应的 TXT 文件或调整文件名过滤规则。")
        
        # 优化 6: 外置日志记录 - 跳过已处理过的提示词文件
        log_dir = None
        if enable_logging:
            if os.path.isabs(log_folder):
                log_dir = log_folder
            else:
                log_dir = os.path.join(base_dir, log_folder)
            
            # 会话启动后第一次运行时清空日志（配合 clear_log_on_start）
            global _log_cleared_this_session
            if clear_log_on_start and not _log_cleared_this_session:
                try:
                    if os.path.isdir(log_dir):
                        for fn in os.listdir(log_dir):
                            if fn.endswith('.json'):
                                os.remove(os.path.join(log_dir, fn))
                    _log_cleared_this_session = True
                    print("[BatchPromptLoader] 🧹 已清空日志文件夹（会话启动后第一次运行）")
                except Exception as e:
                    print(f"[BatchPromptLoader] Warning: 清空日志失败: {e}")
            
            processed_files = _load_log(log_dir, os.path.normpath(target_dir))
            if processed_files:
                remaining = [f for f in txt_files if f not in processed_files]
                print(f"[BatchPromptLoader] 📋 日志过滤：已跳过 {len(txt_files) - len(remaining)} 个已处理文件，剩余 {len(remaining)} 个待处理")
                if not remaining:
                    print("[BatchPromptLoader] ✅ 所有提示词已处理完成（清除日志文件夹可重新开始）")
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
        
        # 优化 4: 跳过已存在的图片
        if skip_exists and output_folder.strip():
            out_base = os.path.join(base_dir, output_folder.rstrip('/').rstrip('\\'))
            base_name = os.path.splitext(os.path.basename(selected_file))[0]
            possible_extensions = ['.png', '.jpg', '.jpeg', '.webp']
            file_exists = False
            
            for ext in possible_extensions:
                check_path = os.path.join(out_base, f"{base_name}{ext}")
                if os.path.exists(check_path):
                    file_exists = True
                    print(f"[BatchPromptLoader] ⏭️ 跳过已存在：{base_name}{ext}")
                    break
            
            if file_exists:
                print(f"[BatchPromptLoader] 已跳过：{selected_file}")
                if enable_logging:
                    _write_log(log_dir, os.path.normpath(target_dir), selected_file, effective_index, len(txt_files))
                empty_cond = [[torch.zeros(1, 1, 2816), {"pooled_output": torch.zeros(1, 2816)}]]
                return (empty_cond, f"SKIPPED:{selected_file}", effective_index, len(txt_files))
        
        # 优化 1: 显示预览信息
        preview_msg = f"✓ [{effective_index + 1}/{len(txt_files)}] {selected_file}"
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
            
            # 优化 6: 记录到外置日志（成功编码后标记为已处理）
            if enable_logging:
                _write_log(log_dir, os.path.normpath(target_dir), selected_file, effective_index, len(txt_files))
            
            # 优化 5: 输出元数据
            return (
                conditioning,
                selected_file,           # filename
                effective_index,         # index (从 0 开始)
                len(txt_files)           # total_count
            )
        
        except Exception as e:
            raise Exception(f"Failed to read file: {selected_file}\nError: {str(e)}")
