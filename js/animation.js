let initialStates = [];

function saveInitialStates() {
    initialStates = elements.map(el => ({
        x: el.x,
        y: el.y,
        rotation: el.rotation, // ✅ 旋转角度
        scale: el.scale,       // ✅ 缩放比例
        size: el.size          // ✅ 元素尺寸
    }));
    console.log("✅ 已记录全部初始状态，包括位置、旋转、缩放、尺寸");
}

function restoreInitialStates() {
    if (initialStates.length === 0) {
        console.warn("⚠️ 尚未记录初始状态");
        return;
    }

    elements.forEach((el, index) => {
        const init = initialStates[index];
        el.x = init.x;
        el.y = init.y;
        el.rotation = init.rotation;
        el.scale = init.scale;
        el.size = init.size; // ✅ 恢复尺寸
    });

    drawAll();
    console.log("🔁 已恢复全部初始状态，包括尺寸");
}

canvas.addEventListener("contextmenu", (e) => {
    e.preventDefault(); // 阻止默认右键菜单

    // 若有选中或拖拽的元素，先反转旋转方向
    const targetIndices = [];
    if (typeof selectedIndex === "number") targetIndices.push(selectedIndex);
    if (typeof dragIndex === "number" && dragIndex !== selectedIndex) targetIndices.push(dragIndex);

    targetIndices.forEach(index => {
        const el = elements[index];
        if (!el) return;

        // 🔄 反转方向
        if (el.isRotating) {
            el.rotationSpeed = -el.rotationSpeed;
            console.log(`🌀 元素 ${index} 旋转方向已反转`);
        }
    });

    // ✅ 再取消选中状态
    selectedIndex = null;
    dragIndex = null;
    console.log("🚫 已取消所有选中状态");

    drawAll(); // 刷新画布
});



function fillSelectedElement() {
    const targetIndex = selectedIndex !== -1 ? selectedIndex : dragIndex;
    const el = elements[targetIndex];
    if (!el) return;

    // 💡 设置画布大小参数
    const maxDimension = Math.max(canvas.width, canvas.height);

    el.size = maxDimension; // 字体大小设为最大边长
    el.x = canvas.width / 2;
    el.y = canvas.height / 2;

    drawAll();
}

// ✨ 全局定义：统一节奏控制（例如 120 BPM）
const bpm = 120;
const beatDuration = 60000 / bpm; // 每拍毫秒
const framesPerBeat = Math.round(beatDuration / (1000 / 60)); // 拍对应帧数（60fps）

function easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

// 💫 节拍触发机制
let beatStep = 0;
setInterval(() => {
    beatStep++;
}, beatDuration);

// 🎶 位移动画：踩拍跳跃
function animateMoveForSelected() {
    elements.forEach((el, i) => {
        if ((i === selectedIndex || i === dragIndex) && !el.isMoving) {
            el.isMoving = true;
            animateSingle(el);
        }
    });
}

function animateSingle(el) {
    const dx = (Math.random() - 0.5) * 100;
    const dy = (Math.random() - 0.5) * 50;
    const frames = framesPerBeat;
    let step = 0;
    const startX = el.x;
    const startY = el.y;

    function moveStep() {
        if (!el.isMoving) return; // 可中止
        if (step < frames) {
            const t = easeInOutQuad(step / frames);
            el.x = startX + dx * t;
            el.y = startY + dy * t;
            drawAll();
            step++;
            el.animationHandle = requestAnimationFrame(moveStep); // ⬅️ 保存动画句柄
        } else {
            // 清除句柄以便下一次动画不会残留
            el.animationHandle = null;

            // 循环触发新的移动动画（节拍跳动）
            if (el.isMoving) {
                setTimeout(() => animateSingle(el), beatDuration);
            }
        }
    }

    el.animationHandle = requestAnimationFrame(moveStep); // ⬅️ 初次记录句柄
}

let globalStep = 0;

// 🧱 初始化所有元素
elements.forEach(el => {
    el.rotationBase = 0;   // 由旋转控制
    el.rotationSwing = 0;  // 由摇摆控制
    el.rotation = 0;       // 总合用于绘制（可选）
});

// 🎯 摇摆启动函数（作用于全部元素）
function startSwingForSelected() {
    elements.forEach((el, i) => {
        if ((i === selectedIndex || i === dragIndex) && !el.isSwinging) {
            el.swingSpeed = 6 + Math.random() * 6;
            el.swingPhaseOffset = Math.random() * Math.PI * 2;
            el.isSwinging = true;
            animateSwingLoop(el);
        }
    });
}

// 🌀 摇摆动画函数
function animateSwingLoop(el) {
    const maxAngle = Math.PI / 12;

    function swingStep() {
        if (!el.isSwinging) return; // 可中止

        const phase = el.swingPhaseOffset || 0;
        const speed = el.swingSpeed || 10;
        el.rotationSwing = Math.sin(phase + globalStep / speed) * maxAngle;

        drawAll();
        globalStep += 0.2;

        // 👉 记录句柄，供 cancelAnimationFrame 使用
        el.animationHandle = requestAnimationFrame(swingStep);
    }

    // 初始帧
    el.animationHandle = requestAnimationFrame(swingStep);
}

function startRotationForSelected() {
    elements.forEach((el, i) => {
        if ((i === selectedIndex || i === dragIndex) && !el.isRotating) {
            el.rotationSpeed = Math.random() * 0.02 + 0.01; // 每帧旋转速度（弧度）
            el.isRotating = true; // 防止重复调用
            animateRotateLoop(el);
        }
    });
}

function animateRotateLoop(el) {
    function step() {
        if (!el.isRotating) return;

        el.rotationBase = (el.rotationBase || 0) + el.rotationSpeed;
        drawAll();
        requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
}

// 🔊 缩放动画：放大并回弹，按深度同步节奏
function startScaleForSelected() {
    elements.forEach((el, i) => {
        if ((i === selectedIndex || i === dragIndex) && !el.isScaling) {
            el.baseSize = el.size;
            el.depthRatio = (elements.length - i) / elements.length;
            el.shouldLoopScale = true;
            animateScaleLoop(el);
        }
    });
}

function animateScaleLoop(el) {
    if (el.isScaling) return;
    el.isScaling = true;

    let step = 0;
    const frames = Math.round(framesPerBeat * (1 + el.depthRatio));
    const amplitude = (0.2 + Math.random() * 0.2) * el.depthRatio;
    const direction = Math.random() < 0.5 ? 1 : -1;
    const beatPause = beatDuration * 0.3; // 🕒 节奏间隔（可调节）

    function scaleStep() {
        if (!el.shouldLoopScale) {
            el.isScaling = false;
            el.scaleHandle = null;
            return;
        }

        if (step < frames) {
            const factor = 1 + direction * amplitude * Math.sin((Math.PI * step) / frames);
            el.size = el.baseSize * factor;
            drawAll();
            step++;
            el.scaleHandle = requestAnimationFrame(scaleStep);
        } else {
            step = 0;
            // ⏱️ 节奏间隔控制：轻微停顿后再进入下一循环
            el.scaleHandle = setTimeout(() => {
                el.scaleHandle = requestAnimationFrame(scaleStep);
            }, beatPause);
        }
    }

    scaleStep();
}


function flipSelfHorizontal() {
    elements.forEach((el, i) => {
        if (i === selectedIndex || i === dragIndex) {
            el.isFlipped = !el.isFlipped;
            el.rotation = -el.rotation;          // ⏪ 翻转旋转方向
            el.x = canvas.width - el.x;          // 📍 镜像位置（以画布中线为基准）
        }
    });
    drawAll();
}

function stopAnimationForSelected() {
    const targetIndices = [];
    if (typeof selectedIndex === "number") targetIndices.push(selectedIndex);
    if (typeof dragIndex === "number" && dragIndex !== selectedIndex) targetIndices.push(dragIndex);

    targetIndices.forEach(index => {
        const el = elements[index];
        if (!el) return;

        el.isSwinging = false;
        el.isRotating = false;
        el.isScaling = false;
        el.isMoving = false;

        // 清除 requestAnimationFrame 或 setTimeout
        if (el.animationHandle) {
            cancelAnimationFrame(el.animationHandle);
            el.animationHandle = null;
        }

        if (el.scaleHandle) {
            cancelAnimationFrame(el.scaleHandle); // 或 clearTimeout，根据 animateScaleLoop 的使用方式决定
            el.scaleHandle = null;
        }

        // 可选恢复初始状态
        if (el.resetOnStop) {
            restoreInitialStates();
        }
    });

    drawAll(); // 重绘画面
}

