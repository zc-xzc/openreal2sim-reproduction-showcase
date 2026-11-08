# Third-party notices

This integration is not the original OpenReal2Sim algorithm. The safety patch modifies OpenReal2Sim at commit 8f69a19e5dfdfe0aad906fdacad0decf862a7adf. Copyright (c) 2025 Jiageng Mao. The complete upstream MIT license is retained at [LICENSES/OpenReal2Sim-MIT.txt](LICENSES/OpenReal2Sim-MIT.txt).

Changes in patches/0001-safe-cli.patch: disable public Gradio sharing by default and allow an explicit bind address; reject invalid reconstruction/motion stage values; make the simulator shell stop on errors and choose GPU 0 unless explicitly overridden. These are integration safety changes, not new reconstruction methods. No model weights or input datasets are distributed by this patch.

The root MIT license does not license the whole dependency stack, models, data, generated assets, or new integration materials. Each component retains its own terms. Directly audited:
- [FoundationPose](https://github.com/PointsCoder/FoundationPose/blob/59df9f028941353e60993eb46be06ae92d0f2534/LICENSE): NVIDIA research/evaluation non-commercial use restriction.
- [ObjectClear](https://github.com/PointsCoder/ObjectClear/blob/5195da65eb52097d6ca7cbced8143322dddd72de/LICENSE): S-Lab License 1.0, non-commercial use; separate commercial permission.
- [Hunyuan3D-2](https://github.com/PointsCoder/Hunyuan3D-2/blob/3b9a1515e1b2d97cd7ede51d7fcc5ada8617012a/LICENSE): Tencent Hunyuan 3D 2.0 Community License, including territorial limits and section 5(b)'s restriction on using works, output or results to improve other AI models except Hunyuan or its derivatives.

Existing documentation additionally flags GraspGen (NVIDIA), WiLoR (CC BY-NC-ND 4.0), and SAM 3D Objects (SAM License). Their full texts and all nested/model-specific licenses must be checked for the exact assets used. MANO requires separate manual acquisition and applicable permission. A public checkpoint mirror is not proof of redistribution permission.

Use of generated assets for robot policy training requires review of the applicable model/output terms. Private repository visibility does not remove license obligations. This notice is not a complete recursive license audit or legal advice.
