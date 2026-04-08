def count_jsonl_lines(file_path):
    """
    统计.jsonl文件的行数（即JSON条目数），并输出前3行内容

    参数:
        file_path (str): .jsonl文件的路径

    返回:
        int: 文件的行数；若出错返回-1
    """
    line_count = 0
    try:
        # 以只读模式打开文件，使用utf-8编码避免中文乱码
        with open(file_path, 'r', encoding='utf-8') as f:
            print("="*50)
            print("📄 文件前3行JSON内容：")
            print("="*50)
            
            # 逐行迭代读取（低内存占用，适合大文件）
            for line in f:
                line_count += 1
                # 输出前3行内容
                if line_count <= 3:
                    print(f"第 {line_count} 行：{line.strip()}")
            
            print("="*50)
        return line_count
    
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 不存在")
        return -1
    except PermissionError:
        print(f"错误：没有权限读取文件 '{file_path}'")
        return -1
    except Exception as e:
        print(f"读取文件时发生未知错误：{str(e)}")
        return -1

# 调用示例
if __name__ == "__main__":
    # 替换为你的.jsonl文件路径
    jsonl_file_path = "/media/baller/Getea/5.jsonl"
    lines = count_jsonl_lines(jsonl_file_path)
    if lines >= 0:
        print(f"✅ 该.jsonl文件共有 {lines} 行")