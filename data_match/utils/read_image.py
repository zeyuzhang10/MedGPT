import json
import os
import glob

def preview_image_paths(file_path: str, base_dir: str, top_n: int = 20):
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    print(f"正在读取 {file_path} 的前 {top_n} 条数据...\n" + "="*80)

    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if count >= top_n:
                break
                
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                idx = data.get("idx", "未知")
                rel_path = data.get("image_path", "")
                
                # 提取诊断简述用于对照参考（避免过长，截取前40个字符）
                diag = data.get("影像学诊断", "").replace("\n", " ")
                if len(diag) > 40:
                    diag = diag[:40] + "..."
                
                # 拼接完整的绝对路径
                full_dir = os.path.normpath(os.path.join(base_dir, rel_path))
                
                # 检索该目录下的 PNG 图片
                png_files = glob.glob(os.path.join(full_dir, '*.png'))
                
                print(f"[{count+1:02d}] 数据编号: {idx}")
                print(f"     诊断对照: {diag}")
                print(f"     文件夹径: {full_dir}")
                
                if png_files:
                    # 为了方便直接复制查看，打印第一张图的绝对路径
                    print(f"     图像示例: {png_files[0]}  (共 {len(png_files)} 张)")
                else:
                    print(f"     图像示例: ⚠️ 该目录下未找到 PNG 图像")
                print("-" * 80)
                
                count += 1
                
            except json.JSONDecodeError:
                print(f"解析 JSON 失败，跳过。")
                continue

if __name__ == "__main__":
    # 指向你刚刚过滤好的可用骨科数据
    TARGET_JSONL = '/media/baller/Getea/pediatric_ortho_usable.jsonl'
    # 你的图像根目录
    BASE_DIR = '/media/baller/Getea/'
    
    preview_image_paths(TARGET_JSONL, BASE_DIR, top_n=20)