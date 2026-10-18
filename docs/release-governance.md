# 发布 / 回滚 规范（ComfyUI-BatchPromptLoader 本仓）

> **来源与权威**：公共条款见 `ReSerendipity/.github` 的 `REPOSITORY_GUIDELINES.md` §10（发布 / 分发统一规范）。
> 本文件按 `RELEASE_GOVERNANCE_TEMPLATE.md` 结构编写，只填**本仓特有**内容，**不重写或抵触 §10 的公共条款**。
> 本文所有事实均以 **2026-10-18 对 `ReSerendipity/ComfyUI-BatchPromptLoader`（默认分支 `master`）的 `gh api` 实测**为依据。

---

## 0. 远端优先（根原则，不可改写）

发布链的构建、打包、扫描、上传、推送**全部在 GitHub Actions 远端完成**；本地只做三件事：改版本位、落 CHANGELOG、`git tag` + `git push`。本地不执行打包 / 镜像构建 / 发布上传。

本仓当前发布链 `release.yml`（触发 `push: tags: v*`）**完全在远端运行**，本地仅 `git tag` + `git push`。本仓不产出二进制，故无「本地打包 / 镜像构建」动作，本原则天然满足。

## 1. 版本号规范

- 遵循 **SemVer** `MAJOR.MINOR.PATCH`（`release.yml` 的 `validate` 作业以正则 `^v[0-9]+\.[0-9]+\.[0-9]+$` 强约束，不合规即 `exit 1` 判红）。预发布用 `-alpha.N` / `-beta.N` / `-rc.N`——**注意**：当前正则**不接受**预发布后缀，预发布 tag 会被拒，属已知现状。
- **唯一权威版本位**：**无版本位**。本仓实测无 `pyproject.toml`（404）、无 `package.json`、`__init__.py` 中仅有 `NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS`、`batch_prompt_loader.py` 中无 `__version__` 或任何版本常量赋值。当前版本仅以**约定口径**存在于文档层：`README.md` 的 `## Changelog` 段最新条目为 **v2.1.2（2026-09-02）**，且 README「发布」段示例用 `git tag v2.1.3`。
- 必须同步的其它版本位：**无**（本仓无任何仓内跟踪的版本声明）。
- 版本位漂移由：**无校验入口**——本仓无 `tests/` 套件（PR #1 记录 "repository has no tracked test suite"），故无 `test_all_version_sites_agree` 类比对；无法做到「漂一处即判红」，属欠账。
- 自动化方式：**手动 tag（人工）**。本仓 workflows 中无 `release-please` 配置，`release.yml` 明确 `--verify-tag`（不替人创建 tag）。

## 2. CHANGELOG 管理

- 目标遵循 **Keep a Changelog**（`Added / Changed / Fixed / Deprecated / Removed / Security`）。
- 每次合并 `main`/`master` 应在 `[Unreleased]` 追加；type 映射 `feat→Added`、`fix→Fixed`、`refactor→Changed`；发版时 `[Unreleased]` → `[VERSION] - YYYY-MM-DD`。
- **现状（实测）**：**`CHANGELOG.md` 已建立**（根级，Keep a Changelog 结构，随补建 PR 引入）。本仓已有遵循 Keep a Changelog 的独立变更日志；`README.md` 的 `## Changelog` 段仍保留历史版本口径（v2.1.2 / v2.1 / v2.0）。
- 收敛方向：已完成——根 `CHANGELOG.md` 已按 Keep a Changelog 建立；后续变更随合并追加至 `[Unreleased]`，发版时转入版本段。

## 3. 发布流程（远端）

本仓实测发布链：**`.github/workflows/release.yml`（文件名实测确认）**，由 PR #1「ci: add source release workflow」于 2026-09-30 合入 `master`（merge commit `cf1a994`）。

1. 确认版本相关文档（`README.md` 的 `## Changelog` 段）已更新到待发版本。
2. 同步版本位——本仓无版本位（见 §1），仅需文档口径一致。
3. 本地打 tag 并推送：`git tag v<X.Y.Z>` → `git push origin v<X.Y.Z>`。
4. **远端** `release.yml` 被 `push: tags: v*` 触发：
   - `validate` 作业：校验 tag 名匹配 `^v[0-9]+\.[0-9]+\.[0-9]+$`，否则判红中止；
   - `publish` 作业（`contents: write`）：`gh release create "$TAG" --verify-tag --generate-notes --title "$TAG"`。
5. **产物形态**：**源码型 GitHub Release**——仅挂 GitHub 自动生成的 release notes，**不附加任何构建资产**（无 wheel/sdist、无镜像、无安装包）。**无 draft 阶段**：`gh release create` 直接创建为 **published** Release（与本模板「先 draft 后 published」口径不同，属本仓现状，未改动流程）。
6. 盯到终态：`gh run list --workflow=release.yml` 确认 `validate` 与 `publish` 两步绿；红了当场修或 `git revert` 止损。

> 默认 workflow 权限为只读（`permissions: contents: read`），仅 `publish` 作业显式提权为 `contents: write`——符合最小权限。

## 4. 分发产物与完整性

| 产物 | 构建位置 | 标签 / 命名 | 完整性手段 |
|---|---|---|---|
| 源码 Release（GitHub Release，无附加资产） | **远端**（`release.yml`） | tag `v<MAJOR.MINOR.PATCH>`；`--verify-tag` 禁凭空建 tag | 无（本仓不产二进制资产，故不产 `SHA256SUMS.txt`；无 GPG） |

- 本仓**不产出容器镜像**：无 `docker-publish.yml`、无 `ghcr.io` 推送、无 Trivy 扫描、无 `provenance` / `sbom`、**无 floating `latest`**（`.github/workflows/` 实测仅 `release.yml` 一个文件，上述项均不存在）。
- 本仓**非桌面分发仓**：无 Tauri/NSIS/APK，无 `*.sig` / `*.sig.ed25519`，无签名密钥需求。
- **不使用 GPG 分离签名**（2026-10-18 裁决，且本仓从未存在 `gpg-signed-release.yml`——实测 workflows 仅 `release.yml`）。
- 因无二进制资产，`SHA256SUMS.txt` 与 Tauri ed25519 签名在本仓**均不适用**；§10.1「产物必须可校验」对本仓的落点仅剩「tag 驱动 + 可复核的 Release 记录」。

## 5. 回滚

- **判定（满足任一即触发）**：**待定（负责人 + 触发条件）**——本仓无在线服务、无监控、无 CI 常驻门禁，无法据实测确定数值阈值；须由仓库所有者裁定后回填。
- **执行**：`git revert <bad-commit>`（保历史、可再 forward）。源码型 Release 无不可变产物，回滚即回退代码并视情况补发新 tag。
- **破坏性动作**：重指向 / 删除 tag、移动任何远端 ref → **须仓库所有者单独授权**。注意：`release.yml` 由 `push: tags: v*` 触发，**移动已发布 tag 会当场重跑发布链**，属高风险动作。
- **回滚后验证**：无自动化测试套件；以 PR #1 使用的口径 `python -m compileall -q` 验证语法可导入为准（本仓无 `tests/`、无 smoke 命令）。

## 6. SLA / 错误预算

- 本仓为源码分发的 ComfyUI 自定义节点，**无在线服务端点**，故不设运行可用性 SLA。
- 与发布相关的可用性口径（「tag → Release 链路成功率」）目标与错误预算：**待定（负责人 + 触发条件）**。超出预算后冻结非紧急发布的触发条件同样 **待定（负责人 + 触发条件）**。

## 7. 发布前检查清单

- [ ] 版本位全部同步——本仓无版本位（§1），改为确认 `README.md` 的 `## Changelog` 段与待发 tag 版本号一致
- [ ] `README.md` `## Changelog` 段已补记本版条目与日期（独立 `CHANGELOG.md` 已建立，见 §2）
- [ ] `python -m compileall -q` 通过（本仓无测试套件，以此作语法烟测）
- [ ] lint / format：**不适用**（本仓未配置 lint / formatter 门禁）
- [ ] 镜像类仓项（Trivy 阻断 / `.trivyignore.yaml` / `provenance: true` + `sbom: true`）：**不适用**（本仓不产容器镜像）
- [ ] **本地未产出任何发布交付物**（本仓发布链全部远端，且不产二进制）

---

## 差异点采集清单（已按本仓实测填值）

| 占位符 | 采集来源 | 本仓取值 |
|---|---|---|
| 版本位文件与字段 | `pyproject.toml` / `config.yaml` / `package.json` / `__init__.py` | **无版本位**（无 `pyproject.toml`、无 `package.json`、`__init__.py` 无版本常量，`batch_prompt_loader.py` 无 `__version__`） |
| 其它需同步版本位 | 仓内版本串扫描 | **无** |
| 版本一致性校验入口 | `<repo>/tests/**` | **无**（本仓无 `tests/` 套件） |
| 自动化方式 | `.github/workflows/`（是否有 release-please） | **手动 tag（人工）**；无 release-please |
| 发布 workflow 文件名 | `.github/workflows/` | **`release.yml`**（唯一 workflow） |
| 产物形态与标签规则 | 构建 workflow | **源码型 GitHub Release**，无附加资产；tag `vMAJOR.MINOR.PATCH`（正则强制，`--verify-tag`） |
| 完整性手段 | Release 资产清单 | **无**（无二进制资产，故无 `SHA256SUMS.txt`；无 GPG；非桌面仓无 Tauri 签名） |
| 回滚判定阈值 | 运行手册 / 监控 | **待定（负责人 + 触发条件）** |
| 回滚后验证命令 | `tests/smoke` 等 | **无测试套件**；以 `python -m compileall -q` 作烟测 |
| 技术栈 | `package.json` / `pyproject.toml` / 静态站 | **Python**（ComfyUI 自定义节点）；`requirements.txt` 无外部依赖 |
| 部署目标 | `deploy/` / Pages workflow | **无**（源码即交付，clone 到 `ComfyUI/custom_nodes` 即用；无 Pages、无服务部署） |

## 现状事实速记（2026-10-18 实测）

- 默认分支：**`master`**（非 `main`）。
- workflows：**仅 `.github/workflows/release.yml`**；无 Trivy、无 `value=latest`、无 `provenance`、无 `sbom`、无 `gpg-signed-release.yml`。
- `CHANGELOG.md`：**已建立**（根级，Keep a Changelog 结构）。
- tag / Release：`gh api .../tags` 与 `.../releases` 均返回**空**（尚无已发布版本）。
- `.gitignore`：以 `*.md` 忽略全部 Markdown，仅 `!README.md` 白名单放行；**本次已补 `!docs/release-governance.md`** 使本文件可入库。
- 本仓无 `docs/` 目录（本次新建）、无 `CODEOWNERS`、无 `.trivyignore.yaml`。

## 禁止事项

- 不得重写 §10 的公共条款（远端优先、tag 驱动、不可变标签、扫描阻断、无 GPG）。
- 本仓不产镜像，但若未来引入容器分发，**不得引入 `latest` 作发布基线**、**不得新建 GPG 签名流程**。
- 不得留空占位符，不得编造阈值。
