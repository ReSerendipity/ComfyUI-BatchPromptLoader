# ComfyUI-BatchPromptLoader

ComfyUI 自定义节点：从文件夹批量加载并编码 TXT 提示词文件，支持**固定/递增/递减/随机**四种模式，以及递归扫描、通配符过滤、跳过已存在等高级功能。

用于"多提示词 + 多张图"的批量生成场景：把提示词拆成多个 TXT 文件放进一个文件夹，节点按索引逐个读取，并通过内置的自动递增功能，每次点 Queue 自动切换下一个提示词。

## 功能特性

- 📁 **递归扫描**：自动扫描文件夹及所有子文件夹中的提示词文件
- 🔍 **通配符过滤**：支持 `*.txt`, `SFW_*.txt` 等文件名模式匹配
- ⏭️ **跳过已存在**：可选跳过已生成的图片，避免重复渲染
- 📋 **外置日志记录**：自动记录已处理的提示词文件，下次运行自动跳过（可外置清除/选择性删除日志）
- 💬 **实时预览**：控制台显示当前文件和总数 `[n/total] filename`
- 🎯 **元数据输出**：输出文件名、索引、总数供后续节点使用
- 🎲 四种索引模式：`fixed`（固定）/ `increment`（递增）/ `decrement`（递减）/ `random`（随机）
- 🔁 内置自动递增：每次 Queue 后自动切换下一个提示词，无需额外种子节点
- 🔃 支持**倒序**排列文件
- 🧠 智能记忆：记录上次读取位置，重启 ComfyUI 后从上次位置继续
- ✂️ 自动拆分正负提示词：支持 `positive:` / `negative:` 段

## 🆕 版本更新 (v2.1)

### 新增功能

- ✅ 外置日志记录（`enable_logging` + `log_folder` + `clear_log_on_start`）
- ✅ 自动跳过已处理过的提示词文件（中断后重跑不重复生成）
- ✅ 日志文件夹可外置清除或选择性删除（每个文件一个 JSON）

### 输入参数

| 英文参数名 | 中文含义 | 类型 | 默认值 | 使用说明 |
|-----------|---------|------|--------|----------|
| `enable_logging` | 启用日志记录 | BOOLEAN | `False` | ✅ 开：记录已处理文件并自动跳过<br>❌ 关：不记录 |
| `log_folder` | 日志文件夹 | STRING | `user/default/batch_prompt_logs` | 日志存放位置（须位于 ComfyUI/user 目录内） |
| `clear_log_on_start` | 会话启动时清空日志 | BOOLEAN | `False` | ✅ 开：每次启动 ComfyUI 后第一次运行时清空日志 |

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
| `folder_path` | STRING | TXT 提示词所在文件夹路径（须位于 ComfyUI/input 目录内；填写相对于 input 的目录名，如 `batch_prompts`） |
| `current_number` | INT | 当前提示词索引（配合"自动更新该值之后"菜单使用） |
| `recursive` | BOOLEAN | 是否递归扫描子文件夹中的 `.txt` 文件（默认开启） |
| `reverse_order` | BOOLEAN | 是否倒序排列文件（默认关闭） |
| `file_pattern` | STRING | 文件名过滤模式，支持通配符（如 `*.txt`, `SFW_*.txt`, `*_v2.txt`，默认 `*.txt`） |
| `output_folder` | STRING | 输出目录路径（用于跳过检查，默认 `output/`） |
| `enable_logging` | BOOLEAN | 是否启用外置日志记录，记录已处理文件并自动跳过（默认关闭） |
| `log_folder` | STRING | 日志文件夹路径（默认 `user/default/batch_prompt_logs`，须位于 ComfyUI/user 目录内） |
| `clear_log_on_start` | BOOLEAN | 会话启动后第一次运行时清空日志（默认关闭） |

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

重启 ComfyUI 后，在画布中右键搜索 **`Batch Prompt Loader`**。

> 💡 **界面语言**：节点名称与参数标签均为英文（ComfyUI 生态的通用做法）。下方提供中英对照表方便快速上手。
>
> ⚠️ **路径约束（v2.1.1 起，v2.1.2 进一步收窄）**：为防范路径遍历，三个路径各自被限制在专属基准目录内，越界一律拒绝（含指向基准外的绝对路径、或借助 `..` 逃逸的路径）：
> - `folder_path` → 限制在 **ComfyUI/input** 内（默认 `batch_prompts`，即 `input/batch_prompts`）
> - `log_folder` → 限制在 **ComfyUI/user** 内（默认 `user/default/batch_prompt_logs`）
> - `output_folder` → 限制在 **ComfyUI/output** 内（默认 `output/`）
>
> 老工作流里以 `input/...`、`user/...`、`output/...` 开头的值仍可正常解析（会自动剥离前缀）。请把提示词文件夹放在如 `ComfyUI/input/batch_prompts` 的位置。

## 📋 参数中英对照表

### 输入参数

| 英文参数名 | 中文含义 | 类型 | 默认值 | 使用说明 |
|-----------|---------|------|--------|----------|
| `clip` | CLIP 模型 | CLIP | (必填) | 从 CLIP Loader 连接过来 |
| `folder_path` | 文件夹路径 | STRING | `batch_prompts` | TXT 提示词所在的文件夹（相对于 ComfyUI/input，即 `input/batch_prompts`） |
| `current_number` | 当前编号 | INT | `0` | 从第几个文件开始（配合右键菜单的递增/递减/随机） |
| `recursive` | 递归扫描子文件夹 | BOOLEAN | `True` | ✅ 开：包含所有子目录<br>❌ 关：只读根目录 |
| `reverse_order` | 倒序排列文件 | BOOLEAN | `False` | ✅ 开：从后往前读（Z→A）<br>❌ 关：正常顺序（A→Z） |
| `file_pattern` | 文件名过滤模式 | STRING | `*.txt` | 通配符，如 `SFW_*.txt`, `*_v2.txt` |
| `output_folder` | 输出目录 | STRING | `output/` | 图片保存位置（用于跳过检查） |

### 可选输入

| 英文参数名 | 中文含义 | 类型 | 默认值 | 使用说明 |
|-----------|---------|------|--------|----------|
| `skip_exists` | 跳过已存在的图片 | BOOLEAN | `False` | ✅ 开：不重复生成同名图片 |

### 输出口

| 英文输出口 | 中文含义 | 类型 | 用途 |
|-----------|---------|------|------|
| `conditioning` | 条件编码 | CONDITIONING | 连到 KSampler |
| `filename` | 文件名 | STRING | 可连到 Save Image 的 `filename_prefix` |
| `index` | 索引号 | INT | 当前是第几个文件（从 0 开始） |
| `total_count` | 总文件数 | INT | 总共扫描到多少个文件 |

### 💡 快速记忆

- **核心参数**：`folder_path`（哪里找）→ `current_number`（从哪开始）→ `conditioning`（输出）
- **常用开关**：`recursive`（要不要扫子目录）、`reverse_order`（要不要倒着读）
- **高级功能**：`file_pattern`（筛选特定文件）、`skip_exists`（跳过已生成的）、`enable_logging`（日志记录，自动跳过已处理）

> ℹ️ **为什么参数是英文？** ComfyUI 生态中，自定义节点的参数名与显示名通常保持英文，这是行业标准做法，方便全球用户交流和资源共享。

> 💡 **新特性提示**：v2.1 新增外置日志记录，自动跳过已处理文件！v2.0 新增通配符过滤、跳过已存在、元数据输出等功能！
> 无第三方依赖，仅需 ComfyUI 自带的 PyTorch 环境。

## 使用方法

### 基础用法

1. 准备提示词文件夹（如 `ComfyUI\input\batch_prompts\SFW`，须位于 ComfyUI/input 目录内），每个提示词一个 `.txt` 文件：

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

### 高级功能 4：外置日志记录（自动跳过已处理）

> 💡 **解决什么问题？** 批量生成 100 个提示词，跑到一半意外中断。重新运行时，如果不加处理会重复生成前面已完成的图片。开启日志记录后，节点会**记住哪些文件已经处理过，下次自动跳过**。

#### 使用步骤

1. 开启 `enable_logging` 开关
2. （可选）设置 `log_folder` 为日志存放位置，默认在 `ComfyUI/user/default/batch_prompt_logs`
3. 正常批量运行。每次节点成功编码一个提示词后，会自动在日志文件夹写入一个 JSON 文件
4. 中断后重新运行，节点读取日志，**自动跳过已处理的文件**，只处理剩余文件
5. 全部处理完后，再次运行会提示"所有提示词已处理完成"（输出口 filename 返回 `ALL_DONE`）

#### 日志文件说明

- 每个已处理的提示词文件对应一个 JSON 日志文件，文件名与提示词文件对应（如 `子目录_提示词A.txt` → `子目录_提示词A.json`）
- 日志内容示例：

  ```json
  {
    "prompt_file": "子目录/提示词A.txt",
    "source_dir": "C:\\ComfyUI\\input\\batch_prompts",
    "index": 0,
    "total_count": 100,
    "processed_at": "2026-08-25 10:30:00"
  }
  ```

#### 如何清除 / 选择性删除日志？

- **全部清除**：直接删除整个 `log_folder` 文件夹（或其中的所有 JSON 文件），下次运行从头开始
- **选择性删除**：想重新生成某个提示词，只需删除对应的那个 JSON 日志文件即可
- **自动清空**：开启 `clear_log_on_start`，则每次启动 ComfyUI 后的第一次运行会自动清空日志（适合换了一批新提示词、想整体重来）

⚠️ **注意**：
- 日志按"节点成功编码该提示词"记录。若图片生成中途失败（如显存不足），请手动删除对应日志条目后重试
- 不同 `folder_path` 的日志会按来源目录自动区分，互不干扰
- `skip_exists`（按图片是否存在判断）与 `enable_logging`（按日志判断）是两套独立机制，可同时开启

### 控制台输出示例

```
[BatchPromptLoader] Fixed: 0 (prompt_001.txt...)
[BatchPromptLoader] ✓ [1/50] prompt_001.txt
[BatchPromptLoader] Increment: 0 → 1 (prompt_002.txt...)
[BatchPromptLoader] ✓ [2/50] prompt_002.txt
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

### v2.1.2 (2026-09-02)

- 🔒 **路径范围收窄**：`folder_path` 限制于 **ComfyUI/input**、`log_folder` 限制于 **ComfyUI/user**、`output_folder` 限制于 **ComfyUI/output**（此前为整个 ComfyUI 根目录）。越界路径（含基准外绝对路径、`..` 逃逸、跨兄弟目录）一律拒绝。
- ♻️ 默认值相应调整：`folder_path` 默认 `batch_prompts`（即 `input/batch_prompts`），老值 `input/...`、`user/...`、`output/...` 会自动剥离前缀继续可用。
- 📝 三个路径控件新增 tooltip 提示其相对基准目录。

### v2.1 (2026-08-25)

- ✨ 新增外置日志记录 (`enable_logging`, `log_folder`, `clear_log_on_start`)
- ✨ 记录已处理的提示词文件，下次运行自动跳过（中断后重跑不重复）
- ✨ 日志文件夹可外置清除 / 选择性删除（每个文件一个 JSON）
- ✨ 全部处理完提示"所有提示词已处理完成"（filename 返回 `ALL_DONE`）

### v2.0 (2026-08-23)

- ✨ 新增通配符过滤 (`file_pattern`)
- ✨ 新增跳过已存在图片功能 (`skip_exists`, `output_folder`)
- ✨ 新增元数据输出 (`filename`, `index`, `total_count`)
- ✨ 增强错误提示（区分路径不存在/文件夹为空）
- ✨ 控制台实时显示当前文件进度

## 许可证

[MIT](LICENSE)
