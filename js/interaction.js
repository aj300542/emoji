
// interaction.js




// 鼠标按下
canvas.addEventListener("mousedown", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    if (e.ctrlKey || e.metaKey) {
        selectionBox = { startX: mx, startY: my, endX: mx, endY: my };
        return;
    }

    selectedIndex = null;
    selectedIndices = [];
    dragging = false;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;
        if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
            selectedIndex = i;
            selectedIndices = [i];
            dragIndex = i;
            offsetX = mx - el.x;
            offsetY = my - el.y;
            dragging = true;
            break;
        }
    }

    drawAll();
});

canvas.addEventListener("mousemove", (e) => {
    if (selectionBox) {
        selectionBox.endX = e.offsetX;
        selectionBox.endY = e.offsetY;
        drawAll(); // 在 drawAll 中添加框绘制
    }
});
canvas.addEventListener("mouseup", () => {
    if (selectionBox) {
        const x1 = Math.min(selectionBox.startX, selectionBox.endX);
        const x2 = Math.max(selectionBox.startX, selectionBox.endX);
        const y1 = Math.min(selectionBox.startY, selectionBox.endY);
        const y2 = Math.max(selectionBox.startY, selectionBox.endY);

        selectedIndices = [];

        elements.forEach((el, i) => {
            if (el.x > x1 && el.x < x2 && el.y > y1 && el.y < y2) {
                selectedIndices.push(i);
            }
        });

        selectionBox = null;
        drawAll();
        return;

    }

    dragging = false;
    dragIndex = null;
});
// 鼠标移动
canvas.addEventListener("mousemove", (e) => {
    if (!dragging || dragIndex === null) return;

    const mx = e.offsetX;
    const my = e.offsetY;
    const el = elements[dragIndex];

    if (el.type === "group") {
        // 群组使用累计偏移 dx/dy
        const dx = mx - offsetX;
        const dy = my - offsetY;
        el.x += dx;
        el.y += dy;
        offsetX = mx;
        offsetY = my;
    } else {
        // 普通元素使用鼠标位置减去初始偏移量
        el.x = mx - offsetX;
        el.y = my - offsetY;
    }

    drawAll();
});
canvas.addEventListener("mousedown", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    if (e.ctrlKey || e.metaKey) {
        selectionBox = { startX: mx, startY: my, endX: mx, endY: my };
        return;
    }

    selectedIndex = null;
    selectedIndices = [];
    dragging = false;
    dragIndex = null;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];

        if (el.type === "group") {
            // 基于所有子元素计算群组的边界包围盒
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx;
                offsetY = my;
                dragging = true;
                break;
            }
        } else {
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx - el.x;
                offsetY = my - el.y;
                dragging = true;
                break;
            }
        }
    }

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
    const delta = e.deltaY < 0 ? 0.1 : -0.1; // 控制缩放幅度

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];

        if (el.type === "group") {
            // ✅ 检测鼠标是否在群组包围盒范围内
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                // ✅ 缩放整个群组：更新子元素尺寸、位置、父级缩放值
                el.scale = Math.max(0.2, el.scale + delta);

                el.children.forEach(child => {
                    child.size = Math.max(10, child.size * (1 + delta));
                    child.x *= (1 + delta);
                    child.y *= (1 + delta);
                });

                drawAll();
                break;
            }
        } else {
            // ✅ 普通元素缩放
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                el.size = Math.max(20, el.size + delta * 60); // 放大倍数更明显
                drawAll();
                break;
            }
        }
    }
});

// 删除 & 取消选中 & 旋转
window.addEventListener("keydown", (e) => {
    // 删除选中元素
    if (e.key === "Delete" && selectedIndex !== null) {
        elements.splice(selectedIndex, 1);
        selectedIndex = null;
        drawAll();
        return;
    }

    // 取消选中
    if (e.key === "Escape") {
        selectedIndex = null;
        drawAll();
        return;
    }

    // 旋转选中元素（包含群组）
    if (selectedIndex !== null) {
        const el = elements[selectedIndex];
        const rotateStep = Math.PI / 18;
        if (e.key === "ArrowLeft") {
            el.rotation = (el.rotation || 0) - rotateStep;
            drawAll();
        }

        if (e.key === "ArrowRight") {
            el.rotation = (el.rotation || 0) + rotateStep;
            drawAll();
        }
        if (el.type === "group" && el.children) {
            const rotateStep = Math.PI / 18;
            el.rotation = (el.rotation || 0) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);

            // 🧠 计算群组真实中心点（基于子元素坐标）
            let sumX = 0, sumY = 0;
            el.children.forEach(child => {
                sumX += child.x;
                sumY += child.y;
            });
            const cx = sumX / el.children.length;
            const cy = sumY / el.children.length;

            // 🎯 绕群组中心旋转每个子元素
            el.children.forEach(child => {
                const dx = child.x - cx;
                const dy = child.y - cy;
                const angle = Math.atan2(dy, dx) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);
                const dist = Math.hypot(dx, dy);
                child.x = cx + dist * Math.cos(angle);
                child.y = cy + dist * Math.sin(angle);
                child.rotation = (child.rotation || 0) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);
            });
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

        if (el.type === "group") {
            // 计算群组的包围盒
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            // 检查鼠标是否在群组范围内
            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                const [selected] = elements.splice(i, 1);
                elements.push(selected); // 置顶
                selectedIndex = elements.length - 1;
                drawAll();
                break;
            }

        } else {
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                const [selected] = elements.splice(i, 1);
                elements.push(selected); // 置顶
                selectedIndex = elements.length - 1;
                drawAll();
                break;
            }
        }
    }
});




