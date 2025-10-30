// 等待整个DOM加载完成后再执行
document.addEventListener('DOMContentLoaded', () => {
    // 绑定第一个按钮
    const backHomeBtn = document.getElementById('backHome');
    if (backHomeBtn) { // 加判断避免找不到元素报错
        backHomeBtn.addEventListener('click', () => {
            window.location.href = './index.html';
        });
    }



    // 绑定第三个按钮
    const biosBtn = document.getElementById('bios');
    if (biosBtn) {
        biosBtn.addEventListener('click', () => {
            window.location.href = "./bios.html"; // 当前页面跳转
        });
    }
    //
    const objectBtn = document.getElementById('object');
    if (objectBtn) {
        objectBtn.addEventListener('click', () => {
            window.location.href = "./objects.html"; // 当前页面跳转
        });
    }
        const knowledgeBtn = document.getElementById('knowledge');
    if (knowledgeBtn) {
        knowledgeBtn.addEventListener('click', () => {
            window.location.href = "./knowledge.html"; // 当前页面跳转
        });
    }
    // 绑定第二个按钮
    const opennewBtn = document.getElementById('opennew');
    if (opennewBtn) {
        opennewBtn.addEventListener('click', () => {
            window.open("https://aj300542.github.io/download.html", "_blank");
        });
    }
});
