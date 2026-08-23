# ComfyUI-BatchPromptLoader

ComfyUI 自定义节点：从文件夹批量加载并编码 TXT 提示词文件，支持**固定/递增/递减/随机**四种模式，以及递归扫描、通配符过滤、跳过已存在等高级功能。

用于"多提示词 + 多张图"的批量生成场景：把提示词拆成多个 TXT 文件放进一个文件夹，节点按索引逐个读取，并通过内置的自动递增功能，每次点 Queue 自动切换下一个提示词。

## 功能特性

- 📁 **递归扫描**：自动扫描文件夹及所有子文件夹中的提示词文件
- 🔍 **通配符过滤**：支持 `*.txt`, `SFW_*.txt` 等文件名模式匹配
- ⏭️ **跳过已存在**：可选跳过已生成的图片，避免重复渲染
- 💬 **实时预览**：控制台显示当前文件和总数 `[n/total] filename`
- 🎯 **元数据输出**：输出文件名、索引、总数供后续节点使用
- 🎲 四种索引模式：`fixed`（固定）/ `increment`（递增）/ `decrement`（递减）/ `random`（随机）
- 🔁 内置自动递增：每次 Queue 后自动切换下一个提示词，无需额外种子节点
- 🔃 支持**倒序**排列文件
- 🧠 智能记忆：记录上次读取位置，重启 ComfyUI 后从上次位置继续
- ✂️ 自动拆分正负提示词：支持 `positive:` / `negative:` 段

## 🆕 版本更新 (v2.0)

### 新增功能

- ✅ 通配符文件名过滤 (`file_pattern`)
- ✅ 跳过已存在的图片 (`skip_exists` + `output_folder`)
- ✅ 元数据输出口 (`filename`, `index`, `total_count`)
- ✅ 增强错误提示（区分路径不存在/文件夹为空/无匹配文件）
- ✅ 控制台实时显示进度 `[n/total] filename`

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
| `recursive` | BOOLEAN | 是否递归扫描子文件夹中的 `.txt` 文件（默认开启） |
| `reverse_order` | BOOLEAN | 是否倒序排列文件（默认关闭） |
| `file_pattern` | STRING | 文件名过滤模式，支持通配符（如 `*.txt`, `SFW_*.txt`, `*_v2.txt`，默认 `*.txt`） |
| `output_folder` | STRING | 输出目录路径（用于跳过检查，默认 `output/`） |

### 可选输入

| 输入 | 类型 | 说明 |
|------|------|------|
| `skip_exists` | BOOLEAN | 开启后，若输出目录已存在同名图片则跳过该文件（默认关闭） |

### 输出

| 输出 | 类型 | 说明 |
|------|------|------|
| `conditioning` | CONDITIONING | 编码后的正向提示词条件 |
| `filename` | STRING | 当前读取的文件名（相对路径） |
| `index` | INT | 当前文件的索引（从 0 开始） |
| `total_count` | INT | 总文件数 |

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ReSerendipity/ComfyUI-BatchPromptLoader.git
```

重启 ComfyUI 后，在画布中右键搜索 `BatchPromptLoader` 或 `批量提示词编码器`。

> 💡 **新特性提示**：v2.0 新增通配符过滤、跳过已存在、元数据输出等功能！
> 无第三方依赖，仅需 ComfyUI 自带的 PyTorch 环境。

## 使用方法

### 基础用法

1. 准备提示词文件夹（如 `C:\prompts\SFW`），每个提示词一个 `.txt` 文件：

   ```
   positive: 一位成熟的大学教授站在讲台上
   negative: 模糊，低质量
   ```

   也可以只写正文（没有 `positive:` 前缀时整段作为正向提示词）。

2. 添加节点并连线：

   ```
   [CLIP Loader] ──clip──> [BatchPromptLoader] ──conditioning──> [KSampler → ...]
   ```

3. 设置 `folder_path` 为提示词文件夹路径，`current_number` 初始为 `0`。

4. 在 `current_number` 上右键，选择 **"递增值"**（或递减/随机）。

5. 每次点击 Queue，节点会自动读取下一个提示词并编码。

### 文件排序说明

- 文件按路径**字典序**（不区分大小写）排列，即先按英文字母 A→Z，再按数字逐位比较（如 `10.txt` 排在 `2.txt` 之前，因为字符 `"1"` 排在 `"2"` 之前）
- 开启 `recursive` 时，子文件夹的文件会**排在其父文件夹文件之后**（按子文件夹名的字典序）
- 开启 `reverse_order` 可对整个文件列表倒序

### 高级功能 1：通配符过滤

通过 `file_pattern` 参数过滤特定名称的文件：

- `*.txt` - 所有 txt 文件（默认）
- `SFW_*.txt` - 以 `SFW_` 开头的文件
- `*_v2.txt` - 以 `_v2.txt` 结尾的文件
- `prompt_*.txt` - 以 `prompt_` 开头的文件

示例：文件夹中有 `prompt_v1_a.txt`, `prompt_v1_b.txt`, `prompt_v2_a.txt`，设置 `file_pattern = "prompt_v2_*.txt"` 只会读取 v2 版本的文件。

### 高级功能 2：跳过已存在的图片

1. 设置 `output_folder` 为你的输出目录（如 `output/`）
2. 开启 `skip_exists` 开关
3. 节点会检查输出目录中是否存在与当前提示词文件同名的图片
4. 如果存在，直接跳过不生成，返回空 conditioning

工作流程：
```
提示词文件：prompt_001.txt → 检查 output/prompt_001.png 是否存在
如果存在 → 跳过
如果不存在 → 正常生成
```

⚠️ **注意**：跳过后会返回空 conditioning，需要在后续节点处理这种情况（或使用 Switch 节点分流）。

### 高级功能 3：使用元数据输出

- `filename` - 可以连接到 Save Image 的 `filename_prefix`，实现按文件名保存
- `index` - 可以用于显示进度或调试
- `total_count` - 显示总共有多少个文件

### 控制台输出示例

```
[BatchPromptLoader] Fixed: 0 (东亚_成熟_单人_大学教授讲堂.txt...)
[BatchPromptLoader] ✓ [1/50] 东亚_成熟_单人_大学教授讲堂.txt
[BatchPromptLoader] Increment: 0 → 1 (东亚_成熟_单人_茶馆遛鸟.txt...)
[BatchPromptLoader] ✓ [2/50] 东亚_成熟_单人_茶馆遛鸟.txt
[BatchPromptLoader] ⏭️ 跳过已存在：prompt_001.png
```

## 提示词文件格式

- 扩展名由 `file_pattern` 决定（默认 `.txt`）
- 可选分段：`positive:` 开头为正向提示词段，`negative:` 开头为负向提示词段
- 分段行之后的内容会续接到对应段
- 无 `positive:` 前缀时，整个文件内容作为正向提示词

## 常见问题

### Q: 输出的 `filename` 怎么用？

A: 可以连接到 Save Image 节点的 `filename_prefix`，实现按提示词文件名保存图片。

### Q: 跳过后图片会空白吗？

A: 会返回空 conditioning，KSampler 可能生成黑图或随机噪声。建议配合 Switch 节点，只在需要时生成。

### Q: 为什么找不到文件？

A: 检查 `folder_path` 是否正确，确认文件夹内是否有符合 `file_pattern` 的 `.txt` 文件。错误信息会显示在控制台和节点红色提示中。

### Q: 如何查看加载了多少个文件？

A: 控制台会输出 `[n/total] filename`，或者将 `total_count` 输出口连接到 Display Int 节点查看。

## Changelog

### v2.0 (2026-08-23)

- ✨ 新增通配符过滤 (`file_pattern`)
- ✨ 新增跳过已存在图片功能 (`skip_exists`, `output_folder`)
- ✨ 新增元数据输出 (`filename`, `index`, `total_count`)
- ✨ 增强错误提示（区分路径不存在/文件夹为空）
- ✨ 控制台实时显示当前文件进度

## 许可证

[MIT](LICENSE)
