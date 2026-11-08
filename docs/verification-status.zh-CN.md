# 验证状态与未完成项

[返回首页](../README.md)

## 当前结论

本次完成的是“固定源码 + 最小安全补丁 + 可执行辅助工具 + CPU单元测试 + 分阶段手册”。**没有完成 OpenReal2Sim GPU 端到端复现。** 环境/模型锁未闭合，标注、重建、视频、运动、仿真和干净环境重跑均不能标为通过。

## 本次实际执行

2026-11-07 UTC，在 Linux x86_64 云环境，Python 3.12.14、NumPy 2.3.5：

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| 46项 unittest | PASS，46/46，无跳过 | 本仓库CPU工具，全部使用本地合成输入或mock |
| patch 对固定上游4文件 git apply --check | PASS | 补丁可干净应用，不证明模型运行 |
| 补丁后3个Python文件 AST | PASS | 语法，不导入模型 |
| 补丁后仿真 shell 与checkout shell bash -n | PASS | shell语法，不执行脚本 |
| dry-run | PASS | 只输出计划，不启动上游、不写结果 |
| 工具GPU前置检查 | FAIL（预期） | 正确识别当前环境不具备运行条件 |

CPU测试覆盖 key/路径与符号链接逃逸、资产 SHA256、空资产、GLB损坏/JSON块、缺轨迹、mask尺寸/类型/命名/ground、pickle显式信任、源码版本/改动、输出覆盖保护、输入歧义、进程失败、验收失败、离线标志和运行摘要。结构测试不评价重建质量；合成trajectory文件只用于引用存在性，不当作有效轨迹。

机器可用环境清单只有当前云电脑。当前没有 nvidia-smi、Docker、Torch 或完整上游checkout/模型；Python也与参考3.10不同。本轮未登录外部GPU服务器，也未运行上游安装器。静态上游文件通过已连接GitHub读取，不运行其安装器。

机器可读结果：[local-validation.json](../reports/local-validation.json)。CI配置验证Python3.10下工具行为；任何CI绿灯也仅代表CPU辅助工具，不代表GPU项目通过。远端CI状态以对应commit的GitHub Actions为准，不能用本地结果冒充远端执行。

## 未运行与阻塞

| 阶段 | 状态 | 仍需什么 |
| --- | --- | --- |
| 依赖/容器从零构建 | NOT RUN | 解析完整依赖，pin镜像digest、Git依赖和OS包；原生扩展构建与ABI验证 |
| 模型下载与hash锁定 | NOT RUN | 许可核验、准确snapshot revision、真实文件SHA256；视频模型供应缺口 |
| 新图MoGe预处理 | NOT RUN | 可用CUDA环境、模型、输入 |
| 分割交互/保存/重载 | NOT RUN | 真实Gradio/SAM2运行与人工标注闭环 |
| 8阶段重建/导出 | NOT RUN | FoundationPose等所有依赖和GPU验收；不能跳过后仍写全通过 |
| 视频/运动/抓取 | NOT RUN | 视频深度/跟踪、MANO许可与资产、WiLoR/GraspGen、轨迹检查 |
| USD/仿真rollout | NOT RUN | 单独Isaac环境、图形驱动、实际物理与任务验收 |
| 新环境冷启动重跑 | NOT RUN | 新容器、新输出、相同锁/输入，重新生成而非检查旧文件 |

不存在本次实测的全流程时长、峰值显存、成功率或质量指标，不用估计值填空。没有已验证的最低GPU配置。

## 公开候选的证据边界

本候选不包含原始聊天、私人来源或历史实验附件。新增49文件归档已按[证据审查](archive-evidence-review.zh-CN.md)提炼，原件仍不公开。本轮验证仅见 [package-validation.json](../reports/package-validation.json)；旧 [local-validation.json](../reports/local-validation.json) 保留为先前的CPU检查记录，两者均不是GPU实验结果。历史环境与未获得原件的完成叙述不用于填充当前通过项。

## 状态语义

- `process_passed`：上游进程退出0，不自动表示交互、质量或物理验收。
- `manual_acceptance_required`：必须完成手册中的人工/模拟器检查。
- `failed_or_interrupted`：进程中断或后续结构验收异常。
- `not_run`、`skipped`、未知版本/null hash：不等于成功，也不得用虚构数据补齐。

完整目标仍未达成；下一步不是再次整理说明，而是在获准GPU环境完成[执行手册](execution-runbook.zh-CN.md)的依赖/模型闭合与真实新输入验收。

## 本次公开候选补充验证

核心46项加新增输入汇总10项，共56项CPU合成测试。本轮另直接复算私有CSV的158/20条记录与候选集合，结果仅限表内一致性。完整结果见 [package-validation.json](../reports/package-validation.json)，不是GPU实验。
