# 上游代码审计与运行边界

本次审计只通过 GitHub 读取源码、生成最小补丁并进行静态检查，没有执行模型、下载权重或完成 GPU 重建。审计基准为 [PointsCoder/OpenReal2Sim 8f69a19](https://github.com/PointsCoder/OpenReal2Sim/tree/8f69a19e5dfdfe0aad906fdacad0decf862a7adf)，不是历史实验实际运行版本的证明。

## 已确认入口与契约

以下命令必须在上游仓库根目录、已验收的环境内运行。启动标注器前必须应用本仓库补丁。

- 预处理：python openreal2sim/preprocess/preprocess_manager.py --config config/config.yaml --key_name SAMPLE
- 标注：python openreal2sim/reconstruction/tools/segmentation_annotator.py --key SAMPLE --port 7860
- 重建：python openreal2sim/reconstruction/recon_agent.py --key SAMPLE
- 运动：python openreal2sim/motion/motion_manager.py --key SAMPLE
- 仿真脚本实际位置：openreal2sim/simulation/isaaclab/demo/sim_agent.sh

重建和运动的 --stage 表示“从该阶段执行到最后”，不是只执行一个阶段。两者固定读取 config/config.yaml。配置应包含 keys、global、local，即使没有局部覆盖也保留 local: {}。不得将错误阶段名退回到全流程。

输入采用 data/SAMPLE.jpg 或 .png；视频为 .mp4，可加 SAMPLE_depth.png 和真实标定参数。建议每次只保留一种输入模式并使用新工作目录，避免旧产物混入。

预处理依次执行图像提取、深度预测、深度标定。单图使用 MoGe-2，视频使用 DepthAnything、UniDepth、MegaSAM、RAFT 和 CVD。无真实深度时标定会跳过，因此执行成功不等于尺度或几何精度得到实测验证。

scene.pkl 的主要字段：
- images：uint8 [N,H,W,3]
- depths：float32 [N,H,W]
- intrinsics：[3,3] 像素坐标内参
- extrinsics：[N,4,4] camera-to-world
- n_frames、height、width
- mask：按帧号、物体 ID 索引的字典；每物体含 name、bbox、H×W 布尔 mask。

标注实际保存在 scene.pkl 的 mask 字段，不是注释中提到的独立 mask_dict.pkl。需要 ground 支撑面和至少一个有效物体；必须检查保存、重新加载。只读取自己生成且可信的 pickle，不自动反序列化下载的陌生样例。

## 重建与降级边界

重建阶段顺序：
1. mask_propagation
2. background_pixel_inpainting
3. background_point_inpainting
4. background_mesh_generation
5. object_mesh_generation
6. scenario_construction
7. scenario_fdpose_optimization
8. scenario_collision_optimization

当前 collision 源码强制读取物体 fdpose 网格，save_assets 强制复制 fdpose_trajs、simple_trajs、hybrid_trajs。因此简单跳过 FoundationPose 不会形成受支持的完整导出流程。本安全补丁不添加假设性降级算法，不制造零轨迹或将 skipped 标成 completed。

上游导出 simulation/scene.json、背景图、背景/物体/整体 GLB 和轨迹。JSON 路径使用绝对路径；仅有文件不证明可移植，需要相对引用规范化、引用校验及移动目录后的验证。导出并不证明物理稳定性或机器人训练成功。

## 安全补丁

patches/0001-safe-cli.patch 只修复明确入口问题：
- 标注器 --share 改成显式 store_true，默认关闭。原来的 type=bool 导致 --share False 仍为 True。
- 添加 --server-name，默认 127.0.0.1。容器内部如需发布端口，显式绑定 0.0.0.0，同时宿主端口只绑定回环地址。
- 重建/运动 CLI 限定阶段 choices，内部非法阶段抛出异常。
- 仿真脚本启用 set -euo pipefail；GPU 默认 0，可通过 OPENREAL2SIM_GPU_ID 指定。

标注器在解析参数前加载模型，因此 --help 不是离线 CPU 冒烟测试。默认端口 7860 与上游文档中的 8000:5000 不一致，必须使用匹配映射。

## 依赖与未闭合事项

上游 Docker 基于 CUDA 11.8、Ubuntu 22.04、Torch 2.5.1+cu118。多项原生 CUDA 扩展必须编译。CUDA 架构列表不是最低显存承诺；本次没有核实全流程最低显存或 GPU 冷启动成功。

install.py 只下载权重，并不执行文档声称的扩展编译。它硬编码 /app、包含非单图任务需要的模型，并留下 MANO 手工下载 TODO。单图运行时还会隐式下载 MoGe、GroundingDINO、ObjectClear、Hunyuan3D。HF 调用未固定 revision，也无 SHA256，不能把安装完成当作完整模型锁定。

主要运行时模型：
- Ruicheng/moge-2-vitl-normal
- IDEA-Research/grounding-dino-base
- jixin0101/ObjectClear
- tencent/Hunyuan3D-2（turbo shape 和 paint）
- sam2.1_hiera_large.pt

视频另需要 mega-sam/checkpoints/megasam_final.pth，当前 installer 未显式下载，需核对嵌套依赖。requirements 中多项包、PyTorch3D/chumpy Git 安装未固定版本；基础镜像是 tag 而非 digest。有效模型 revision/hash、完整依赖锁、真实新输入、GPU、标注验收、导出及模拟器验收仍需补齐。

上游 compose 挂载整个 HOME 和 Docker socket，不应原样用于普通单图运行；受限方案只挂载必要仓库、数据和缓存。SAM3D 的容器编排不是默认授权打开 Docker socket 的理由。

## 静态检查与许可证

本补丁已针对连接器读取的固定版本原文件通过 git apply --check；三个修改后的 Python 文件通过 AST 解析；仿真 shell 通过 bash -n。没有导入上游模型模块，也没有声称运行成功。

根项目 MIT 及作者版权见 LICENSES/OpenReal2Sim-MIT.txt。FoundationPose、ObjectClear、Hunyuan3D 等有独立限制，模型和输入数据许可也需分别核验。Hunyuan 许可第 5(b) 条尤其涉及输出用于改进其他 AI 模型的限制。详见 THIRD_PARTY_NOTICES.md。

主要代码证据均在上述固定版本：
- openreal2sim/preprocess/{preprocess_manager,image_extraction,depth_prediction,depth_calibration}.py
- openreal2sim/reconstruction/recon_agent.py
- openreal2sim/reconstruction/tools/segmentation_annotator.py
- openreal2sim/reconstruction/modules/{object_mesh_generation,background_pixel_inpainting,scenario_collision_optimization}.py
- openreal2sim/motion/motion_manager.py
- openreal2sim/simulation/isaaclab/demo/sim_agent.sh
- docker/real2sim/{Dockerfile,requirements.docker.txt}
- docker/compose.yml、scripts/installation/install.py
