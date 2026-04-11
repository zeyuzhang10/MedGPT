import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LogNorm
import numpy as np

def visualize_ortho_data(stats_excel, matrix_excel):
    # 建立骨科关键词的中英映射字典，用于翻译数据内容
    en_dict = {
        "骨盆": "Pelvis", "髋关节": "Hip Joint", "股骨": "Femur", "髋臼": "Acetabulum", 
        "髂骨": "Ilium", "坐骨": "Ischium", "耻骨": "Pubis", "胫骨": "Tibia", 
        "腓骨": "Fibula", "髌骨": "Patella", "肱骨": "Humerus", "尺骨": "Ulna", 
        "桡骨": "Radius", "锁骨": "Clavicle", "肩胛骨": "Scapula", "脊柱": "Spine", 
        "颈椎": "Cervical", "胸椎": "Thoracic", "腰椎": "Lumbar", "骶骨": "Sacrum", 
        "尾骨": "Coccyx", "肋骨": "Ribs", "颅骨": "Skull", "关节": "Joint", 
        "韧带": "Ligament", "半月板": "Meniscus", "滑膜": "Synovium", "肌腱": "Tendon", 
        "软骨": "Cartilage", "骨骺": "Epiphysis", "骨折": "Fracture", 
        "脱位": "Dislocation", "半脱位": "Subluxation", "骨髓炎": "Osteomyelitis", 
        "骨囊肿": "Bone Cyst", "骨软骨瘤": "Osteochondroma", "成骨": "Osteogenesis", 
        "青枝骨折": "Greenstick Fracture", "骨软骨炎": "Osteochondritis", 
        "发育不良": "Dysplasia", "侧弯": "Scoliosis", "畸形": "Deformity"
    }

    # ==========================================
    # 图表 1: 关键词阴阳性分布 (堆叠柱状图)
    # ==========================================
    print(f"正在处理 {stats_excel}...")
    df_stats = pd.read_excel(stats_excel)
    df_top = df_stats.head(20).copy()
    
    # 翻译坐标轴数据
    df_top['关键词'] = df_top['关键词'].map(lambda x: en_dict.get(x, x))
    
    plt.figure(figsize=(14, 8))
    p1 = plt.bar(df_top['关键词'], df_top['阳性数'], label='Positive', color='#E15759')
    p2 = plt.bar(df_top['关键词'], df_top['阴性数'], bottom=df_top['阳性数'], label='Negative', color='#76B7B2')
    
    plt.title('Top 20 Orthopedic Keywords Distribution', fontsize=18, pad=20)
    plt.xlabel('Keywords', fontsize=14)
    plt.ylabel('Count', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    stats_png = 'new-ortho_keywords_distribution.png'
    plt.savefig(stats_png, dpi=300)
    plt.close()
    print(f"成功保存图表 1: {stats_png}")

    # ==========================================
    # 图表 2: 部位 vs 病理 交叉矩阵 (热力图)
    # ==========================================
    print(f"正在处理 {matrix_excel}...")
    df_matrix = pd.read_excel(matrix_excel, index_col=0)
    
    # 翻译 DataFrame 的行索引（部位）和列索引（病理）
    df_matrix.index = df_matrix.index.map(lambda x: en_dict.get(x, x))
    df_matrix.columns = df_matrix.columns.map(lambda x: en_dict.get(x, x))
    
    plt.figure(figsize=(16, 12))
    
    # sns.heatmap(df_matrix, annot=True, fmt='g', cmap='YlOrRd', linewidths=0.5, 
    #             cbar_kws={'label': 'Frequency'})

    sns.heatmap(df_matrix.replace(0, np.nan), annot=df_matrix, fmt='g', cmap='YlOrRd', linewidths=0.5, 
                norm=LogNorm(vmin=1, vmax=df_matrix.max().max()),
                cbar_kws={'label': 'Frequency (Log Scale)'})
    
    plt.title('Orthopedic Body Part vs Pathology Heatmap', fontsize=18, pad=20)
    plt.xlabel('Pathology', fontsize=14)
    plt.ylabel('Body Part', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.yticks(rotation=0, fontsize=12)
    
    plt.tight_layout()
    matrix_png = 'new-ortho_cross_matrix_heatmap.png'
    plt.savefig(matrix_png, dpi=300)
    plt.close()
    print(f"成功保存图表 2: {matrix_png}")

if __name__ == "__main__":
    # 请将这里的两个文件名替换为你实际保存的 Excel 文件路径
    STATS_FILE = '/media/baller/Getea/jsonl/合并后数据集关键词统计.xlsx'     # 包含总命中、阳性数、阴性数的表
    MATRIX_FILE = '/media/baller/Getea/jsonl/合并后部位病理交叉矩阵.xlsx'    # 交叉矩阵表
    
    visualize_ortho_data(STATS_FILE, MATRIX_FILE)