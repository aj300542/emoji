import * as THREE from 'three';
import { MTLLoader } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/loaders/MTLLoader.js';
import { OBJLoader } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/loaders/OBJLoader.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/environments/RoomEnvironment.js';

/* -------------------------
   加载进度条和错误提示 DOM
   ------------------------- */
function createUIElements() {
    // 创建进度条（保持原有代码）
    let progressContainer = document.getElementById('emoji-loading');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'emoji-loading';
        progressContainer.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            background: rgba(0,0,0,0.7);
            padding: 20px 30px;
            border-radius: 8px;
            color: white;
            font-family: sans-serif;
        `;

        const progressBarBg = document.createElement('div');
        progressBarBg.style.cssText = `
            width: 200px;
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
        `;

        const progressBar = document.createElement('div');
        progressBar.id = 'emoji-progress-bar';
        progressBar.style.cssText = `
            width: 0%;
            height: 100%;
            background: #00ffcc;
            transition: width 0.2s ease;
        `;

        const progressText = document.createElement('div');
        progressText.id = 'emoji-progress-text';
        progressText.textContent = '加载中... 0%';
        progressText.style.fontSize = '14px';

        progressBarBg.appendChild(progressBar);
        progressContainer.appendChild(progressBarBg);
        progressContainer.appendChild(progressText);
        document.body.appendChild(progressContainer);
    }

    // 创建错误提示元素
    let errorContainer = document.getElementById('emoji-error');
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.id = 'emoji-error';
        errorContainer.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            display: none;
            background: rgba(0,0,0,0.8);
            color: #ff4444;
            padding: 16px 24px;
            border-radius: 8px;
            font-family: sans-serif;
            max-width: 80%;
            text-align: center;
        `;
        document.body.appendChild(errorContainer);
    }
}

/* -------------------------
   进度和错误管理工具
   ------------------------- */
const loadingManager = {
    total: 0,
    completed: 0,
    missingFiles: [], // 存储缺失的文件

    init(codes) {
        this.total = codes.length * 2;
        this.completed = 0;
        this.missingFiles = [];
        this.showProgress();
        this.updateProgress();
        this.hideError();
    },

    increment() {
        this.completed = Math.min(this.completed + 1, this.total);
        this.updateProgress();
        
        // 全部加载完成后检查是否有缺失文件
        if (this.completed >= this.total) {
            setTimeout(() => {
                this.hideProgress();
                if (this.missingFiles.length > 0) {
                    this.showError(`部分模型文件缺失：\n${this.missingFiles.join(', ')}\n\nSEGUIEMJ.TTF没有相关emoji`);
                }
            }, 300);
        }
    },

    addMissingFile(code) {
        if (!this.missingFiles.includes(code)) {
            this.missingFiles.push(code);
        }
    },

    updateProgress() {
        const progress = Math.round((this.completed / this.total) * 100);
        const bar = document.getElementById('emoji-progress-bar');
        const text = document.getElementById('emoji-progress-text');
        if (bar) bar.style.width = `${progress}%`;
        if (text) text.textContent = `加载中... ${progress}%`;
    },

    showProgress() {
        const container = document.getElementById('emoji-loading');
        if (container) container.style.display = 'flex';
    },

    hideProgress() {
        const container = document.getElementById('emoji-loading');
        if (container) container.style.display = 'none';
    },

    showError(message) {
        const container = document.getElementById('emoji-error');
        if (container) {
            container.textContent = message;
            container.style.display = 'block';
            
            // 5秒后自动隐藏错误提示
            setTimeout(() => this.hideError(), 5000);
        }
    },

    hideError() {
        const container = document.getElementById('emoji-error');
        if (container) container.style.display = 'none';
    },

    reset() {
        this.total = 0;
        this.completed = 0;
        this.missingFiles = [];
        this.hideProgress();
        this.hideError();
    }
};

/* -------------------------
   Canvas 初始化
   ------------------------- */
let canvas = document.getElementById('three-canvas');
if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'three-canvas';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '9999';
    canvas.style.display = 'none';
    document.body.appendChild(canvas);
}

const singleEmojiEl = document.getElementById('emoji') || null;
const codeDisplay = document.getElementById('code') || null;

/* -------------------------
   Three.js 状态管理
   ------------------------- */
let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let pivots = [];
let helpers = [];
let animationFrameId = null;

/* -------------------------
   工具函数
   ------------------------- */
function getEmojiCodeSequence(emojiChar) {
    return [...emojiChar].map(c => 'U+' + c.codePointAt(0).toString(16).toUpperCase());
}

function initThree() {
    if (scene) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 0, 5);

    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x000000, 0);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const envMap = pmremGenerator.fromScene(new RoomEnvironment(), 0.2).texture;
    scene.environment = envMap;

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.5);
    scene.add(hemi);

    const rimLight = new THREE.DirectionalLight(0xffffff, 1);
    rimLight.position.set(10, 10, 5);
    rimLight.castShadow = true;
    rimLight.shadow.mapSize.width = 1024;
    rimLight.shadow.mapSize.height = 1024;
    rimLight.shadow.camera.near = 0.5;
    rimLight.shadow.camera.far = 50;
    scene.add(rimLight);

    const fillLight = new THREE.PointLight(0xffffff, 0.8);
    fillLight.position.set(-5, 5, 5);
    scene.add(fillLight);

    const ground = new THREE.Mesh(
        new THREE.PlaneGeometry(20, 20),
        new THREE.ShadowMaterial({ opacity: 0.3 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1;
    ground.receiveShadow = true;
    scene.add(ground);
    window.addEventListener('resize', onWindowResize);

    // 暴露调试接口
    window.__emojiScene = scene;
    window.__emojiCamera = camera;
    window.__emojiRenderer = renderer;
    window.THREE = THREE;

    console.log('Three initialized. Debug handles: __emojiScene, __emojiCamera, __emojiRenderer, THREE');
}

function onWindowResize() {
    if (!camera || !renderer) return;
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

/* -------------------------
   资源释放
   ------------------------- */
function disposeMaterial(material) {
    if (!material) return;
    if (Array.isArray(material)) {
        material.forEach(disposeMaterial);
        return;
    }
    for (const k in material) {
        const v = material[k];
        if (v && v.isTexture) try { v.dispose(); } catch (e) { }
    }
    if (material.dispose) try { material.dispose(); } catch (e) { }
}

function disposeObject(obj) {
    obj.traverse(child => {
        if (child.isMesh) {
            try { child.geometry && child.geometry.dispose(); } catch (e) { }
            if (child.material) disposeMaterial(child.material);
        }
    });
}

/* -------------------------
   场景清理
   ------------------------- */
function clearSceneKeepRenderer() {
    pivots.forEach(p => {
        try { disposeObject(p); } catch (e) { }
        if (scene) try { scene.remove(p); } catch (e) { }
    });
    pivots = [];

    helpers.forEach(h => {
        try { if (scene) scene.remove(h); } catch (e) { }
        try { h.geometry && h.geometry.dispose && h.geometry.dispose(); } catch (e) { }
        try { h.material && h.material.dispose && h.material.dispose(); } catch (e) { }
    });
    helpers = [];

    console.log('Scene cleared (kept renderer).');
}

/* -------------------------
   材质和法线处理
   ------------------------- */
function forceVisibleMaterialsAndNormals(object, debugEmissive = 0xffffff) {
    const template = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: debugEmissive,
        metalness: 0,
        roughness: 1,
        side: THREE.DoubleSide,
        transparent: false,
        depthTest: true,
        depthWrite: true
    });

    object.traverse(child => {
        if (!child.isMesh) return;

        const geom = child.geometry;

        if (geom) {
            if (!geom.attributes.normal) {
                try { geom.computeVertexNormals(); } catch (e) { console.warn('computeVertexNormals failed', e); }
            }
            if (!geom.attributes.position) {
                console.warn('mesh has no position attribute', child);
            }
        }

        try {
            child.material = template.clone();
            child.material.needsUpdate = true;
        } catch (e) {
            console.warn('material override failed', e);
        }

        child.visible = true;
        child.castShadow = true;
        child.receiveShadow = true;
        child.frustumCulled = false;
        child.renderOrder = 1;
        if (child.material) {
            child.material.side = THREE.DoubleSide;
            child.material.transparent = false;
            child.material.depthTest = true;
            child.material.depthWrite = true;
            child.material.polygonOffset = true;
            child.material.polygonOffsetFactor = -1;
            child.material.polygonOffsetUnits = 1;
        }

        let hasFaces = false;
        if (geom) {
            if (geom.index && geom.index.count > 0) hasFaces = true;
            if (geom.attributes.normal) hasFaces = true;
            if (geom.attributes.uv) hasFaces = true;
        }

        if (!hasFaces) {
            try {
                const geo = child.geometry || new THREE.BoxGeometry(0.5, 0.5, 0.5);
                const wf = new THREE.LineSegments(
                    new THREE.WireframeGeometry(geo),
                    new THREE.LineBasicMaterial({ color: 0x00ff00 })
                );
                wf.renderOrder = 2;
                child.add(wf);
            } catch (e) { console.warn('wireframe fallback failed', e); }

            try {
                if (!child.geometry || !child.geometry.boundingBox || child.geometry.boundingBox.isEmpty()) {
                    const placeholder = new THREE.Mesh(
                        new THREE.BoxGeometry(0.5, 0.5, 0.5),
                        new THREE.MeshBasicMaterial({ color: 0x333333, opacity: 0.12, transparent: true })
                    );
                    placeholder.renderOrder = 0;
                    child.add(placeholder);
                }
            } catch (e) { /* ignore */ }
        }
    });
}

function clearScene() {
    pivots.forEach(p => scene.remove(p));
    pivots = [];
}

function handleLoadedObject(object, code, index) {
    clearScene();

    if (!scene) { disposeObject(object); console.warn('Scene missing, skip', code); return; }
    console.log('✅ 成功加载 OBJ：', code);

    try { forceVisibleMaterialsAndNormals(object, 0xffffff); } catch (e) { console.warn('forceVisibleMaterialsAndNormals error', e); }

    const box = new THREE.Box3().setFromObject(object);
    const center = box.getCenter(new THREE.Vector3());
    let size = box.getSize(new THREE.Vector3()).length();
    if (size === 0) size = 1;

    object.position.sub(center);
    const scaleFactor = Math.max(1, 1.5 / size);
    object.scale.setScalar(scaleFactor);
    object.position.y += 0.25 * scaleFactor;

    const pivot = new THREE.Object3D();
    pivot.add(object);
    pivot.position.x = index * (1.2 * scaleFactor);
    scene.add(pivot);
    pivots.push(pivot);

    object.traverse(child => {
        if (child.isMesh) {
            try {
                const bh = new THREE.BoxHelper(child, 0xff0000);
                bh.renderOrder = 10;
                scene.add(bh);
                helpers.push(bh);
            } catch (e) { console.warn('BoxHelper add failed', e); }
        }
    });

    const fullGroup = new THREE.Group();
    pivots.forEach(p => fullGroup.add(p));
    const fullBox = new THREE.Box3().setFromObject(fullGroup);
    const fullCenter = fullBox.getCenter(new THREE.Vector3());
    const fullSize = fullBox.getSize(new THREE.Vector3()).length();
    const z = Math.max(1.5, fullSize * 1.8 + 2);

    camera.near = 0.001;
    camera.far = 5000;
    camera.updateProjectionMatrix();
    camera.position.set(fullCenter.x, fullCenter.y, z);
    camera.lookAt(fullCenter);
    controls.target.copy(fullCenter);
    controls.update();
}

/* -------------------------
   加载序列（核心改进部分）
   ------------------------- */
function loadEmojiSequence(codes) {
    const filtered = codes.filter(c => c !== 'U+200D' && c !== 'U+FE0F');
    if (filtered.length === 0) return;

    // 初始化加载管理器
    loadingManager.init(filtered);

    const fallbackMaterial = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        specular: 0x666666,
        shininess: 30,
        side: THREE.DoubleSide
    });

    filtered.forEach((code, index) => {
        const isGitHubPages = window.location.hostname === 'aj300542.github.io';
        const basePath = isGitHubPages ? '/emoji/emoji_export/' : '../emoji_export/';
        const mtlPath = `${basePath}${code}/${code}.mtl`;
        const objPath = `${basePath}${code}/${code}.obj`;

        // 先检查文件是否存在（通过HEAD请求）
        const checkFileExists = (url) => {
            return fetch(url, { method: 'HEAD' })
                .then(response => response.ok)
                .catch(() => false);
        };

        // 并行检查MTL和OBJ文件
        Promise.all([
            checkFileExists(mtlPath),
            checkFileExists(objPath)
        ]).then(([mtlExists, objExists]) => {
            if (!mtlExists || !objExists) {
                // 记录缺失的文件
                loadingManager.addMissingFile(code);
                // 仍然增加进度计数，避免进度条卡住
                loadingManager.increment();
                loadingManager.increment();
                console.warn(`文件缺失: ${code} (MTL: ${mtlExists}, OBJ: ${objExists})`);
                return;
            }

            // 文件存在，继续加载
            const mtlLoader = new MTLLoader();
            mtlLoader.load(
                mtlPath,
                (materials) => {
                    materials.preload();

                    for (const key in materials.materials) {
                        const mat = materials.materials[key];
                        if (mat instanceof THREE.MeshPhongMaterial) {
                            mat.specular = new THREE.Color(1, 1, 1);
                            mat.shininess = 8;
                            mat.reflectivity = 0.1;
                            mat.envMap = scene.environment;
                        }
                    }

                    loadingManager.increment();

                    const objLoader = new OBJLoader();
                    objLoader.setMaterials(materials);
                    objLoader.load(
                        objPath,
                        (object) => {
                            object.traverse((child) => {
                                if (child.isMesh) {
                                    child.castShadow = true;
                                    child.receiveShadow = true;
                                }
                            });

                            const box = new THREE.Box3().setFromObject(object);
                            const center = box.getCenter(new THREE.Vector3());
                            const size = box.getSize(new THREE.Vector3()).length();

                            object.position.sub(center);

                            const pivot = new THREE.Object3D();
                            pivot.add(object);
                            pivot.position.x = index * (size + 0.5);
                            scene.add(pivot);
                            pivots.push(pivot);

                            const totalWidth = (filtered.length - 1) * (size + 0.5);
                            camera.position.set(0, 0, totalWidth + 1.75);
                            camera.lookAt(0, 0, 0);
                            controls.target.set(0, 0, 0);
                            controls.update();

                            loadingManager.increment();
                        },
                        (xhr) => {
                            const fileProgress = Math.round((xhr.loaded / xhr.total) * 100);
                            console.log(`OBJ ${code} 加载中: ${fileProgress}%`);
                        },
                        (error) => {
                            console.warn(`OBJ 加载失败: ${code}`, error);
                            loadingManager.addMissingFile(code);
                            loadingManager.increment();
                        }
                    );
                },
                (xhr) => {
                    const fileProgress = Math.round((xhr.loaded / xhr.total) * 100);
                    console.log(`MTL ${code} 加载中: ${fileProgress}%`);
                },
                (error) => {
                    console.warn(`MTL 加载失败: ${code}`, error);
                    loadingManager.addMissingFile(code);
                    loadingManager.increment();
                }
            );
        });
    });
}

/* -------------------------
   动画循环
   ------------------------- */
function animate() {
    cancelAnimationFrame(animationFrameId);
    function loop() {
        animationFrameId = requestAnimationFrame(loop);
        pivots.forEach(p => p.rotation.y += 0.005);
        controls && controls.update();
        if (renderer && scene && camera) renderer.render(scene, camera);
    }
    loop();
}

/* -------------------------
   事件绑定
   ------------------------- */
function bindSingleEmoji() {
    if (!singleEmojiEl) return false;
    singleEmojiEl.addEventListener('mouseenter', () => {
        if (canvas) canvas.style.display = 'block';
        clearSceneKeepRenderer();

        const emojiChar = singleEmojiEl.textContent.trim();
        const codeSequence = getEmojiCodeSequence(emojiChar);
        const visibleCodes = codeSequence.filter(code => code !== 'U+200D' && code !== 'U+FE0F');
        if (codeDisplay) codeDisplay.textContent = visibleCodes.join('_');

        if (!scene) initThree();
        loadEmojiSequence(visibleCodes);
        animate();
    });

    singleEmojiEl.addEventListener('mouseleave', () => {
        if (canvas) canvas.style.display = 'none';
        cancelAnimationFrame(animationFrameId);
        clearSceneKeepRenderer();
        loadingManager.reset();
    });

    console.log('Bound single #emoji handlers');
    return true;
}

function bindItemHover(item) {
    if (item.__emojiBound) return;
    item.__emojiBound = true;
    let hoverTimer = null;

    item.addEventListener('mouseenter', () => {
        hoverTimer = setTimeout(() => {
            const charEl = item.querySelector('.char');
            if (!charEl) return;
            const emojiChar = charEl.textContent.trim();
            if (!emojiChar) return;
            const visibleCodes = getEmojiCodeSequence(emojiChar).filter(c => c !== 'U+200D' && c !== 'U+FE0F');

            if (canvas) canvas.style.display = 'block';
            clearSceneKeepRenderer();

            if (!scene) initThree();
            loadEmojiSequence(visibleCodes);
            animate();
        }, 200);
    });

    item.addEventListener('mouseleave', () => {
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }
        clearSceneKeepRenderer();
        if (canvas) canvas.style.display = 'none';
        cancelAnimationFrame(animationFrameId);
        loadingManager.reset();
    });
}

function bindExistingItems() {
    const items = document.querySelectorAll('.item');
    if (items.length > 0) {
        items.forEach(bindItemHover);
        console.log('Bound hover handlers to existing .item elements');
        return true;
    }
    return false;
}

function watchForItems() {
    const root = document.getElementById('gallery') || document.body;
    const mo = new MutationObserver((mutations, observer) => {
        if (bindExistingItems()) {
            observer.disconnect();
        }
    });
    mo.observe(root, { childList: true, subtree: true });
    setTimeout(() => { bindExistingItems(); mo.disconnect(); }, 5000);
}

/* -------------------------
   初始化
   ------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    createUIElements(); // 创建进度条和错误提示
    if (!bindSingleEmoji()) {
        if (!bindExistingItems()) {
            watchForItems();
            console.log('No #emoji found; watching for .item insertion');
        }
    }
});

/* -------------------------
   调试工具
   ------------------------- */
window.__emojiAddTestCube = function () {
    if (!window.__emojiScene || !window.THREE) { console.warn('scene or THREE not ready'); return; }
    const cube = new window.THREE.Mesh(
        new window.THREE.BoxGeometry(1, 1, 1),
        new window.THREE.MeshStandardMaterial({ color: 0x00ffcc, emissive: 0x222222 })
    );
    cube.position.set(0, 0, 0);
    window.__emojiScene.add(cube);
    console.log('test cube added');
};

window.__emojiListMeshes = function () {
    if (!window.__emojiScene) { console.warn('scene not available'); return; }
    window.__emojiScene.traverse(n => {
        if (n.isMesh) {
            console.log(n, 'frustumCulled', n.frustumCulled, 'renderOrder', n.renderOrder,
                'material', n.material && { type: n.material.type, transparent: n.material.transparent, opacity: n.material.opacity },
                'geom attrs', Object.keys(n.geometry.attributes || {}), 'index', !!n.geometry.index);
        }
    });
};

window.addEventListener('resize', onWindowResize);