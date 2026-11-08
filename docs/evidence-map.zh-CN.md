# 证据与复现缺口

[返回首页](../README.md)

| 主张 | 可检查的材料 | 可得结论 |
| --- | --- | --- |
| 辅助工具可作CPU检查 | scripts/、70项共享测试、[本轮验证报告](../reports/distribution-validation.json) | 通过仅限合成输入和mock，不是模型验证 |
| 上游来源固定 | source-lock.json、公开commit和子模块gitlink | 固定来源，不是完整依赖或权重锁 |
| 最小安全补丁已交付 | patch、修改后文件hash、MIT许可 | 可检查diff与静态应用，不证明GPU兼容 |
| 环境契约 | environment-contract.json | 参考栈，未完成构建闭合 |
| 模型来源 | model-sources.json | 来源清单，未知revision/hash保持null |
| 单图、视频、运动、仿真 | 分阶段手册与模板 | 待执行，未达到真实单样本或端到端验证 |

本候选不分发原始私有资料，也不以私人历史叙述证明实验成果。新增49文件资料包含终端记录、对话、报告、SOP和输入CSV。只提取去标识方法与表内统计，不用于填写GPU通过状态。详见[新增证据审查](archive-evidence-review.zh-CN.md)。

下一份最小复验记录应包含：固定根/子模块commit、实际补丁、镜像digest和完整依赖、模型snapshot/hash与许可、合法输入hash、配置与种子、逐阶段状态/日志/耗时/显存、标注闭环、结构与几何/仿真验收，以及全新环境重跑结果。

“进程退出0”“结构合格”“几何合格”“物理任务合格”分别报告。任何failed/skipped/not_run不转换为passed。没有完整分母不报成功率。
