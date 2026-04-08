import os
import json
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
    
    print(f"共找到 {len(jsonl_files)} 个 .jsonl 文件，开始处理...\n")

    # 以追加/覆写模式打开目标输出文件
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for file_path in jsonl_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    for line_number, line in enumerate(in_f, 1):
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
                            print(f"文件 [{file_path.name}] 第 {line_number} 行格式错误，已跳过。")
                            continue
            except Exception as e:
                print(f"读取文件 [{file_path.name}] 时出错: {e}")

    print("-" * 30)
    print("分析与提取完成！")
    print(f"处理文件总数: {len(jsonl_files)}")
    print(f"读取数据总行数: {total_count}")
    print(f"提取的骨科数据量: {valid_count}")
    print(f"数据有效占比: {(valid_count / total_count * 100):.2f}%" if total_count > 0 else "0.00%")
    print(f"输出文件已保存至: {output_file}")
    print("-" * 30)

if __name__ == "__main__":
    # 配置输入文件夹路径和输出文件路径
    INPUT_DIRECTORY = '/media/baller/Getea/jsonl'                       # .jsonl 所在的目录
    OUTPUT_FILE_PATH = '/media/baller/Getea/pediatric_ortho.jsonl' # 提取后生成的新文件
    
    process_ortho_data(INPUT_DIRECTORY, OUTPUT_FILE_PATH)