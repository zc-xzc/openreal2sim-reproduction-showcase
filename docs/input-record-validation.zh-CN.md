# 输入记录复算与匿名聚合

[返回首页](../README.md)

本轮直接解析两份归档CSV，仅分析表中记录，不读取CSV路径指向的原图。结果见 [input-record-summary.json](../reports/input-record-summary.json)。

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| 总清单数据行 | 158 | 不是158张原图字节验证 |
| 候选数据行 | 20 | 不是20次重建完成 |
| 非空唯一key | 总清单158、候选20 | 不证明内容无重复 |
| YES/NO | 20/138 | 仅表示表中的选中标签 |
| 候选关联 | 20个key均存在，集合恰等于YES集合 | 表内一致性，不是筛选质量验证 |
| 记录格式 | JPEG 152、PNG 6 | 来自元数据字段，未解码原图 |
| 数值字段 | 尺寸均为可解析正整数；分数为38–100有限数 | 不证明测量正确、评分有效或重建成功概率 |

## 复算工具

`scripts/summarize_input_manifest.py` 使用标准库，仅输出固定白名单的聚合字段。它不输出原文件名、路径、逐图key、reason、缩略图或EXIF，不读取图像内容，不重新评分，也不会联网上传。

在自己本地保留原CSV时，可以执行：

```bash
python3 scripts/summarize_input_manifest.py   --manifest /path/to/image_manifest.csv   --candidates /path/to/selected_candidates.csv
```

总清单要求suggested_key、quality_score、width、height、image_format、selected列；候选清单要求suggested_key列。未知格式与选中标签仅计OTHER，不原样回显。解析错误只报通用错误，不打印源数据或路径。

包含10项合成解析测试。公开包没有原CSV，因此公开读者可运行合成测试，但不能仅靠本包复算这批私有原件。报告中的统计是此次对原件的审查结果，不是数据集公开发布。
