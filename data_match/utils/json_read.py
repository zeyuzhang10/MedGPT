import os
import json
from pathlib import Path
from tqdm import tqdm  # 导入进度条库
import glob
import numpy as np
from PIL import Image
import re
from collections import defaultdict
import pandas as pd
from tqdm import tqdm

def process_ortho_data(input_dir: str, output_file: str):
    # 丰富的骨科关键词库（涵盖常见骨骼、关节、软组织及典型骨科疾病）
    ortho_keywords = [
        "骨盆", "髋关节", "股骨", "髋臼", "髂骨", "坐骨", "耻骨", 
        "胫骨", "腓骨", "髌骨", "肱骨", "尺骨", "桡骨", "锁骨", "肩胛骨",
        "脊柱", "颈椎", "胸椎", "腰椎", "骶骨", "尾骨", "肋骨", "颅骨",
        "关节", "韧带", "半月板", "滑膜", "肌腱", "软骨",
        "骨折", "脱位", "半脱位", "骨髓炎", "骨囊肿", "骨软骨瘤", "成骨",
        "骨骺", "青枝骨折", "骨软骨炎", "发育不良", "侧弯", "畸形"
    ]
    
    valid_count = 0
    total_count = 0
    
    # 获取输入目录下所有的 .jsonl 文件（包含子文件夹）
    input_path = Path(input_dir)
    jsonl_files = list(input_path.glob("**/*.jsonl"))
    
    print(f"共找到 {len(jsonl_files)} 个 .jsonl 文件，正在统计总数据行数...\n")

    # ===================== 新增：预先统计总行数（用于进度条）=====================
    total_lines = 0
    for file_path in jsonl_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                total_lines += sum(1 for _ in f)
        except Exception:
            continue
    # ==========================================================================

    print(f"✅ 总数据行数：{total_lines}，开始处理...\n")
    # 初始化进度条
    pbar = tqdm(total=total_lines, desc="处理进度", unit="行", colour="green")

    # 以追加/覆写模式打开目标输出文件
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for file_path in jsonl_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    for line_number, line in enumerate(in_f, 1):
                        # 更新进度条
                        pbar.update(1)
                        
                        line = line.strip()
                        if not line:
                            continue
                            
                        total_count += 1
                        try:
                            data = json.loads(line)
                            content_str = json.dumps(data, ensure_ascii=False)
                            
                            # 条件 A：内容长度有效（过滤掉极短的异常数据）
                            if len(content_str) <= 10:
                                continue
                                
                            # 条件 B：包含骨科关键词
                            is_ortho = any(key in content_str for key in ortho_keywords)
                            
                            # 默认全部为儿童数据，满足骨科条件即为目标数据
                            if is_ortho:
                                out_f.write(line + '\n')
                                valid_count += 1
                                
                        except json.JSONDecodeError:
                            # print(f"文件 [{file_path.name}] 第 {line_number} 行格式错误，已跳过。")
                            continue
            except Exception as e:
                print(f"读取文件 [{file_path.name}] 时出错: {e}")

    # 关闭进度条
    pbar.close()

    print("-" * 50)
    print("分析与提取完成！")
    print(f"处理文件总数: {len(jsonl_files)}")
    print(f"读取数据总行数: {total_count}")
    print(f"提取的骨科数据量: {valid_count}")
    print(f"数据有效占比: {(valid_count / total_count * 100):.2f}%" if total_count > 0 else "0.00%")
    print(f"输出文件已保存至: {output_file}")
    print("-" * 50)

def check_single_png_usability(png_path: str) -> bool:
    """
    检测单张 PNG 图像是否包含有效的医学影像信息。
    """
    try:
        with Image.open(png_path) as img:
            # 统一转换为灰度图进行矩阵计算
            img_gray = img.convert('L')
            arr = np.array(img_gray)
            
            h, w = arr.shape
            # 规则 1：尺寸限制
            if h < 128 or w < 128:
                return False
                
            # 规则 2：前景像素占比（灰度值大于 5 的像素比例）
            foreground_ratio = np.sum(arr > 5) / (h * w)
            if foreground_ratio < 0.01:
                return False
                
            # 规则 3：信息熵/标准差检测（过滤极低对比度的废片）
            std_dev = np.std(arr)
            if std_dev < 5.0:
                return False
                
            return True
    except Exception:
        # 文件损坏或无法读取视为无效
        return False

def filter_jsonl_by_image(input_file: str, output_file: str, base_img_dir: str):
    """
    遍历 JSONL 文件，校验对应目录下的图像，导出可用的数据记录。
    """
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    total_count = 0
    valid_count = 0
    missing_dir_count = 0

    print(f"正在统计文件总行数...")
    with open(input_file, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for line in f)
    print(f"✅ 待处理总记录数：{total_lines}，开始校验图像...\n")

    # 初始化进度条：青色进度条，实时显示进度
    pbar = tqdm(total=total_lines, desc="图像校验进度", unit="条", colour="cyan")

    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        for line_idx, line in enumerate(fin, 1):
            pbar.update(1)
            
            line = line.strip()
            if not line:
                continue
                
            total_count += 1
            try:
                data = json.loads(line)
                rel_path = data.get("image_path", "")
                
                if not rel_path:
                    continue

                full_dir = os.path.normpath(os.path.join(base_img_dir, rel_path))
                
                if not os.path.isdir(full_dir):
                    missing_dir_count += 1
                    continue
                
                # 获取目录下所有 PNG 文件
                png_files = glob.glob(os.path.join(full_dir, '*.png'))
                if not png_files:
                    continue

                # 判断文件夹是否有效：只要有一张有效切片，即认为该序列可用
                is_dir_valid = False
                for png in png_files:
                    if check_single_png_usability(png):
                        is_dir_valid = True
                        break  # 找到一张有效即可通过，节省计算开销
                
                if is_dir_valid:
                    fout.write(line + '\n')
                    valid_count += 1

            except json.JSONDecodeError:
                # print(f"第 {line_idx} 行 JSON 解析失败。")
                pass
            except Exception as e:
                # print(f"处理第 {line_idx} 行时发生异常: {e}")
                pass

    # 关闭进度条
    pbar.close()

    # 输出统计信息
    print("\n" + "-" * 40)
    print("图像可用性校验与过滤完成！")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"总读取记录数: {total_count}")
    print(f"未找到图像目录数: {missing_dir_count}")
    print(f"图像可用且成功导出的记录数: {valid_count}")
    print(f"最终留存率: {(valid_count / total_count * 100):.2f}%" if total_count > 0 else "0.00%")
    print("-" * 40)


def analyze_ortho_keywords(file_path: str):
    # 定义要统计的关键词列表
    ortho_keywords = [
        "骨盆", "髋关节", "股骨", "髋臼", "髂骨", "坐骨", "耻骨", 
        "胫骨", "腓骨", "髌骨", "肱骨", "尺骨", "桡骨", "锁骨", "肩胛骨",
        "脊柱", "颈椎", "胸椎", "腰椎", "骶骨", "尾骨", "肋骨", "颅骨",
        "关节", "韧带", "半月板", "滑膜", "肌腱", "软骨",
        "骨折", "脱位", "半脱位", "骨髓炎", "骨囊肿", "骨软骨瘤", "成骨",
        "骨骺", "青枝骨折", "骨软骨炎", "发育不良", "侧弯", "畸形"
    ]
    
    # 初始化统计字典
    keyword_counts = {kw: 0 for kw in ortho_keywords}
    total_records = 0

    if not Path(file_path).exists():
        print(f"错误：找不到文件 {file_path}")
        return

    print(f"开始扫描并统计文件: {file_path} ...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            total_records += 1
            try:
                # 解析 JSON 确保数据完整，并转为中文字符串用于检索
                data = json.loads(line)
                content_str = json.dumps(data, ensure_ascii=False)
                
                # 检查每个关键词是否存在于该条数据中
                for kw in ortho_keywords:
                    if kw in content_str:
                        keyword_counts[kw] += 1
                        
            except json.JSONDecodeError:
                print(f"第 {line_idx} 行解析失败，已跳过。")

    # 对统计结果按数值进行降序排序
    sorted_counts = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

    # 打印最终报告
    print("\n" + "=" * 45)
    print(f"统计完成！总分析数据量: {total_records} 条")
    print("=" * 45)
    print(f"{'关键词':<10}\t{'数据条数':<10}\t{'占比'}")
    print("-" * 45)
    
    for kw, count in sorted_counts:
        # 只打印有命中记录的关键词（如果想全打印，可去掉 if 判断）
        if count > 0:
            percentage = (count / total_records * 100) if total_records > 0 else 0
            # 使用 chr(12288) (全角空格) 补齐中文对齐
            kw_padded = kw.ljust(6, chr(12288)) 
            print(f"{kw_padded}\t{count:<10}\t{percentage:.2f}%")
            
    print("-" * 45)
    print("注：由于单条检查记录可能同时包含多个部位或疾病（如'股骨骨折'），因此各关键词条数总和可能大于总数据量。")


def analyze_dataset_distribution(file_path: str):
    # 1. 定义关键词词典（区分为“部位”和“病理”用于交叉矩阵）
    body_parts = [
        "骨盆", "髋关节", "股骨", "髋臼", "髂骨", "坐骨", "耻骨", 
        "胫骨", "腓骨", "髌骨", "肱骨", "尺骨", "桡骨", "锁骨", "肩胛骨",
        "脊柱", "颈椎", "胸椎", "腰椎", "骶骨", "尾骨", "肋骨", "颅骨",
        "关节", "韧带", "半月板", "滑膜", "肌腱", "软骨", "骨骺"
    ]
    pathologies = [
        "骨折", "青枝骨折", "脱位", "半脱位", "骨髓炎", "骨囊肿", 
        "骨软骨瘤", "成骨", "骨软骨炎", "发育不良", "侧弯", "畸形"
    ]
    all_keywords = body_parts + pathologies
    
    # 否定词典（用于判断阴性）
    negative_words = ["未见", "无", "未发现", "排除", "未见明显", "未显示", "正常"]

    # 2. 初始化统计容器
    pos_neg_stats = {kw: {'pos': 0, 'neg': 0} for kw in all_keywords}
    modality_stats = {kw: {'CT': 0, 'DR/CR': 0, 'MRI': 0, 'Other': 0} for kw in all_keywords}
    cross_matrix = defaultdict(lambda: defaultdict(int))
    
    # 获取总行数
    print("正在计算文件行数...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return

    print(f"\n开始分析 {total_lines} 条数据分布...")
    
    # 3. 逐行解析
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=total_lines, desc="Processing JSONL", unit="line"):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                diag_text = data.get("影像学表现", "") + "。" + data.get("影像学诊断", "")
                full_text = json.dumps(data, ensure_ascii=False)
                
                # 识别模态
                modality_raw = str(data.get("设备类型", "")).upper() + str(data.get("检查", "")).upper()
                if "CT" in modality_raw:
                    modality = "CT"
                elif any(m in modality_raw for m in ["DR", "CR", "DX", "X线", "摄片"]):
                    modality = "DR/CR"
                elif any(m in modality_raw for m in ["MR", "核磁"]):
                    modality = "MRI"
                else:
                    modality = "Other"

                clauses = re.split(r'[。，；！\n]', diag_text)
                
                # 关键词统计
                for kw in all_keywords:
                    if kw in full_text:
                        modality_stats[kw][modality] += 1
                        is_negative = False
                        for clause in clauses:
                            if kw in clause:
                                if any(neg in clause for neg in negative_words):
                                    is_negative = True
                                    break
                        if is_negative:
                            pos_neg_stats[kw]['neg'] += 1
                        else:
                            pos_neg_stats[kw]['pos'] += 1

                # 交叉矩阵
                for part in body_parts:
                    if part in full_text:
                        for patho in pathologies:
                            if patho in full_text:
                                cross_matrix[part][patho] += 1
                                
            except json.JSONDecodeError:
                continue
                
    # ===================== 输出结果 =====================
    print("\n\n生成统计表格...")

    # 1. 关键词阴阳性 + 模态表格
    rows = []
    for kw in all_keywords:
        total = pos_neg_stats[kw]['pos'] + pos_neg_stats[kw]['neg']
        if total == 0:
            continue
        pos_cnt = pos_neg_stats[kw]['pos']
        neg_cnt = pos_neg_stats[kw]['neg']
        pos_rate = pos_cnt / total * 100 if total > 0 else 0
        rows.append({
            "关键词": kw, "总命中": total, "阳性数": pos_cnt, "阴性数": neg_cnt, "阳性率(%)": round(pos_rate,1),
            "CT": modality_stats[kw]['CT'], "DR/CR": modality_stats[kw]['DR/CR'],
            "MRI": modality_stats[kw]['MRI'], "其他": modality_stats[kw]['Other']
        })
    df_kw = pd.DataFrame(rows).sort_values(by="总命中", ascending=False)

    # 2. 部位-病理交叉矩阵
    df_cross = pd.DataFrame(cross_matrix).fillna(0).astype(int).T
    df_cross = df_cross.loc[(df_cross != 0).any(axis=1), (df_cross != 0).any(axis=0)]

    # ===================== 保存文件 =====================
    save_dir = os.path.dirname(file_path)  # 保存到和原数据同一个文件夹

    # 保存 关键词统计
    df_kw.to_excel(os.path.join(save_dir, "数据集关键词统计.xlsx"), index=False)
    df_kw.to_markdown(os.path.join(save_dir, "数据集关键词统计.md"), index=False)

    # 保存 交叉矩阵
    df_cross.to_excel(os.path.join(save_dir, "部位病理交叉矩阵.xlsx"))
    df_cross.to_markdown(os.path.join(save_dir, "部位病理交叉矩阵.md"))

    print("\n✅ 所有结果已保存！")
    print(f"📁 保存位置：{save_dir}")
    print("📄 生成文件：")
    print("   - 数据集关键词统计.xlsx")
    print("   - 数据集关键词统计.md")
    print("   - 部位病理交叉矩阵.xlsx")
    print("   - 部位病理交叉矩阵.md")

    # 同时在终端打印预览
    print("\n" + "="*60)
    print("关键词统计预览")
    print("="*60)
    print(df_kw.to_string(index=False))

if __name__ == "__main__":

    # INPUT_DIRECTORY = '/media/baller/Getea/jsonl'                       # .jsonl 所在的目录
    # OUTPUT_FILE_PATH = '/media/baller/Getea/pediatric_ortho.jsonl' # 提取后生成的新文件
    # process_ortho_data(INPUT_DIRECTORY, OUTPUT_FILE_PATH)

    # Stage 2: 图像可用性校验与过滤
    # INPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho.jsonl'
    # OUTPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable.jsonl'
    # BASE_IMAGE_DIR = '/media/baller/Getea/image' 
    # filter_jsonl_by_image(INPUT_JSONL, OUTPUT_JSONL, BASE_IMAGE_DIR)

    # # Stage 3：统计骨科子分类数据量
    # TARGET_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable.jsonl'
    # analyze_ortho_keywords(TARGET_JSONL)
    
    # Stage 4：分析数据分布（阴阳性、模态分布、部位-病理交叉矩阵）
    TARGET_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable.jsonl'
    analyze_dataset_distribution(TARGET_JSONL)
