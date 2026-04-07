import os
import pandas as pd

def merge_excel_files(folder_path, output_filename):
    """
    将指定文件夹下的所有 Excel 文件合并为一个文件。
    
    :param folder_path: 目标文件夹路径
    :param output_filename: 合并后的文件名
    """
    all_data_frames = []
    
    # 遍历文件夹中的所有文件
    for file in os.listdir(folder_path):
        # 筛选 excel 文件，排除临时文件（以~$开头的文件）
        if (file.endswith('.xlsx') or file.endswith('.xls')) and not file.startswith('~$'):
            file_path = os.path.join(folder_path, file)
            print(f"正在处理: {file}")
            
            # 读取 Excel 文件
            # 注意：默认读取第一个工作表(sheet)，若需读取全部 sheet 可设置 sheet_name=None
            df = pd.read_excel(file_path)
            
            # 可选：添加一列记录数据来源文件名
            df['来源文件'] = file
            
            all_data_frames.append(df)
    
    if all_data_frames:
        # 合并所有 DataFrame
        # ignore_index=True 重新排列合并后的行索引
        combined_df = pd.concat(all_data_frames, ignore_index=True)
        
        # 保存到本地
        combined_df.to_excel(output_filename, index=False)
        print(f"合并完成！结果已保存至: {output_filename}")
    else:
        print("文件夹中未找到有效的 Excel 文件。")

# 使用示例
target_folder = '/media/baller/Getea/excel/12'  # 替换为你的文件夹路径
output_file = '12.xlsx'
merge_excel_files(target_folder, output_file)