import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import matplotlib.cm as cm

def visualize_word_attention(
    image_path: str, 
    cross_attn_weights: torch.Tensor, 
    token_index: int, 
    patch_grid_size: tuple = (14, 14), 
    alpha: float = 0.5,
    save_path: str = None
):
    """
    可视化特定生成词汇对原图的跨模态注意力图。
    
    参数:
        image_path (str): 原始医学图像的路径。
        cross_attn_weights (torch.Tensor): 交叉注意力权重。
            预期形状: (num_heads, sequence_length, num_patches) 或 (sequence_length, num_patches)。
        token_index (int): 目标词汇在序列中的索引 (例如 "pneumonia" 对应的 index)。
        patch_grid_size (tuple): 视觉特征图的空间维度 (H, W)。
            例如：224x224 图像，Patch size 为 16，则 grid_size 为 (14, 14)，共 196 个 patches。
        alpha (float): 原图与热力图融合的透明度权重。
        save_path (str): 如果提供，则将结果保存到该路径。
    """
    # 1. 读取并预处理原始图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # 转换为 RGB 以供 Matplotlib 显示
    orig_h, orig_w = img.shape[:2]

    # 2. 处理注意力权重张量
    # 如果包含多头维度 (num_heads, seq_len, num_patches)，对所有的 heads 求平均
    if cross_attn_weights.dim() == 3:
        attn = cross_attn_weights.mean(dim=0) # 形状变为 (seq_len, num_patches)
    elif cross_attn_weights.dim() == 2:
        attn = cross_attn_weights
    else:
        raise ValueError("传入的 cross_attn_weights 维度必须是 2 或 3。")

    # 取出目标词汇的注意力分布
    # attn_map 形状: (num_patches,)
    attn_map = attn[token_index] 

    # 3. 将 1D 注意力向量 Reshape 回 2D 空间网格
    # 形状: (H, W) -> 例如 (14, 14)
    attn_map = attn_map.view(patch_grid_size[0], patch_grid_size[1]).detach().cpu().numpy()

    # 4. 归一化注意力分数至 [0, 1] 区间
    attn_map = (attn_map - attn_map.min()) / (attn_map.max() - attn_map.min() + 1e-8)

    # 5. 上采样 (双线性插值) 放大到原图尺寸
    attn_map_resized = cv2.resize(attn_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    # 6. 将 [0, 1] 映射到 [0, 255] 并生成伪彩色热力图
    attn_map_color = np.uint8(255 * attn_map_resized)
    # 使用 JET color map (红黄高亮，蓝暗冷)
    heatmap = cv2.applyColorMap(attn_map_color, cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    # 7. 叠加融合 (Overlay)
    overlay = cv2.addWeighted(img, alpha, heatmap, 1 - alpha, 0)

    # 8. 绘图展示
# 8. 绘图展示
    # 稍微增加宽度以容纳 Colorbar (从 15 增加到 16)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # 8.1 原始图像
    axes[0].imshow(img)
    axes[0].set_title("Original Image")
    axes[0].axis('off')

    # 8.2 注意力热力图 (提取 mappable 对象)
    # vmin 和 vmax 确保无论当前图的极值如何，Colorbar 始终固定在 [0, 1] 区间
    # cmap='jet' 对应深蓝到深红的渐变
    im = axes[1].imshow(attn_map_resized, cmap='jet', vmin=0.0, vmax=1.0)
    axes[1].set_title("Attention Heatmap")
    axes[1].axis('off')

    # 8.3 叠加图
    axes[2].imshow(overlay)
    axes[2].set_title(f"Overlayed for Token Idx: {token_index}")
    axes[2].axis('off')

    # 8.4 添加颜色刻度条 (Colorbar)
    # ax=axes[2] 表示将 colorbar 放置在最后一个子图的右侧
    # fraction 和 pad 用于控制 colorbar 的大小和与图像的间距
    cbar = fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
    
    # 根据 Fig 4 的样式，设置关键刻度
    cbar.set_ticks([0.0, 0.5, 1.0])
    cbar.ax.tick_params(labelsize=10) # 调整刻度字体大小

    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图像已保存至 {save_path}")
    
    plt.show()

if __name__ == "__main__":
    # ==========================================
    # 模拟测试环境
    # ==========================================

    # 假设原图尺寸为 512x512
    mock_image = np.ones((512, 512, 3), dtype=np.uint8) * 100 
    cv2.imwrite("mock_chest_xray.jpg", mock_image)

    # 假设模型参数:
    # sequence_length = 30 (生成了 30 个 token)
    # num_patches = 196 (ViT 提取了 14x14 的特征网格)
    # num_heads = 8 (Transformer 的注意力头数)
    seq_len = 30
    num_patches = 196
    heads = 8

    # 1. 模拟从模型中提取出的注意力权重矩阵
    # 维度: [8, 30, 196]
    mock_attn_weights = torch.rand(heads, seq_len, num_patches)

    # 假设为了让可视化明显一点，我们手动给第 10 个 token（比如 "pneumonia"）
    # 在中间偏右上的区域注入极高的注意力权重
    mock_attn_weights[:, 10, :] *= 0.1 # 压低背景
    mock_attn_weights[:, 10, 40:45] = 5.0 # 提亮特定块 

    # 2. 调用可视化函数
    # 假设我们要看第 10 个词对应的注意力，视觉网格为 14x14
    visualize_word_attention(
        image_path="mock_chest_xray.jpg",
        cross_attn_weights=mock_attn_weights,
        token_index=10, 
        patch_grid_size=(14, 14),
        alpha=0.6,
        save_path="attention_pneumonia_vis.png"
    )