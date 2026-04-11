import json
import os
import glob
import shutil

def export_sample_patient_images(file_path: str, base_dir: str, output_base: str, num_patients: int = 2):
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    # 记录我们要抽样的患者 PID
    target_pids = set()
    copied_counts = {pid: 0 for pid in target_pids}
    
    print(f"开始扫描 {file_path}，提取前 {num_patients} 名患者的图像...\n" + "="*60)

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                pid = str(data.get("病人编号", "")).strip()
                
                if not pid:
                    continue
                
                # 收集患者 ID 逻辑
                if len(target_pids) < num_patients:
                    target_pids.add(pid)
                    if pid not in copied_counts:
                        copied_counts[pid] = 0
                elif pid not in target_pids:
                    # 如果已经找齐了目标数量的患者，且当前这行是新的患者，就提前结束读取
                    break
                
                # 提取图像路径 (兼容合并后可能变为 list 的情况)
                img_paths = data.get("image_path", [])
                if isinstance(img_paths, str):
                    img_paths = [img_paths]
                
                # 创建以 PID 命名的目标文件夹
                dest_dir = os.path.join(output_base, pid)
                os.makedirs(dest_dir, exist_ok=True)
                
                # 遍历该条记录关联的所有图像路径
                for rel_path in img_paths:
                    full_dir = os.path.normpath(os.path.join(base_dir, rel_path))
                    png_files = glob.glob(os.path.join(full_dir, '*.png'))
                    
                    for png in png_files:
                        # 为了防止不同目录下的 image.png 相互覆盖，用其父文件夹名做前缀
                        parent_folder = os.path.basename(os.path.dirname(png))
                        file_name = os.path.basename(png)
                        new_file_name = f"{parent_folder}_{file_name}"
                        
                        dest_path = os.path.join(dest_dir, new_file_name)
                        
                        # 复制文件并保留原有的元数据（修改时间等）
                        shutil.copy2(png, dest_path)
                        copied_counts[pid] += 1
                        
            except json.JSONDecodeError:
                print("解析 JSON 失败，跳过该行。")
                continue

    # 打印最终统计报告
    print("提取复制完成！统计如下：")
    for pid in target_pids:
        dest_dir = os.path.join(output_base, pid)
        print(f" 👤 患者 ID: {pid}")
        print(f"    ├─ 保存路径: {dest_dir}")
        print(f"    └─ 成功复制: {copied_counts[pid]} 张 PNG 图像")
    print("="*60)

if __name__ == "__main__":
    # 使用合并后的最新 JSONL
    TARGET_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable_merged.jsonl'
    
    # 原始图像的根目录
    BASE_DIR = '/media/baller/Getea/image'
    
    # 导出的 sample 文件夹路径
    OUTPUT_SAMPLE_DIR = '/media/baller/Getea/image_sample/'
    
    # 执行提取，设置 num_patients=2
    export_sample_patient_images(TARGET_JSONL, BASE_DIR, OUTPUT_SAMPLE_DIR, num_patients=2)