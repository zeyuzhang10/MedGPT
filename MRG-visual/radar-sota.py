import numpy as np
import matplotlib.pyplot as plt

def plot_radar_chart(
    metrics,
    data_series,
    labels,
    colors,
    markers,
    alpha=0.1,
    grid_linewidth=0.5,
    grid_alpha=0.5,
    radar_linewidth=0.5,
    rader_markersize=5,
    ylim=None
):
    """
    绘制多面雷达图

    参数:
        metrics (list): n个评价指标的名称
        data_series (list of lists): 数据序列
        labels (list): 每个数据序列对应的模型名称
        colors (list): 每个雷达面对应的颜色
        markers (list): 每个雷达面顶点对应的形状标识 ('o', 's', '^', 'v' 等)
        alpha (float): 雷达面的透明度
        grid_linewidth (float): 网格线条的粗细
        grid_alpha (float): 网格线条的透明度
        ylim (tuple): 网格半径范围 (min, max)，例如 (0.0, 1.0)
    """
    # 1. 计算各个指标的角度
    num_vars = len(metrics)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    # 2. 闭合多边形逻辑
    angles += angles[:1]

    # 3. 初始化画布与极坐标系
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # 4. 遍历数据序列，逐个绘制雷达面
    for data, label, color, marker in zip(data_series, labels, colors, markers):
        # 闭合数据点
        data_closed = data + data[:1]

        # 绘制外侧边框线条及顶点 marker
        ax.plot(
            angles,
            data_closed,
            color=color,
            linewidth=radar_linewidth,
            label=label,
            marker=marker,
            markersize=rader_markersize
        )

        # 填充雷达面，并应用透明度 alpha
        ax.fill(angles, data_closed, color=color, alpha=alpha)

    # 5. 设置图表格式
    # 去掉最外层背景圆圈的默认度数标识 (0°, 45° 等)，替换为指标名称
    # ax.set_xticks(angles[:-1])
    # ax.set_xticklabels(metrics, fontsize=12)
    # 注：如果你连文字 metrics 都不想显示，请使用 ax.set_xticklabels([])
    ax.set_xticklabels([])

    # 统一网格样式：内部网格 + 最外层网格
    ax.grid(color='grey', linestyle='-', linewidth=grid_linewidth, alpha=grid_alpha)
    ax.spines['polar'].set_color('grey')
    ax.spines['polar'].set_linestyle('--')
    ax.spines['polar'].set_linewidth(grid_linewidth)
    ax.spines['polar'].set_alpha(grid_alpha)

    # 仅隐藏度量区间文字，保留网格线
    ax.set_yticklabels([])

    # 调整网格半径范围
    if ylim is not None:
        ax.set_ylim(ylim)

    # 6. 配置图例与标题
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=len(labels), fontsize=12)
    plt.title('Performance Comparison: Ours vs Others', y=1.08, fontsize=16, fontweight='bold')

    # 自动调整布局并显示/保存
    plt.tight_layout(rect=[0, 0.10, 1, 1])
    plt.savefig("/media/data/zzy/TI-ReID/MRG-visual/test_radar.png", dpi=300, bbox_inches='tight')
    print("图片已保存！")


if __name__ == "__main__":
    # n = 8 个评价指标
    metrics = [
        'Accuracy', 'Precision', 'Recall', 'F1-Score',
        'Robustness', 'Efficiency', 'Scalability', 'Usability'
    ]

    # 模拟数据
    data_ours = [0.95, 0.92, 0.90, 0.91, 0.88, 0.90, 0.93, 0.90]
    data_sota = [0.85, 0.88, 0.82, 0.85, 0.75, 0.85, 0.80, 0.85]
    data_low1 = [0.72, 0.79, 0.75, 0.78, 0.71, 0.81, 0.74, 0.77]
    data_low2 = [0.70, 0.76, 0.73, 0.75, 0.70, 0.78, 0.71, 0.75]

    data_series = [data_ours, data_sota, data_low1, data_low2]
    labels = ['Ours', 'Others1', 'Others2', 'Others3']

    # 颜色配置池
    colors = ['#ff6b6b', '#3366cc', '#ff9900', '#33aa99']

    # 顶点形状配置：'o'为圆，'s'为方块，'^'为上三角，'v'为下三角
    markers = ['o', 's', '^', 'v']

    # 调用绘图函数
    plot_radar_chart(
        metrics=metrics,
        data_series=data_series,
        labels=labels,
        colors=colors,
        markers=markers,        # 顶点标识参数
        alpha=0.1,              # 调整雷达 面的透明度
        grid_linewidth=0.3,     # 调整网格 线条粗细
        grid_alpha=0.6,         # 调整网格 线条透明度
        radar_linewidth=0.5,    # 调整雷达 边框线条粗细
        rader_markersize=4,     # 调整雷达 顶点图形大小
        ylim=(0.6, 0.96)        # 调整网格半径范围
    )
