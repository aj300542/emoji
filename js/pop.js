document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("gallery");
  let popupTimer = null; // ⏱️ 用于记录当前的定时器

  container.querySelectorAll(".item").forEach((el, index) => {
    el.setAttribute("data-index", index);
    el.addEventListener("click", () => {
      const clickedItem = objectItems[index];

      const popup = document.getElementById("popup");
      const popupIcon = document.getElementById("popup-icon");
      const popupName = document.getElementById("popup-name");

      popupIcon.textContent = clickedItem.icon;
      popupName.textContent = clickedItem.name;
      popup.style.transform = "translate(-50%, -50%) scale(1)";

      const contentToCopy = `${clickedItem.icon} ${clickedItem.name}`;
      navigator.clipboard.writeText(contentToCopy)
        .then(() => console.log("已复制到剪贴板:", contentToCopy))
        .catch(err => console.error("复制失败:", err));

      // 🔄 如果已有定时器，则清除它
      if (popupTimer) clearTimeout(popupTimer);

      // ⏲️ 启动新的定时器
      popupTimer = setTimeout(() => {
        popup.style.transform = "translate(-50%, -50%) scale(0)";
        popupTimer = null;
      }, 1000);
    });
  });
});
// 监听 gallery 中所有 .item 的 emoji 双击事件
document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.getElementById('gallery');

  // 使用事件委托监听 .char 的双击
  gallery.addEventListener('dblclick', (event) => {
    const target = event.target;
    if (target.classList.contains('char')) {
      const emoji = target.textContent.trim();
      const encoded = encodeURIComponent(emoji);
      // 跳转到根目录下的 download.html
    const isGitHubPages = window.location.hostname === 'aj300542.github.io';
    // 线上用绝对路径，本地用相对路径（../ 跳出 bios 目录）
    const path = isGitHubPages ? '/emoji/downloadobj.html' : '../downloadobj.html';
    window.location.href = `${path}?emoji=${encoded}`;
    }
  });
});
