# DICOM 数据集处理脚本

这套脚本用于：
- 递归扫描某个月份目录（如 `4/`）下的 DICOM
- 尝试解码像素并导出 PNG（损坏/不可解码会跳过）
- 从 DICOM 提取 `PatientID/放射编号(AccessionNumber 等)/检查时间` 等信息
- 在对应 Excel（如 `excel/4.xlsx`）中进行“相似度/容错”匹配
- 对匹配成功的数据写出 `jsonl`，并把 PNG 存入 `{month}_image/{idx}/`
- 生成带时间戳的运行日志，输出统计信息

适用场景：你有“影像 DICOM 文件 + 同月 Excel 检查记录”，需要自动对齐并生成训练用 `jsonl + png`。

> 建议先跑一次“单个 DICOM 字段检查”，确认你这批数据里真正有值的字段是哪些（有些 DICOM 可能没有 PatientID）。

## 1) 安装依赖

建议使用独立环境（conda/venv）。

```bash
pip install -r requirements.txt
```

如果你使用 conda，推荐在独立环境中安装依赖，避免污染 base 环境。

## 2) 先检查一个 DICOM 的字段（强烈建议）

```bash
python -m dicom_dataset_tools.inspect_one_dicom --dicom "F:\\4\\...\\xxx.dcm"
python -m dicom_dataset_tools.inspect_one_dicom --dicom "F:\\4\\1\\0ABCDB4F\\47E75FE1\\BCB8A19B"

# 也兼容直接运行（不推荐，但可用）
python dicom_dataset_tools/inspect_one_dicom.py --dicom "F:\\4\\1\\0ABCDB4F\\47E75FE1\\BCB8A19B"
```

它会打印常见关键 tag（PatientID、AccessionNumber、StudyDate/StudyTime 等）以及你可以用来匹配 Excel 的候选字段。

### DICOM 字段名（在代码里的位置）

- 病人编号/放射编号等提取逻辑在 `dicom_pipeline/dicom_utils.py` 的 `extract_meta()`：
	- `patient_id` 候选：`PatientID` / `OtherPatientIDs` / `PatientName`
	- `accession_number` 候选：`AccessionNumber`（优先）/ `StudyID` / `RequestedProcedureID` / `ScheduledProcedureStepID` / `OtherStudyNumbers`
- 检查日期时间提取逻辑在同文件的 `parse_study_datetime()`：
	- 优先 `AcquisitionDateTime`
	- 兜底使用 `StudyDate + StudyTime`（并兼容 Acquisition/Content/Series 的 Date/Time）

> 你这批样例里：`AccessionNumber` 有值；`PatientID` 可能为 `null`（这会明显影响 Excel 匹配）。

## 3) 正式处理某个月份

示例（处理 4 月）：

```bash
python -m dicom_dataset_tools.build_month_jsonl --root "F:\\" --month 4
python /media/baller/Getea/dicom_dataset_tools/build_month_jsonl.py --root /media/baller/Getea/ --month 10

# 也兼容直接运行（不推荐，但可用）
python dicom_dataset_tools/build_month_jsonl.py --root "F:\\" --month 4
```

### Windows 路径注意事项（很重要）

- `--root` 推荐传 **盘符根目录**：`F:\\`（也就是 `F:\`）。
- 不要传 `F:`（会变成“相对当前目录”，可能写到 `F:logs` 这种怪路径）。
- PowerShell 中建议像这样写：

```powershell
python -m dicom_dataset_tools.build_month_jsonl --root 'F:\' --month 4
```

它默认会尝试读取：
- DICOM 根目录：`F:\\4`
- Excel：`F:\\excel\\4.xlsx`

输出默认写到根目录：
- `4.jsonl`
- `4_image/4-00001/*.png`
- `logs/run_YYYYmmdd-HHMMSS_4.log`

### 输出格式说明

- `*.jsonl`：每行一个 JSON 对象
	- `idx`：如 `4-00001`
	- `image_path`：导出 PNG 所在目录（相对 root）
	- 其余字段：来自 Excel 的整行（并将“影像学诊断/影像学表现/设备类型”等优先提前）
	- `dicom_meta`：从 DICOM 提取到的核心字段（包含 `source_dicom`，方便溯源）
- `{month}_image/`：每个 `idx` 一个子目录，内部存 `image.png`（多帧则 `image_000.png ...`）。
- `{month}_image/_tmp/`：运行中临时目录，程序会尽量在失败时自动清理。

## 4) 测试模式（只采样 N 条）

```bash
python -m dicom_dataset_tools.build_month_jsonl --root "F:\\" --month 4 --test --sample 20 --seed 42
```

测试模式会写出：
- `4_test.jsonl`
- `4_image_test/`

### 关于“采样”的说明

测试模式不是简单取“遍历到的前 N 个文件”，而是尽量从不同的顶层目录里收集一个更大的候选池并打散，以降低采到同一病人/同一批次的概率。

## 5) 进度与日志

- 处理进度：若安装了 `tqdm`，会显示“候选 DICOM 列表”的处理进度条（总数为候选数/采样数）。
- 扫描阶段：正式模式需要先扫描目录以收集候选列表，这一步在超大目录下会比较耗时；当前版本会在日志里输出 `scanned_files` 与 `probable_dicoms`，但不会显示扫描进度条。
- 日志文件：写在 `logs/` 下，包含关键统计（读 DICOM 成功数、Excel 匹配数、PNG 导出成功数、最终写入数、占比、最后 idx）。

## 5) 常用可调参数

- `--excel`: 手动指定 Excel 路径（当不是 `excel/{month}.xlsx` 时很有用）
- `--fuzz-threshold`: 文本相似度阈值（默认 0.90）
- `--day-tolerance`: 日期允许误差天数（默认 1）
- `--aggressive-scan`: 更激进地把“无扩展名/无 DICM 头”的文件也尝试当 DICOM 读（可能更慢）

## 6) 匹配策略（Excel 对齐）

程序会尝试从 Excel 自动识别三列：病人编号 / 放射编号 / 检查时间（基于表头相似度）。

匹配逻辑大致为：
- 优先：`pid + acc` 规范化后完全一致
- 其次：基于相似度的加权评分（pid、acc 权重更高；日期作为弱约束，并允许 `--day-tolerance` 天误差）

如果你发现大量 `excel_no_match`：
- 先用 `inspect_one_dicom` 确认 DICOM 里的 `PatientID` 是否经常为空
- 再核对 Excel 的“放射编号”列是否就是 `AccessionNumber` 对应的那串（例如样例 `202404010253`）
- 必要时把阈值调低一点：`--fuzz-threshold 0.85`

## 7) 常见问题

### 1) ModuleNotFoundError: No module named 'dicom_dataset_tools'

优先用 `-m` 方式运行：

```bash
python -m dicom_dataset_tools.build_month_jsonl --root "F:\\" --month 4
```

### 2) Excel 读入警告（openpyxl default style）

这是 Excel 文件样式缺省导致的 openpyxl 提示，一般不影响数据读取。

### 3) DICOM 警告（Invalid value for VR UI / VR lookup failed）

这类警告通常来自部分非标准 tag 或写入不规范，一般不影响像素导出与关键字段提取；如果确实影响读入，会在日志里以 `dicom_read_fail` 记录。

> 你如果把几条 Excel 表头（列名）发我，我也可以把列名映射词典再强化一波。
