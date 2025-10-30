document.addEventListener('DOMContentLoaded', () => {
    // 动态获取基础路径：本地运行时为 ''，GitHub 上为 '/emoji'
    const basePath = window.location.pathname.includes('/emoji/') ? '/emoji' : '';

    // 绑定返回主页按钮
    const backHomeBtn = document.getElementById('backHome');
    if (backHomeBtn) {
        backHomeBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/index.html`;
        });
    }

    // 绑定 bios 按钮
    const biosBtn = document.getElementById('bios');
    if (biosBtn) {
        biosBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/bios.html`;
        });
    }

    // 绑定 object 按钮
    const objectBtn = document.getElementById('object');
    if (objectBtn) {
        objectBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/objects.html`;
        });
    }

    // 绑定 knowledge 按钮
    const knowledgeBtn = document.getElementById('knowledge');
    if (knowledgeBtn) {
        knowledgeBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/knowledge.html`;
        });
    }

    // 绑定新窗口打开按钮（无需修改，链接是完整 URL）
    const opennewBtn = document.getElementById('opennew');
    if (opennewBtn) {
        opennewBtn.addEventListener('click', () => {
            window.open("https://aj300542.github.io/download.html", "_blank");
        });
    }
});