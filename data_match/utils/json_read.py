import os
import json
from pathlib import Path
from tqdm import tqdm  # 导入进度条库
import glob
import numpy as np
from PIL import Image
from pathlib import Path

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

if __name__ == "__main__":
    # # 配置输入文件夹路径和输出文件路径
    # INPUT_DIRECTORY = '/media/baller/Getea/jsonl'                       # .jsonl 所在的目录
    # OUTPUT_FILE_PATH = '/media/baller/Getea/pediatric_ortho.jsonl' # 提取后生成的新文件
    
    # process_ortho_data(INPUT_DIRECTORY, OUTPUT_FILE_PATH)

    # 配置输入、输出与基础图像路径
    INPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho.jsonl'
    OUTPUT_JSONL = '/media/baller/Getea/jsonl/pediatric_ortho_usable.jsonl'
    
    # 基础图像目录，注意尾部斜杠或拼接逻辑
    # 如果用户的绝对要求是 /media/baller/Getea/image 做前缀，请在此处修改。
    BASE_IMAGE_DIR = '/media/baller/Getea/image' 
    
    filter_jsonl_by_image(INPUT_JSONL, OUTPUT_JSONL, BASE_IMAGE_DIR)
