import json
from collections import defaultdict
from datetime import datetime
from tqdm import tqdm

def merge_redundant_jsonl(input_file: str, output_file: str, time_threshold_hours: float = 1.0):
    pid_registry = defaultdict(list)
    total_original_records = 0
    
    # ---------------------------------------------------------
    # 阶段 1：读取文件并按 PID 分组加载到内存
    # ---------------------------------------------------------
    print("阶段 1/3: 正在读取并按 PID 聚合数据...")
    with open(input_file, 'r', encoding='utf-8') as f:
        # 为了提供 tqdm 进度，先读取所有行，内存占用约需几GB
        lines = f.readlines()
        
    for line in tqdm(lines, desc="解析数据", unit="条"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            pid = str(data.get("病人编号", "")).strip()
            if pid:
                pid_registry[pid].append(data)
                total_original_records += 1
        except json.JSONDecodeError:
            continue
                
    # ---------------------------------------------------------
    # 阶段 2：执行合并逻辑
    # ---------------------------------------------------------
    merged_records = []
    print(f"\n阶段 2/3: 正在处理 {len(pid_registry)} 个独立患者的记录...")
    
    for pid, records in tqdm(pid_registry.items(), desc="合并冗余", unit="患者"):
        # 1. 提取并验证时间戳
        valid_records = []
        for r in records:
            time_str = r.get("检查时间", "")
            try:
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                valid_records.append((dt, r))
            except ValueError:
                # 缺失有效时间的记录不参与时间差合并，直接转为列表格式后独立保存
                if isinstance(r.get("image_path"), str):
                    r["image_path"] = [r["image_path"]]
                merged_records.append(r)
        
        if not valid_records:
            continue
            
        # 2. 按时间升序排序，保证合并的时序连续性
        valid_records.sort(key=lambda x: x[0])
        
        # 3. 初始化基准点（第一个有效记录）
        base_time, base_record = valid_records[0]
        # 格式统一：将字符串形式的路径转换为列表
        if isinstance(base_record.get("image_path"), str):
            base_record["image_path"] = [base_record["image_path"]]
        elif not base_record.get("image_path"):
            base_record["image_path"] = []
            
        # 4. 滑动对比后续记录
        for current_time, current_record in valid_records[1:]:
            time_diff_hours = abs((current_time - base_time).total_seconds()) / 3600.0
            diag_base = base_record.get("影像学诊断", "").strip()
            diag_curr = current_record.get("影像学诊断", "").strip()
            
            # 判断合并条件
            if time_diff_hours <= time_threshold_hours and diag_base == diag_curr:
                curr_img = current_record.get("image_path")
                # 去重追加路径
                if isinstance(curr_img, str) and curr_img not in base_record["image_path"]:
                    base_record["image_path"].append(curr_img)
                elif isinstance(curr_img, list):
                    for img in curr_img:
                        if img not in base_record["image_path"]:
                            base_record["image_path"].append(img)
            else:
                # 不满足合并条件，固化当前 base_record
                merged_records.append(base_record)
                
                # 重置 base 为 current
                base_time = current_time
                base_record = current_record.copy()
                if isinstance(base_record.get("image_path"), str):
                    base_record["image_path"] = [base_record["image_path"]]
                elif not base_record.get("image_path"):
                    base_record["image_path"] = []
        
        # 不要遗漏保存最后一个处理的 base_record
        merged_records.append(base_record)
        
    # ---------------------------------------------------------
    # 阶段 3：写入磁盘
    # ---------------------------------------------------------
    print(f"\n阶段 3/3: 正在写入合并后的数据到 {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in tqdm(merged_records, desc="写入文件", unit="条"):
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
    # 输出合并报表
    print("\n" + "="*50)
    print(" 数据合并清理完成！")
    print(f" 原始总数据量: {total_original_records}")
    print(f" 合并后数据量: {len(merged_records)}")
    if total_original_records > 0:
        compress_rate = len(merged_records) / total_original_records * 100
        print(f" 最终压缩率:   {compress_rate:.2f}% (消除重复量: {total_original_records - len(merged_records)})")
    print("="*50)

if __name__ == "__main__":
    # 请替换为你当前的 JSONL 数据集路径
    INPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable.jsonl'
    OUTPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable_merged.jsonl'
    
    # 执行合并 (时间阈值: 1.2 小时)
    merge_redundant_jsonl(INPUT_JSONL, OUTPUT_JSONL, time_threshold_hours=1.2)

    # head -n 1 /media/baller/Getea/jsonl/pediatric_ortho_usable_merged.jsonl
    # /media/baller/Getea/image/10_image/10-00003