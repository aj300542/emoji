const canvas = document.getElementById("iconCanvas");
const ctx = canvas.getContext("2d");
const input = document.getElementById("iconInput");
let elements = [];
let dragging = false;
let dragIndex = null;
let selectedIndex = null;
let offsetX = 0, offsetY = 0;

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

    elements.forEach((el, i) => {
        const rotation = (el.rotationBase || 0) + (el.rotationSwing || 0) + (el.rotation || 0);
        const scaleX = (el.isFlipped ? -1 : 1) * (el.scale || 1);
        const scaleY = el.scale || 1;

        ctx.save();
        ctx.translate(el.x, el.y);
        ctx.scale(scaleX, scaleY); // 💫 支持翻转 + 缩放
        ctx.rotate(rotation);

        ctx.font = `${el.size}px "SegoeEmojiOld", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        ctx.shadowColor = "rgba(0, 0, 0, 0.2)";
        ctx.shadowBlur = 4;
        ctx.fillText(el.char, 0, 0);
        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;

        if (i === selectedIndex || i === dragIndex) {
            ctx.strokeStyle = "red";
            ctx.lineWidth = 2;
            const padding = 4;
            ctx.strokeRect(-el.size / 2 - padding, -el.size / 2 - padding, el.size + padding * 2, el.size + padding * 2);
        }

        ctx.restore();
    });
}




// 鼠标按下
canvas.addEventListener("mousedown", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;
    selectedIndex = null;
    dragging = false;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;
        if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
            selectedIndex = i;
            dragIndex = i;
            offsetX = mx - el.x;
            offsetY = my - el.y;
            dragging = true;
            break;
        }
    }

    drawAll();
});

// 鼠标移动
canvas.addEventListener("mousemove", (e) => {
    if (!dragging || dragIndex === null) return;
    const mx = e.offsetX, my = e.offsetY;
    elements[dragIndex].x = mx - offsetX;
    elements[dragIndex].y = my - offsetY;
    drawAll();
});

// 鼠标抬起
canvas.addEventListener("mouseup", () => {
    dragging = false;
    dragIndex = null;
});

// 滚轮缩放
canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const mx = e.offsetX;
    const my = e.offsetY;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;
        if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
            const delta = e.deltaY < 0 ? 6 : -6;
            el.size = Math.max(20, el.size + delta);
            drawAll();
            break;
        }
    }
});

// 删除 & 取消选中 & 旋转
window.addEventListener("keydown", (e) => {
    if (e.key === "Delete" && selectedIndex !== null) {
        elements.splice(selectedIndex, 1);
        selectedIndex = null;
        drawAll();
    }

    if (e.key === "Escape") {
        selectedIndex = null;
        drawAll();
    }

    if (selectedIndex !== null) {
        const el = elements[selectedIndex];
        if (e.key === "ArrowLeft") {
            el.rotation -= Math.PI / 18; // 左旋转 10°
            drawAll();
        }
        if (e.key === "ArrowRight") {
            el.rotation += Math.PI / 18; // 右旋转 10°
            drawAll();
        }
    }
});

// 双击置顶
canvas.addEventListener("dblclick", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;
        if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
            const [selected] = elements.splice(i, 1);
            elements.push(selected);
            selectedIndex = elements.length - 1;
            drawAll();
            break;
        }
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


