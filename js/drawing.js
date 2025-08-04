const canvas = document.getElementById("iconCanvas");
const ctx = canvas.getContext("2d");
const input = document.getElementById("iconInput");
let elements = [];
let dragging = false;
let dragIndex = null;
let selectedIndex = null;
let offsetX = 0, offsetY = 0;
let selectionBox = null;
let selectedIndices = [];




// 初始化 canvas 尺寸
function resizeCanvas() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    drawAll();
}
window.addEventListener("load", resizeCanvas);
window.addEventListener("resize", resizeCanvas);

// 输入监听并添加图标
input.addEventListener("input", () => {
    const icons = extractIcons(input.value);
    addIcons(icons);
    input.value = "";
});

// Emoji 提取函数
function extractIcons(text) {
    const emojiRegex = /[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u26FF\uFE0F]/g;
    return text.match(emojiRegex) || [];
}

// 添加图标到元素数组
function addIcons(icons) {
    icons.forEach((icon, i) => {
        elements.push({
            char: icon,
            x: 60 + (elements.length + i) * 70,
            y: canvas.height / 2,
            size: 200,
            rotation: 0
        });
    });

    // ✅ 同步状态
    setScene([...elements]); // 使用展开符确保不会共享引用
}

// 绘制所有图标（支持旋转）
function drawAll() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // ✅ 绘制选择框（背景层）
    if (selectionBox) {
        const x = Math.min(selectionBox.startX, selectionBox.endX);
        const y = Math.min(selectionBox.startY, selectionBox.endY);
        const w = Math.abs(selectionBox.startX - selectionBox.endX);
        const h = Math.abs(selectionBox.startY - selectionBox.endY);

        ctx.save();
        ctx.globalAlpha = 0.08;
        ctx.fillStyle = "blue";
        ctx.fillRect(x, y, w, h);
        ctx.restore();

        ctx.strokeStyle = "rgba(0, 0, 255, 0.5)";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
    }
    elements.forEach((el, i) => {
        if (el.type === "group") {
            ctx.save();

            // ✅ 将群组中心作为旋转中心（兼容摇摆动画）
            const centerX = el.x;
            const centerY = el.y;
            // 🎯 先平移到中心
            ctx.translate(centerX, centerY);

            // 🔄 缩放和旋转都在中心坐标系内进行
            ctx.scale(el.size || 1, el.size || 1);
            ctx.rotate((el.rotationBase || 0) + (el.rotationSwing || 0));

            // ↩️ 再平移回原始坐标系
            ctx.translate(-centerX, -centerY);

            // ✅ 绘制子元素
            el.children.forEach((child, j) => {
                drawEmojiWithContext(
                    child,
                    el.x + child.x,
                    el.y + child.y,
                    selectedIndices.includes(i)
                );
            });

            ctx.restore();
        } else {
            drawEmojiWithContext(
                el,
                el.x,
                el.y,
                selectedIndices.includes(i) || selectedIndex === i || dragIndex === i
            );
        }
    });

}
function drawEmojiWithContext(el, finalX, finalY, isSelected) {
    const rotation = (el.rotationBase || 0) + (el.rotationSwing || 0) + (el.rotation || 0);
    const scaleX = (el.isFlipped ? -1 : 1) * (el.scale || 1);
    const scaleY = el.scale || 1;

    ctx.save();
    ctx.translate(finalX, finalY);
    ctx.scale(scaleX, scaleY);
    ctx.rotate(rotation);

    ctx.font = `${el.size}px "SegoeEmojiOld", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    ctx.shadowColor = "rgba(0, 0, 0, 0.2)";
    ctx.shadowBlur = 4;
    ctx.fillText(el.char, 0, 0);
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;

    if (isSelected) {
        ctx.strokeStyle = "red";
        ctx.lineWidth = 2;
        const padding = 4;
        ctx.strokeRect(-el.size / 2 - padding, -el.size / 2 - padding, el.size + padding * 2, el.size + padding * 2);
    }

    ctx.restore();
}

document.getElementById("mergeSelectedBtn").addEventListener("click", () => {
    if (selectedIndices.length < 2) {
        alert("请至少选择两个元素进行合并");
        return;
    }

    // 获取选中元素数据
    const selectedElements = selectedIndices.map(index => elements[index]);

    // 计算组合中心
    const centerX = selectedElements.reduce((sum, el) => sum + el.x, 0) / selectedElements.length;
    const centerY = selectedElements.reduce((sum, el) => sum + el.y, 0) / selectedElements.length;

    // 构建组合元素
    const groupedElement = {
        type: "group",
        x: centerX,
        y: centerY,
        children: selectedElements.map(el => ({
            char: el.char,
            x: el.x - centerX,
            y: el.y - centerY,
            size: el.size,
            rotation: el.rotation,
            rotationSwing: el.rotationSwing,
            animationHandle: el.animationHandle,
            swingSpeed: el.swingSpeed,
            swingPhaseOffset: el.swingPhaseOffset,
            isSwinging: el.isSwinging,
            isRotating: el.isRotating,
            isScaling: el.isScaling,
            isMoving: el.isMoving
        }))

    };

    // 删除原始元素
    selectedIndices.sort((a, b) => b - a).forEach(index => elements.splice(index, 1));

    // 添加组合元素
    elements.push(groupedElement);
    selectedIndex = elements.length - 1;
    selectedIndices = [selectedIndex];
    dragIndex = selectedIndex;

    // 重新绘制
    drawAll();
});


document.getElementById("sendToBackBtn").addEventListener("click", () => {
    if (selectedIndex !== null && selectedIndex >= 0) {
        const [selected] = elements.splice(selectedIndex, 1);
        elements.unshift(selected); // 插入数组开头（底层）
        selectedIndex = 0;
        drawAll();
    }
});

// 粘贴剪贴板 emoji
document.getElementById("pasteBtn").addEventListener("click", async () => {
    if (!navigator.clipboard) {
        alert("剪贴板功能不可用，请使用支持的浏览器");
        return;
    }

    try {
        const text = await navigator.clipboard.readText();
        const icons = extractIcons(text); // 假设返回 emoji 字符数组

        if (icons.length === 0) {
            alert("剪贴板中未检测到 emoji 图案");
            return;
        }

        // 🎯 替换选中元素（红框显示）
        const targetIndices = [];
        if (typeof selectedIndex === "number") targetIndices.push(selectedIndex);
        if (typeof dragIndex === "number" && dragIndex !== selectedIndex) targetIndices.push(dragIndex);

        if (targetIndices.length > 0) {
            icons.forEach((emoji, i) => {
                const target = elements[targetIndices[i % targetIndices.length]];
                if (target) target.char = emoji;
            });
        } else {
            addIcons(icons); // 默认行为：粘贴到画布
        }

        const input = document.getElementById("yourInputId");
        if (input) input.value = "";

        drawAll(); // 🖼 刷新画布显示
    } catch (err) {
        console.error("剪贴板读取失败:", err);
        alert("无法访问剪贴板，请确保你已点击授权并使用受支持的浏览器（如 Chrome 最新版本）");
    }
});

