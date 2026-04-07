import json

def analyze_pelvis_hip_data(file_path):
    # 定义相关关键词
    keywords = ["骨盆", "髋关节", "股骨头", "髋臼", "髂骨", "坐骨", "耻骨"]
    
    valid_count = 0
    total_count = 0
    matched_data = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                total_count += 1
                try:
                    data = json.loads(line.strip())
                    
                    # 将整条数据转为字符串进行全文本搜索，或指定特定字段（如 data.get('text', '')）
                    content = json.dumps(data, ensure_ascii=False)
                    
                    # 校验：1. 是否包含关键词；2. 内容是否非空（这里以字符串长度为例）
                    is_relevant = any(key in content for key in keywords)
                    is_not_empty = len(content.strip()) > 10 # 假设有效数据至少大于10个字符
                    
                    if is_relevant and is_not_empty:
                        valid_count += 1
                        matched_data.append(data)
                        
                except json.JSONDecodeError:
                    print(f"第 {line_number} 行格式错误，已跳过。")
                    continue

        print("-" * 30)
        print(f"分析完成！")
        print(f"总行数: {total_count}")
        print(f"骨盆髋关节相关有效数据量: {valid_count}")
        print(f"占比: {(valid_count / total_count * 100):.2f}%" if total_count > 0 else 0)
        print("-" * 30)
        
        return matched_data

    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")

# 执行分析
if __name__ == "__main__":
    # 如果你的文件名不是 5.jsonl，请在此修改
    analyze_pelvis_hip_data('/media/baller/Getea/5.jsonl')

