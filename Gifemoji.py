import os
import math
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import trimesh
from io import BytesIO

# 确保安装必要依赖
try:
    import trimesh
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
except ImportError:
    print("请安装依赖：pip install trimesh pillow matplotlib numpy")
    exit(1)

# 渲染配置
RENDER_CONFIG = {
    "width": 512,
    "height": 512,
    "frames": 60,
    "rotation_speed": 360,
    "camera_distance": 3.0,
    "bg_color": (1, 1, 1, 0),  # 透明背景
    "gif_duration": 100,
}

def render_single_emoji(emoji_code: str, root_dir: str = "emoji_export") -> bool:
    """生成单个emoji的旋转GIF（无OpenGL依赖）"""
    # 构建文件路径
    emoji_dir = os.path.join(root_dir, emoji_code)
    obj_path = os.path.join(emoji_dir, f"{emoji_code}.obj")
    output_gif = os.path.join(emoji_dir, f"{emoji_code}.gif")

    # 检查文件是否存在
    if not os.path.exists(emoji_dir):
        print(f"目录不存在: {emoji_dir}")
        return False
    if not os.path.exists(obj_path):
        print(f"OBJ文件不存在: {obj_path}")
        return False

    try:
        # 加载模型
        mesh = trimesh.load(obj_path, force='mesh')

        # 处理多网格场景
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump().sum()  # 合并所有网格

        if not isinstance(mesh, trimesh.Trimesh):
            print(f"无法解析为有效网格: {obj_path}")
            return False

        # 模型居中
        mesh.apply_translation(-mesh.centroid)

        # 设置matplotlib后端为Agg（无界面渲染）
        plt.switch_backend('Agg')
        
        # 创建图形
        fig = plt.figure(figsize=(RENDER_CONFIG["width"]/100, RENDER_CONFIG["height"]/100), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        
        # 关闭坐标轴和背景
        ax.set_axis_off()
        fig.patch.set_alpha(0)

        # 渲染帧
        frames = []
        for i in range(RENDER_CONFIG["frames"]):
            # 清除之前的绘制
            ax.clear()
            ax.set_axis_off()

            # 计算旋转角度
            angle = math.radians(i * (RENDER_CONFIG["rotation_speed"] / RENDER_CONFIG["frames"]))
            
            # 旋转模型
            rotated_mesh = mesh.copy()
            rotated_mesh.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 1, 0]))

            # 绘制网格
            ax.plot_trisurf(
                rotated_mesh.vertices[:, 0],
                rotated_mesh.vertices[:, 1],
                rotated_mesh.vertices[:, 2],
                triangles=rotated_mesh.faces,
                color=[0.8, 0.8, 0.8],  # 灰色模型
                shade=True
            )

            # 设置视角
            ax.view_init(elev=30, azim=i * (RENDER_CONFIG["rotation_speed"] / RENDER_CONFIG["frames"]))
            ax.set_xlim(-RENDER_CONFIG["camera_distance"], RENDER_CONFIG["camera_distance"])
            ax.set_ylim(-RENDER_CONFIG["camera_distance"], RENDER_CONFIG["camera_distance"])
            ax.set_zlim(-RENDER_CONFIG["camera_distance"], RENDER_CONFIG["camera_distance"])

            # 关键修复：使用BytesIO保存图像
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', transparent=True)
            buf.seek(0)
            img = Image.open(buf).convert("RGBA")
            frames.append(img)

        # 保存为GIF
        frames[0].save(
            output_gif,
            format="GIF",
            append_images=frames[1:],
            save_all=True,
            duration=RENDER_CONFIG["gif_duration"],
            loop=0,
            disposal=2
        )

        # 清理资源
        plt.close(fig)
        for f in frames:
            f.close()
        buf.close()

        print(f"成功生成: {output_gif}")
        return True

    except Exception as e:
        print(f"生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 使用实际路径
    render_single_emoji("U+1F01B", root_dir="Z:/2025/emoji135/emoji_export")