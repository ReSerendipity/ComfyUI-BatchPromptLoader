# Changelog

本项目的所有值得注意的变更都将记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本（Semantic Versioning）](https://semver.org/lang/zh-CN/)。

## [Unreleased]

> **说明**：本仓尚无 git tag 或 GitHub Release，尚未建立版本化发布；以下条目按提交历史回填
> （`feat`→Added、`fix`→Fixed、`refactor`→Changed），待首次发版时转入对应版本段。

### Added

- 初始版本：从 TXT 文件批量加载并编码提示词，支持 fixed / increment / decrement / random 模式
- 递归文件夹扫描（同时移除未使用的 web 上传代码）
- 文件扫描新增 `recursive` 与 `reverse_order` 开关
- wildcard 过滤器、skip-exists、元数据输出、增强错误提示与预览
- 中文界面：汉化节点参数名称与显示名称、完整汉化所有参数标签
- 外置日志记录：自动跳过已处理的提示词文件

### Fixed

- 移除损坏的中文标签，修复 UNKNOWN parameter 问题
- 安全修复：将用户可控路径限制在 ComfyUI 根目录内，并将节点界面本地化为英文
- 安全收窄：`folder_path` 限制到 `input/`，`log_folder` 限制到 `user/`，`output_folder` 限制到 `output/`
