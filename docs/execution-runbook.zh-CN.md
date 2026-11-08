# 从源码到验收的执行手册

[返回首页](../README.md)

**本手册是带明确停止条件的复现路径，不是已完成 GPU 验收的证明。** 当前可直接运行的是本仓库的 CPU 工具和测试。完整 GPU 环境、模型字节、人工标注、视频和仿真仍未验证，不能承诺“一键完整复现”。

## 0. 先理解三个范围

1. **本仓库工具验收**：命令生成、来源核验、补丁、文件结构检查和合成单元测试。无需 GPU。
2. **单图完整重建**：新输入 → 预处理 → 人工标注 → 全部 8 个重建阶段 → 带轨迹引用的导出。需要实际模型、原生扩展与 GPU。跳过 FoundationPose 的静态结果不属于此项。
3. **视频到仿真**：另验视频深度/相机、传播与跟踪、手/抓取/轨迹、USD 转换、物理回放与示范数据。单张图不能证明这条链路，更不能证明策略训练。

## 1. 本地 CPU 验收

在这个复现仓库根目录运行：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
bash -n scripts/checkout_upstream.sh
python3 scripts/repro.py run --root /not-used --key demo_image --stage preprocess
```

最后一条只有计划输出，没有运行上游、下载模型、读取 pickle 或创建输出。掩码合成测试需要 NumPy；CI 安装 `numpy==1.26.3`。测试通过不代表模型推理通过。

## 2. 获取固定源码

选一个新的 Linux 工作目录，不覆盖已有服务器环境。把以下路径换成自己的绝对路径：

```bash
export NOTES=/absolute/path/openreal2sim-reproduction-notes
export UPSTREAM=/absolute/path/new/OpenReal2Sim
bash "$NOTES/scripts/checkout_upstream.sh" "$UPSTREAM"
```

脚本只克隆源码、检出 `8f69a19e5dfdfe0aad906fdacad0decf862a7adf`、递归初始化固定 gitlink、应用已审查安全补丁并核验。HTTPS 重写只影响该命令，不改全局 Git 配置。它不运行上游安装器、不安装依赖、不下载权重。克隆需要 GitHub 网络和正常仓库访问权限。不要使用 `git submodule update --remote`。

直接子模块锁见 [source-lock.json](../locks/source-lock.json)。源码改动只能是清单中的安全补丁和自己的配置；别把旧环境里未审查的修改混进来。本包不包含历史兼容或降级补丁；本次安全补丁不是其恢复版。

## 3. 先建立环境，再谈可复现

上游参考栈：Linux x86_64、Ubuntu 22.04、Python 3.10、CUDA 11.8、Torch 2.5.1+cu118 / torchvision 0.20.1+cu118。见 [环境契约](../locks/environment-contract.json)。这是固定源码里的参考，不是本次成功构建的锁。其他CUDA/Torch栈不能混装后宣称等价。

目前缺少基础镜像 digest、APT 快照、完整依赖解析/哈希和部分 Git 依赖 pin。本仓库不捏造锁文件。上游 Dockerfile 的 PyTorch3D/chumpy 等可变依赖、原生扩展以及 Gradio/Supervision/Pandas 组合都必须在目标 GPU 环境验证并冻结。

在独立构建环境中审查上游 `docker/real2sim/Dockerfile` 和 requirements 后才能构建。不要直接在已有用户机器上执行安装脚本或改系统库。`scripts/installation/install.py` 仅下载模型，并不会编译扩展；编译在 Dockerfile 中，且脚本硬编码 `/app`。

上游构建入口如下，**本次未执行**，在解决上述可变依赖后才可作为复现环境来源。构建会从外部下载依赖并执行构建代码，不是只读步骤：

```bash
cd "$UPSTREAM"
docker build -f docker/real2sim/Dockerfile -t openreal2sim-local:repro .
docker image inspect --format '{{.Id}}' openreal2sim-local:repro
```

保存输出的实际 image ID。使用第三方预构建镜像时，还需验证来源和真正的 RepoDigest，不把浮动 `:dev` 当锁。普通计算容器只挂必要目录，可使用已经验证的 image ID：

```bash
export IMAGE_ID=sha256:REPLACE_WITH_ACTUAL_VERIFIED_IMAGE_ID
docker run --rm -it --gpus device=0 --network none \
  --mount type=bind,src="$UPSTREAM",dst=/app \
  --mount type=bind,src="$NOTES",dst=/notes \
  --workdir /app "$IMAGE_ID" bash
```

容器内路径改为 `NOTES=/notes`、`UPSTREAM=/app`。上例断网适合模型已齐备的计算阶段，**不能用它映射标注网页**。标注另启容器、只映射 `-p 127.0.0.1:7860:7860`，使用补丁后的上游入口显式 `--server-name 0.0.0.0`，绝不加 `--share`。这里不要求更改宿主安全设置、执行 `xhost +`、挂载Docker socket或整个HOME。

所需运行验证至少包括：
- `python -m pip check` 无依赖冲突；Torch/torchvision CUDA 操作成功。
- Open3D、GL/EGL、pymeshlab 及图像读写正常；无头渲染正常。
- Grounded-SAM-2、Hunyuan 两个 rasterizer、FoundationPose `mycpp`/`mycuda`、nvdiffrast/Kaolin、视频 MegaSAM 和运动 GraspGen 扩展实际可用。
- MoGe 依赖来自正确的 GitHub `utils3d` 实现。PyPI同名包导入成功不证明API兼容。
- Gradio 实际完成点击、Confirm、Save、Reload。只升级 pandas 或进程启动不能作为这项通过证据。

记录当前环境（只含包名/版本，不读取环境变量或认证文件）：

```bash
python "$NOTES/scripts/repro.py" capture-env --output "$NOTES/local-runs/environment-observed.json"
python "$NOTES/scripts/repro.py" preflight --root "$UPSTREAM"
```

`preflight` 失败退出非零。成功也只是前置存在性检查，不是 ABI/模型验收。不要对失败使用 `|| true` 来制造“全部通过”。保存镜像 digest、驱动与编译器版本、完整环境输出后，仍须在全新环境重新跑一个新输入。

## 4. 模型与数据

[模型来源清单](../locks/model-sources.json) 中 `revision`/`sha256` 的 null 明确表示未知，不是可用锁。依据固定上游源码核对模型卡、原作者来源和许可，在获准的机器下载。不要把任何第三方权重、MANO、真实输入或生成资产提交本仓库。

单图涉及 MoGe、GroundingDINO、SAM2、ObjectClear、Hunyuan3D 和 FoundationPose。视频还涉及 DepthAnything、UniDepth、MegaSAM、RAFT/CVD；上游安装器没有显式提供 `megasam_final.pth`，必须按固定子模块的说明补齐。运动另需 WiLoR、MANO、GraspGen；不能用占位文件代替。

把已下载且有权使用的模型保存在上游工作目录内，例如 `.cache/huggingface`、各 `third_party/.../checkpoints`。避免指向目录外的符号链接。对**明确选择的模型目录**生成本地字节清单，不要选择整个 HOME、凭据目录或原始数据目录：

```bash
python "$NOTES/scripts/repro.py" inventory --root "$UPSTREAM" \
  --paths .cache/huggingface/hub third_party/Grounded-SAM-2/checkpoints \
  --output "$NOTES/local-runs/model-bytes.json"
python "$NOTES/scripts/repro.py" verify-assets --root "$UPSTREAM" \
  --manifest "$NOTES/local-runs/model-bytes.json"
```

这里的两个路径只是清单示例，**不是全流程模型齐全的保证**。必须补入所选路径全部必需模型。字节校验只能证明前后相同，不能证明模型正确或有许可。记录下载时的真实 snapshot commit 和模型卡，不能根据文件大小编造 hash。

运行器默认 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，缺模型就失败，不隐式改用未固定的最新权重。这些环境变量不是网络隔离，其他依赖仍可能联网；要禁止网络应在已经配置好的隔离容器中设置网络策略。这里不会修改系统网络设置。

## 5. 单图全流程

先选择一个新 key。复现官方样例可用 `demo_image`，自有输入应改配置中的 key 与 `data/KEY.jpg` 一致。不要同时放同名 `.jpg`、`.png` 和 `.mp4`。首次运行使用全新输出目录。

```bash
cp "$NOTES/configs/single-image.yaml" "$UPSTREAM/config/config.yaml"
export MODEL_LOCK="$NOTES/local-runs/model-bytes.json"
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_image \
  --stage preprocess --execute --trust-local-code --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/01-preprocess.json"
python "$NOTES/scripts/repro.py" check --root "$UPSTREAM" --key demo_image --stage preprocess
```

只在新建专用 checkout 中复制示例配置。已有配置先自行备份，不盲目覆盖。预处理结构检查要求实际帧文件和非空 scene.pkl，但不自动反序列化。还必须人工验证深度、内外参、帧数、尺寸和可视化点云；没有真实标定，不能声称米制准确。

启动标注器：

```bash
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_image \
  --stage annotate --execute --trust-local-code --trust-local-pickle --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/02-annotate.json"
```

默认只监听 127.0.0.1:7860，不生成公网分享链接。远程机器用已有获准的端口转发访问。容器若必须绑定 `0.0.0.0`，只把宿主端口映射到 `127.0.0.1:7860`，不要沿用上游 HOME/Docker socket 大范围挂载。命令行 `--share False` 不是关闭分享的正确用法。

人工交互是必需步骤，不能由“服务启动成功”代替：
1. Output-key 使用 `demo_image`，LOAD 后确认输入正确。
2. 在真实支撑面标 `ground`，先看到临时 mask 再 Confirm。
3. 给目标刚体独立名称（如 `object`），不要误命名为排除项 `hand` 或 `robot`。
4. Save mask_dict，重新 LOAD 确认两种 mask 保留。单图不需要视频 PROPAGATE。
5. 若 Confirm 报错，查看该回调直接 traceback。后台 analytics 的 pandas 报错不证明是唯一原因。

以下操作会加载 Python pickle，只能对自己刚生成、可信的文件执行：

```bash
python "$NOTES/scripts/repro.py" check --root "$UPSTREAM" --key demo_image \
  --stage masks --trust-local-pickle
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_image \
  --stage reconstruct --execute --trust-local-code --trust-local-pickle \
  --assets-lock "$MODEL_LOCK" --report "$NOTES/local-runs/03-reconstruct.json"
python "$NOTES/scripts/repro.py" check --root "$UPSTREAM" --key demo_image --stage reconstruct
```

全重建必须经过全部 8 阶段。运行器不会添加假轨迹、静默跳过 FoundationPose 或用旧产物冒充新结果。重建结构检查验证 JSON 引用、非空文件、GLB结构与完整路径约束，不是几何精度/无碰撞/质量检查。对 GLB 做视觉检查，确认目标、尺度、朝向、支撑关系和碰撞几何；记录异常。

上游导出 JSON 含绝对路径。迁移时必须明确更新引用并在移动后的目录复验；原目录可读不代表可移植。当前工具不会静默改写用户资产。

## 6. 视频、运动、仿真

这部分独立验收，不能从单图通过推断。复制 [video.yaml](../configs/video.yaml) 到专用 checkout，准备 `data/demo_video.mp4`，重新完成 preprocess、人工关键帧标注、PROPAGATE & SAVE、reconstruct。检查所有关键帧、遮挡、轨迹漂移和对象 ID，不能只检查第一帧。

模型和许可闭合后，运行：

```bash
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_video \
  --stage motion --execute --trust-local-code --trust-local-pickle --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/04-motion.json"
```

需人工检查抓取点和轨迹，必要时使用上游 grasp editor；不要默认公开该服务。运动使用自己的可信 scene.pkl，要求同样的 pickle 信任边界。Hunyuan 等许可可能限制用输出改进其他 AI 模型，策略训练之前须单独审查用途。

仿真在**单独**的已验收 IsaacLab 2.0.2 / IsaacSim 4.5.0 环境执行，不能把普通重建 venv 当作 Isaac 环境。需要满足 NVIDIA/Omniverse条款和图形/驱动要求。以该环境的 Python 分别调用：

```bash
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_video \
  --stage usd --execute --trust-local-code --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/05-usd.json"
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_video \
  --stage rollout --execute --trust-local-code --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/06-rollout.json"
python "$NOTES/scripts/repro.py" run --root "$UPSTREAM" --key demo_video \
  --stage randomize --execute --trust-local-code --assets-lock "$MODEL_LOCK" \
  --report "$NOTES/local-runs/07-randomize.json"
```

必须逐条确认上一条真实通过再执行下一条。运行器用当前解释器，不猜测 Isaac 安装位置。USD/rollout进程退出0仍标 `manual_acceptance_required`，需实际场景加载、无NaN、物理稳定、抓取/放置成功率与示范数据内容验证。指定成功阈值、样本数、随机种子后才能报告成功率，不能把生成文件数量当任务成功率。MuJoCo在该版本文档中仍是WIP，不作为已支持的等价全流程。

## 7. 最终验收与复跑

- 保存每阶段非零失败/退出码，不只看最后一条 shell 输出。
- 保存输入 hash、配置 hash、源码/子模块/补丁、包版本、模型 snapshot/hash、镜像 digest、驱动/设备信息、各阶段耗时和峰值显存。
- 记录人工标注闭环、结构验收与质量验收，skipped/failed/not_run 不得写成 passed。
- 在干净容器、干净输出目录、相同固定输入下重新生成结果；仅检查旧文件不算冷启动复现。
- 本地运行报告和日志默认不入 Git。分享前去掉个人路径、服务器标识、令牌和受限数据。

本仓库目前未完成第3节完整环境闭合，也未执行第5/6节GPU链路。详细证据见 [验证状态](verification-status.zh-CN.md)。
