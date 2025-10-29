import * as THREE from 'three';
import { MTLLoader } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/loaders/MTLLoader.js';
import { OBJLoader } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/loaders/OBJLoader.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.150.1/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'RoomEnvironment';

/* -------------------------
   Canvas setup
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

/* -------------------------
   Three.js state
   ------------------------- */
let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let pivots = [];
let helpers = [];
let animationFrameId = null;

/* -------------------------
   Utility
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

    // Expose for console debugging after init
    window.__emojiScene = scene;
    window.__emojiCamera = camera;
    window.__emojiRenderer = renderer;

    // Expose THREE globally so Console can use constructors directly
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
   Disposal
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
   Material fix
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

        if (geom && !geom.attributes.normal) {
            try { geom.computeVertexNormals(); } catch (e) { console.warn('computeVertexNormals failed', e); }
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

        // conservative face detection
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

/* -------------------------
   Load and handle OBJ
   ------------------------- */
function handleLoadedObject(object, code, index) {
    if (!scene) return;

    forceVisibleMaterialsAndNormals(object);

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

    // add BoxHelper for debugging
    object.traverse(child => {
        if (child.isMesh) {
            try {
                const bh = new THREE.BoxHelper(child, 0xff0000);
                bh.renderOrder = 10;
                scene.add(bh);
                helpers.push(bh);
            } catch (e) { /* ignore */ }
        }
    });

    // position camera to fit all pivots
    const fullGroup = new THREE.Group();
    pivots.forEach(p => fullGroup.add(p));
    const fullBox = new THREE.Box3().setFromObject(fullGroup);
    const fullCenter = fullBox.getCenter(new THREE.Vector3());
    const fullSize = fullBox.getSize(new THREE.Vector3()).length() || 1;
    const z = Math.max(1.5, fullSize * 1.8 + 2);

    camera.near = 0.0005;
    camera.far = 5000;
    camera.updateProjectionMatrix();
    camera.position.set(fullCenter.x, fullCenter.y, z);
    camera.lookAt(fullCenter);
    controls.target.copy(fullCenter);
    controls.update();
}

/* -------------------------
   Load sequence
   ------------------------- */
function loadEmojiSequence(codes) {
    const filtered = codes.filter(c => c !== 'U+200D' && c !== 'U+FE0F');
    if (filtered.length === 0) return;

    const fallbackMaterial = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        specular: 0x666666,
        shininess: 30,
        side: THREE.DoubleSide
    });

    filtered.forEach((code, index) => {
        const mtlPath = `../emoji_export/${code}/${code}.mtl`;
        const objPath = `../emoji_export/${code}/${code}.obj`;

        const mtlLoader = new MTLLoader();
        mtlLoader.load(mtlPath, (materials) => {
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

            const objLoader = new OBJLoader();
            objLoader.setMaterials(materials);
            objLoader.load(objPath, (object) => {
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
            });
        });
    });
}


/* -------------------------
   Animation loop
   ------------------------- */
function animate() {
    cancelAnimationFrame(animationFrameId);
    function loop() {
        animationFrameId = requestAnimationFrame(loop);
        pivots.forEach(p => { p.rotation.y += 0.005; });
        controls && controls.update();
        renderer && scene && camera && renderer.render(scene, camera);
    }
    loop();
}
/* -------------------------
   Hover binding and DOM watch
   ------------------------- */
function bindItemHover(item) {
    if (item.__emojiBound) return;
    item.__emojiBound = true;

    item.addEventListener('mouseenter', () => {
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
    });

    item.addEventListener('mouseleave', () => {
        clearSceneKeepRenderer();
        if (canvas) canvas.style.display = 'none';
        cancelAnimationFrame(animationFrameId);
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
    // safety: stop observing after a short while
    setTimeout(() => { bindExistingItems(); try { mo.disconnect(); } catch (e) {} }, 5000);
}

/* -------------------------
   Single #emoji support (optional)
   ------------------------- */
function bindSingleEmoji() {
    const singleEmojiEl = document.getElementById('emoji');
    if (!singleEmojiEl) return false;

    singleEmojiEl.addEventListener('mouseenter', () => {
        const emojiChar = singleEmojiEl.textContent.trim();
        if (!emojiChar) return;
        const visibleCodes = getEmojiCodeSequence(emojiChar).filter(c => c !== 'U+200D' && c !== 'U+FE0F');
        if (canvas) canvas.style.display = 'block';
        clearSceneKeepRenderer();
        if (!scene) initThree();
        loadEmojiSequence(visibleCodes);
        animate();
    });

    singleEmojiEl.addEventListener('mouseleave', () => {
        clearSceneKeepRenderer();
        if (canvas) canvas.style.display = 'none';
        cancelAnimationFrame(animationFrameId);
    });

    return true;
}

/* -------------------------
   DOM ready init
   ------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    if (!bindSingleEmoji()) {
        if (!bindExistingItems()) {
            watchForItems();
            console.log('No #emoji found; watching for .item insertion');
        }
    }
});

/* -------------------------
   Debug helpers exposed to console
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

/* -------------------------
   Resize listener (redundant safe)
   ------------------------- */
window.addEventListener('resize', onWindowResize);

/* -------------------------
   End of emojiobjCC.js
   ------------------------- */
