# ComfyUI-BatchPromptLoader

ComfyUI 自定义节点：从文件夹批量加载并编码 TXT 提示词文件，支持**固定 / 递增 / 递减 / 随机**四种模式。

用于"多提示词 + 多张图"的批量生成场景：把提示词拆成多个 TXT 文件放进一个文件夹，节点按索引逐个读取，并通过内置的自动递增功能，每次点 Queue 自动切换下一个提示词。

## 功能特性

- 📁 从指定文件夹加载所有 `.txt` 提示词文件（自动按文件名排序）
- 🎲 四种索引模式：`fixed`（固定）/ `increment`（递增）/ `decrement`（递减）/ `random`（随机）
- 🔁 内置自动递增：每次 Queue 后自动切换下一个提示词，无需额外种子节点
- 🧠 智能记忆：记录上次读取位置，重启 ComfyUI 后从上次位置继续
- ✂️ 自动拆分正负提示词：支持 `positive:` / `negative:` 段

## 节点

| 节点名 | 显示名 | 说明 |
|--------|--------|------|
| `BatchPromptReaderWithClip` | BatchPromptLoader | 加载 TXT 提示词并编码为 conditioning |

### 输入

| 输入 | 类型 | 说明 |
|------|------|------|
| `clip` | CLIP | 来自 CLIP Loader |
| `folder_path` | STRING | TXT 提示词所在文件夹路径（绝对路径或相对于 ComfyUI 根目录） |
| `current_number` | INT | 当前提示词索引（配合"自动更新该值之后"菜单使用） |

### 输出

| 输出 | 类型 | 说明 |
|------|------|------|
| `conditioning` | CONDITIONING | 编码后的正向提示词条件 |

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ReSerendipity/ComfyUI-BatchPromptLoader.git
```

重启 ComfyUI 后，在画布中右键搜索 `BatchPromptLoader` 或 `批量提示词编码器`。

> 无第三方依赖，仅需 ComfyUI 自带的 PyTorch 环境。

## 使用方法

1. 准备提示词文件夹（如 `C:\prompts\SFW`），每个提示词一个 `.txt` 文件：

   ```
   positive: 一位成熟的大学教授站在讲台上
   negative: 模糊, 低质量
   ```

   也可以只写正文（没有 `positive:` 前缀时整段作为正向提示词）。

2. 添加节点并连线：

   ```
   [CLIP Loader] ──clip──> [BatchPromptLoader] ──conditioning──> [KSampler → ...]
   ```

3. 设置 `folder_path` 为提示词文件夹路径，`current_number` 初始为 `0`。

4. 在 `current_number` 上右键，选择 **"递增值"**（或递减/随机）。

5. 每次点击 Queue，节点会自动读取下一个提示词并编码。

### 控制台输出示例

```
[BatchPromptLoader] Fixed: 0 (东亚_成熟_单人_大学教授讲堂.txt...)
[BatchPromptLoader] ✓ [1/50] 东亚_成熟_单人_大学教授讲堂.txt
[BatchPromptLoader] Increment: 0 → 1 (东亚_成熟_单人_茶馆遛鸟.txt...)
[BatchPromptLoader] ✓ [2/50] 东亚_成熟_单人_茶馆遛鸟.txt
```

## 提示词文件格式

- 扩展名必须为 `.txt`（大小写不敏感）
- 可选分段：`positive:` 开头为正向提示词段，`negative:` 开头为负向提示词段
- 分段行之后的内容会续接到对应段
- 无 `positive:` 前缀时，整个文件内容作为正向提示词

## 许可证

[MIT](LICENSE)
