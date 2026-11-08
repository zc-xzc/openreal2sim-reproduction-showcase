# 来源、署名与许可边界

[返回总览](../README.md)

## 本仓库的分发范围

本仓库提供技术说明、空白模板、新增复现辅助工具及最小上游安全补丁。补丁含必要上游上下文，已附完整 MIT 版权许可，见 LICENSES/OpenReal2Sim-MIT.txt 和 THIRD_PARTY_NOTICES.md。不包含完整上游源码、第三方权重、镜像、真实输入或生成资产。

新增工具、文档与模板暂未声明开放许可证。上游 MIT 不自动覆盖本仓库新材料，也不覆盖整套依赖。后续若发布补丁或代码，应先确认来源，再保留对应版权、许可和改动说明。

## 根项目

[OpenReal2Sim LICENSE](https://github.com/PointsCoder/OpenReal2Sim/blob/8f69a19e5dfdfe0aad906fdacad0decf862a7adf/LICENSE) 为 MIT，版权声明为 **Copyright (c) 2025 Jiageng Mao**。复制或分发其代码或实质部分须保留相应版权与许可声明。根项目与各依赖的算法和实现贡献属于各原作者。

本次代码对照 commit 为 `8f69a19e5dfdfe0aad906fdacad0decf862a7adf`；不是历史运行版本的证明。子模块来源见[上游 .gitmodules](https://github.com/PointsCoder/OpenReal2Sim/blob/8f69a19e5dfdfe0aad906fdacad0decf862a7adf/.gitmodules)及[第三方说明](https://github.com/PointsCoder/OpenReal2Sim/blob/8f69a19e5dfdfe0aad906fdacad0decf862a7adf/third_party/README.md)。

## 需要特别关注的组件

以下是对照版本中部分组件的许可提示。整理时重新打开并核对了下列固定版本的许可证全文；这不是完整递归依赖审计，也不是法律意见。实际使用仍应阅读与所用版本和权重对应的全文。

| 组件 | 已查阅的许可 | 实际含义 |
| --- | --- | --- |
| [FoundationPose](https://github.com/PointsCoder/FoundationPose/blob/59df9f028941353e60993eb46be06ae92d0f2534/LICENSE) | NVIDIA 许可 | 限非商业研究或评估用途，不能概括为 MIT |
| [GraspGen](https://github.com/DynamoDuan/GraspGen/blob/9fbacb100f6e6afb31cae0db3c1ae0c0ca5ae6dc/LICENSE) | NVIDIA 许可 | 有非商业研究/评估限制 |
| [ObjectClear](https://github.com/PointsCoder/ObjectClear/blob/5195da65eb52097d6ca7cbced8143322dddd72de/LICENSE) | S-Lab License 1.0 | 有非商业限制，商业用途需另行许可 |
| [WiLoR](https://github.com/DynamoDuan/WiLoR/blob/1936830a63d32629665a03ec038310f3a9b09772/license.txt) | CC BY-NC-ND 4.0 | 含非商业、禁止按该许可分享改编材料等条件 |
| [Hunyuan3D-2](https://github.com/PointsCoder/Hunyuan3D-2/blob/3b9a1515e1b2d97cd7ede51d7fcc5ada8617012a/LICENSE) | Tencent Hunyuan 3D 2.0 Community License | 有地域、使用规模和用途条款；第 5(b) 条限制用作品、输出或结果改进其他 AI 模型，例外为其衍生模型 |
| [SAM 3D Objects](https://github.com/licesma/sam-3d-objects/blob/922aa11f79e05d26034d1ad53b416afbccaeff3f/LICENSE) | SAM License | 适用独立许可及再分发/研究署名等条款，不能按 MIT 一并授权 |

上游还包含其他子模块。上述列表不是“未列出即无约束”。下载 checkpoint、使用数据集或 MANO 等资产时，还需另查相应条款。

尤其是把重建结果用于机器人策略训练或其他 AI 模型改进时，应先针对实际所用 Hunyuan3D 版本与授权审查适用范围，不能因为场景文件已生成就认为后续用途无限制。

## 未来发布补丁的要求

- 记录实际基准 commit、各子模块 revision 和补丁对应文件。
- 保留原作者署名、许可证与需要的 NOTICE。
- 标明新增、修改与继承部分，避免将第三方实现重新冠名。
- 不把第三方私有/受限资产加入 Git 历史。
- 对代码、权重、输入数据、生成资产分别作许可判断。

