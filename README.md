# OpenReal2Sim Reproduction Harness

固定上游来源、默认仅输出计划的执行辅助工具、安全入口补丁、结构验收和中文复现手册。

**这是从筛选候选整理的独立公开展示版本。当前验证限于 70 项合成 CPU 工具测试（46项原工具 + 10项输入汇总 + 14项版本一致性）与静态检查。GPU 推理、完整环境/模型锁、真实输入、标注交互、视频和仿真均未验证，不能称为完整或离线一键复现。**

## 快速检查

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
python3 scripts/verify_distribution.py
bash -n scripts/checkout_upstream.sh
python3 scripts/repro.py run --root /not-used --key demo_image --stage preprocess
```

NumPy用于掩码合成测试；CI使用numpy==1.26.3。本轮本地版本见 [本轮验证报告](reports/distribution-validation.json)。最后一条仅输出计划，不运行上游、不联网、不读取pickle或加载模型。默认不自动安装任何依赖。

## 实现范围

- 固定公开上游 commit `8f69a19e5dfdfe0aad906fdacad0decf862a7adf` 及9个直接子模块gitlink。
- 4文件安全补丁：标注器默认本地监听及显式share开关、重建/运动入口拒绝无效阶段、仿真脚本规范失败退出。
- 明确阶段命令、前置检查、可信pickle门禁、路径约束、资产hash校验、环境版本记录与逐次运行报告。
- 预处理文件、掩码、scene.json引用和GLB结构检查。结构合格不等于几何/物理合格。
- 46项核心合成CPU测试、10项输入汇总测试及14项版本一致性测试，不涉及模型推理、真实个人数据或GPU。

## 新增的工程案例与证据

- [归档工程案例](docs/archive-engineering-case.zh-CN.md)：依赖冲突、阶段追踪、显式降级和验收防误判。
- [逐项证据审查](docs/archive-evidence-review.zh-CN.md)：49个来源文件的取舍及11条主张映射。
- [输入记录复算](docs/input-record-validation.zh-CN.md)：158条记录、20条候选的匿名聚合，不是重建成功率。
- [冷启动验收协议](docs/cold-start-acceptance.zh-CN.md)：当前环境自检、旧产物可读、真冷启动、新输入复跑分别验收。

## 版本完整性

[公私版本与个人原件的分工](docs/version-pair-guide.zh-CN.md)明确每类资料的去向。共享技术文件可通过[同步契约](reports/distribution-contract.json)和本地对比工具检查；原始私人材料不进入公开仓库。四份原始 ZIP 的完整保全不等于模型和端到端复现已经完整。

## 文档

- [执行手册](docs/execution-runbook.zh-CN.md)、[验证状态](docs/verification-status.zh-CN.md)、[证据与缺口](docs/evidence-map.zh-CN.md)
- [项目概览](docs/project-overview.zh-CN.md)、[贡献边界](docs/contribution-audit.zh-CN.md)、[整理过程](docs/project-history.zh-CN.md)
- [单样本检查](docs/workflow-and-artifacts.zh-CN.md)、[批量输入](docs/batch-input-workflow.zh-CN.md)、[排错方法](docs/troubleshooting-cases.zh-CN.md)、[复现清单](docs/reproduction-checklist.zh-CN.md)
- [源码锁](locks/source-lock.json)、[环境契约](locks/environment-contract.json)、[模型来源](locks/model-sources.json)
- [许可与来源](docs/licensing-and-provenance.zh-CN.md)、[第三方声明](THIRD_PARTY_NOTICES.md)、[发布前门禁](PUBLICATION_GATE.zh-CN.md)

## 不包含的内容

完整上游与递归子模块源码、容器镜像、权重、真实输入/输出、原始聊天、个人经历、私人链接、服务器日志、认证文件和原仓库Git历史。新增49文件归档中的相关技术记录已提炼，原件未纳入公开包；单独的4文件摘要归档也不作运行证明。缺失材料不会用占位权重、伪日志或合成结果冒充。

[checkout_upstream.sh](scripts/checkout_upstream.sh)只获取固定公开源码并应用补丁，需网络；不安装依赖或下载模型。[执行手册](docs/execution-runbook.zh-CN.md)中的后续GPU命令尚未在本轮运行。

## 许可与展示

上游安全补丁保留 [MIT全文](LICENSES/OpenReal2Sim-MIT.txt)。新增工具、文档与模板的开放许可尚待作者决定，不自动继承上游MIT。各依赖、模型、输入与输出须分别核验许可。本展示版本不构成对未来用途或权利的保证。

## English summary

A pinned-source reproduction harness with safe defaults, staged execution planning, structural checks and synthetic CPU tests. GPU inference, complete dependency and model locks, annotation interaction, video and simulation remain unverified. This independent showcase contains no original conversations or private runtime data. Its history starts from a new root commit and does not include the original private repository history.
