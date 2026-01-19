/**
 * embedding-engine.js - Neon Brain Semantic Engine with Communication
 */

class WordEmbeddingVisualization {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.composer = null; 
        this.controls = null;
        
        this.wordNodes = [];
        this.wordLabels = [];
        this.connections = [];
        this.signals = []; 
        this.wordData = [];
        
        this.highlightedWords = new Set();
        this.searchQuery = '';
        this.similarityThreshold = 0.55;
        // Raycaster and mouse tracking for hover interactions
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2(-1, -1); // Initialize off-screen
        this.hoveredNode = null;
        this.focusRing = null; // Will be initialized after scene is set up

        this.init();
    }
    
    init() {
        this.setupScene();
        this.setupCamera();
        this.setupRenderer();
        this.setupPostProcessing(); 
        this.setupControls();
        this.setupLighting();
        this.createClouds();
        this.createBlackHoleVoid();
        this.createCosmicEnvironment();
        this.focusRing = this.createFocusRing(); // Initialize focus ring after scene
        this.loadWordEmbeddings();
        this.setupEventListeners();
        this.animate();
    }
    
    setupScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000205); 
        this.scene.fog = new THREE.FogExp2(0x000205, 0.000002);
    }
    
    setupCamera() {
        this.camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 15000);
        this.camera.position.set(600, 400, 800);
    }
    
    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.toneMapping = THREE.ReinhardToneMapping;
        document.getElementById('canvas-container').appendChild(this.renderer.domElement);
    }

    setupPostProcessing() {
        const renderScene = new THREE.RenderPass(this.scene, this.camera);
        
        const bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(window.innerWidth, window.innerHeight),
            2.5,    // STRENGTH: High-intensity bloom for laser beam effect
            0.4,    // RADIUS: How far the glow spreads
            0.01    // THRESHOLD: Low enough for all connections to glow
        );
        
        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(renderScene);
        this.composer.addPass(bloomPass);
    }
    
    setupLighting() {
        this.scene.add(new THREE.AmbientLight(0x4040ff, 0.5));
        const pLight = new THREE.PointLight(0x00f2ff, 2, 2000);
        this.scene.add(pLight);
        
        // Create glowing origin point
        this.createOriginPoint();
    }
    
    createOriginPoint() {
        // Main glowing sphere at origin (0, 0, 0) - Sun Color
        const originGeometry = new THREE.SphereGeometry(12, 32, 32);
        const originMaterial = new THREE.MeshBasicMaterial({
            color: 0xffaa00,  // Sun color (golden yellow-orange)
            emissive: 0xffaa00,
            emissiveIntensity: 10.0,  // Much brighter than other components
            transparent: true,
            opacity: 10.0
        });
        const originSphere = new THREE.Mesh(originGeometry, originMaterial);
        originSphere.position.set(0, 0, 0);
        this.scene.add(originSphere);
        
        // Pulsing ring around origin point
        const ringGeometry = new THREE.BufferGeometry();
        const ringPositions = [];
        const ringCount = 128;
        const ringRadius = 20;
        
        for (let i = 0; i < ringCount; i++) {
            const angle = (i / ringCount) * Math.PI * 2;
            ringPositions.push(
                Math.cos(angle) * ringRadius,
                0,
                Math.sin(angle) * ringRadius
            );
        }
        
        ringGeometry.setAttribute('position', new THREE.Float32BufferAttribute(ringPositions, 3));
        const ringMaterial = new THREE.LineBasicMaterial({
            color: 0x00ffff,
            linewidth: 3,
            transparent: true,
            opacity: 0.9
        });
        const ring = new THREE.LineLoop(ringGeometry, ringMaterial);
        ring.userData = { pulse: 0 };
        this.scene.add(ring);
        this.originRing = ring;
    }

    createBlackHoleVoid() {
        // This is the "shadow" of the black hole
        const geometry = new THREE.SphereGeometry(12, 32, 32);
        const material = new THREE.MeshBasicMaterial({ color: 0x000000 });
        const horizon = new THREE.Mesh(geometry, material);
        this.scene.add(horizon);
    }

    // Helper to create soft circular textures for clouds/nebulae
    createCircleTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 64; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        grad.addColorStop(0, 'rgba(255,255,255,1)');
        grad.addColorStop(0.5, 'rgba(255,255,255,0.3)');
        grad.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0,0,64,64);
        return new THREE.CanvasTexture(canvas);
    }

    addDistantGalaxy(position, color) {
        const group = new THREE.Group();
        group.position.copy(position);

        const particleCount = 2500;
        const geometry = new THREE.BufferGeometry();
        const positions = [];
        const colors = [];
        const galaxyColor = new THREE.Color(color);

        for (let i = 0; i < particleCount; i++) {
            // Spiral math: radius increases with angle
            const angle = Math.random() * Math.PI * 8;
            const radius = 10 + Math.pow(Math.random(), 0.6) * 200;
            
            // Basic spiral with some thickness (y-axis) and randomness
            const x = Math.cos(angle) * radius + (Math.random() - 0.5) * 30;
            const z = Math.sin(angle) * radius + (Math.random() - 0.5) * 30;
            const y = (Math.random() - 0.5) * 15 * (1 - radius/200);

            positions.push(x, y, z);
            const col = galaxyColor.clone().lerp(new THREE.Color(0xffffff), Math.random() * 0.5);
            colors.push(col.r, col.g, col.b);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 2.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.5,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        const points = new THREE.Points(geometry, material);
        group.add(points);
        
        // Tilt the galaxy randomly for realism
        group.rotation.x = Math.random() * Math.PI;
        group.rotation.z = Math.random() * Math.PI;

        this.scene.add(group);
        return group;
    }

    createCosmicEnvironment() {
        const tex = this.createCircleTexture();
        this.exotics = [];

        // 1. ADD DISTANT GALAXIES (Outer Rim)
        const galaxyColors = [0x4444ff, 0xff44ff, 0x00ffff, 0xffaa44];
        for (let i = 0; i < 4; i++) {
            const radius = 5000 + Math.random() * 2000;
            const angle = (i / 4) * Math.PI * 2 + Math.random();
            const pos = new THREE.Vector3(Math.cos(angle) * radius, (Math.random() - 0.5) * 2000, Math.sin(angle) * radius);
            
            const galaxyObj = this.addDistantGalaxy(pos, galaxyColors[i]);
            this.exotics.push({
                obj: galaxyObj,
                type: 'galaxy',
                orbit: { radius, angle, speed: 0.0001 + Math.random() * 0.0002 }
            });
        }

        // 2. ADD PULSARS & MAGNETARS (Mid Rim)
        for (let i = 0; i < 4; i++) {
            const isPulsar = i < 2;
            const radius = 3000 + Math.random() * 1500;
            const angle = Math.random() * Math.PI * 2;
            const yOffset = (Math.random() - 0.5) * 1000;
            const pos = new THREE.Vector3(Math.cos(angle) * radius, yOffset, Math.sin(angle) * radius);
            
            const obj = isPulsar ? this.addPulsar(pos, 0x00ffff) : this.addMagnetar(pos, 0xff3300);
            this.exotics.push({
                obj: obj,
                type: isPulsar ? 'pulsar' : 'magnetar',
                orbit: { radius, angle, speed: 0.0004 + Math.random() * 0.0006, y: yOffset }
            });
        }

        // 3. BACKGROUND NEBULA CLOUDS (Static distant haze)
        const nebulaColors = [0x4400ff, 0xff0088];
        nebulaColors.forEach(color => {
            const geo = new THREE.BufferGeometry();
            const pos = [];
            for(let i=0; i<1700; i++) {
                const r = 5000 + Math.random() * 2000;
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                pos.push(r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
            }
            geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
            const mat = new THREE.PointsMaterial({ size: 220, color: color, map: tex, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, depthWrite: false });
            this.scene.add(new THREE.Points(geo, mat));
        });
    }

    addPulsar(position, color) {
        const group = new THREE.Group();
        group.position.copy(position);

        // Core
        const core = new THREE.Mesh(new THREE.SphereGeometry(80, 32, 32), new THREE.MeshBasicMaterial({ color: 0xffffff }));
        group.add(core);

        // Beams (Top and Bottom)
        const beamGeo = new THREE.CylinderGeometry(2, 50, 1500, 12, 1, true);
        const beamMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
        const topBeam = new THREE.Mesh(beamGeo, beamMat);
        const bottomBeam = topBeam.clone();
        topBeam.position.y = 750;
        bottomBeam.position.y = -750;
        bottomBeam.rotation.x = Math.PI;
        group.add(topBeam, bottomBeam);

        this.scene.add(group);
        return group;
    }

    addMagnetar(position, color) {
        const group = new THREE.Group();
        group.position.copy(position);

        // Glowing core
        const core = new THREE.Mesh(new THREE.SphereGeometry(90, 48, 48), new THREE.MeshBasicMaterial({ color: color }));
        group.add(core);

        // Magnetic Field Lines (Torus rings)
        for(let i=0; i<3; i++) {
            const ring = new THREE.Mesh(
                new THREE.TorusGeometry(80 + i*40, 1, 16, 64),
                new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.2 })
            );
            ring.rotation.x = Math.random() * Math.PI;
            ring.rotation.y = Math.random() * Math.PI;
            group.add(ring);
        }

        this.scene.add(group);
        return group;
    }

    createClouds() {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        const colors = [];
        
        const totalParticles = 300000;
        const innerRadius = 300;  // Start of the glowing disk (leaves space for the hole)
        const outerRadius = 1350; // Edge of the high-energy disk
        
        const colorHot = new THREE.Color(0xffffff); // Inner heat (white)
        const colorMid = new THREE.Color(0xff6600); // Accretion orange
        const colorEdge = new THREE.Color(0x330000); // Cooling outer red

        for (let i = 0; i < totalParticles; i++) {
            // 1. Position Logic: Accretion Disk
            const radius = innerRadius + Math.pow(Math.random(), 2) * (outerRadius - innerRadius);
            const angle = Math.random() * Math.PI * 2;
            
            let x = Math.cos(angle) * radius;
            let z = Math.sin(angle) * radius;
            let y = (Math.random() - 0.5) * (15 * (radius / outerRadius)); // Thin disk

            // 2. Gravitational Lensing Simulation (The "Warped" Look)
            // If the particle is in a certain zone, bend it up/down to create the halo
            if (Math.random() > 0.9) {
                const bend = Math.sin(angle) * radius * 0.5;
                y += bend;
            }

            vertices.push(x, y, z);

            // 3. Color Logic: Thermal Gradient
            const distRatio = (radius - innerRadius) / (outerRadius - innerRadius);
            let col;
            if (distRatio < 0.1) {
                col = colorHot.clone().lerp(colorMid, distRatio * 10);
            } else {
                col = colorMid.clone().lerp(colorEdge, distRatio);
            }
            colors.push(col.r, col.g, col.b);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

        // Create circular texture for spherical particles
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.6, 'rgba(255, 255, 255, 0.8)');
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
        const texture = new THREE.CanvasTexture(canvas);

        const material = new THREE.PointsMaterial({
            size: 2.2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            map: texture,
            sizeAttenuation: true
        });

        this.accretionDisk = new THREE.Points(geometry, material);
        this.scene.add(this.accretionDisk);
    }
    
    async loadWordEmbeddings() {
        try {
            const response = await fetch('embedding-data.json');
            const data = await response.json();
            this.wordData = data.words;
            this.normalizeData(this.wordData);
            
            this.createWordNodes();
            this.createWordLabels();
            this.createSemanticConnections();
            
            this.updateStats();
            document.getElementById('loading').style.display = 'none';
        } catch (e) { console.error(e); }
    }

    createWordNodes() {
        const geometry = new THREE.SphereGeometry(2.5, 16, 16);
        const whatsappGreen = new THREE.Color(0x25D366);

        this.wordData.forEach((wordObj) => {
            const material = new THREE.MeshStandardMaterial({
                color: whatsappGreen,
                roughness: 0.7,
                metalness: 0.2,
                emissive: 0x000000, // Strictly NO glow
                emissiveIntensity: 0
            });
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.set(wordObj.position.x, wordObj.position.y, wordObj.position.z);
            sphere.userData = { word: wordObj.word, categories: wordObj.categories || [] };
            this.scene.add(sphere);
            this.wordNodes.push(sphere);
        });
    }

    getCategoryColor(cat) {
        const colors = { 'media': 0xff00ff, 'hvac': 0x00ffff, 'navigation': 0xffff00, 'control': 0x00ff00 };
        return colors[cat.toLowerCase()] || 0x4444ff;
    }

    createFocusRing() {
        const geometry = new THREE.TorusGeometry(8, 0.2, 16, 100);
        const material = new THREE.MeshBasicMaterial({ 
            color: 0x00f2ff, 
            transparent: true, 
            opacity: 0 
        });
        const ring = new THREE.Mesh(geometry, material);
        this.scene.add(ring);
        return ring;
    }

    createWordLabels() {
        this.wordLabels = [];
        this.wordData.forEach((wordObj, i) => {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = 256;
            canvas.height = 128;

            context.font = 'bold 40px Arial';
            context.textAlign = 'center';
            context.fillStyle = '#25D366'; // WhatsApp Green Text
            context.fillText(wordObj.word, 128, 64);

            const texture = new THREE.CanvasTexture(canvas);
            const material = new THREE.SpriteMaterial({ 
                map: texture, 
                transparent: true,
                depthTest: false, // Ensures words stay visible
                depthWrite: false
            });

            const sprite = new THREE.Sprite(material);
            sprite.position.copy(this.wordNodes[i].position);
            sprite.position.y -= 8;
            sprite.scale.set(15, 7.5, 1); // Normal size
            
            this.scene.add(sprite);
            this.wordLabels.push(sprite);
        });
    }

    createSemanticConnections() {
        this.wordData.forEach((wordObj) => {
            const similar = wordObj.similar_words || [];
            similar.slice(0, 2).forEach(([name, score]) => {
                if (score < this.similarityThreshold) return;
                const target = this.wordData.find(w => w.word === name);
                if (!target) return;

                const points = [new THREE.Vector3(wordObj.position.x, wordObj.position.y, wordObj.position.z),
                                new THREE.Vector3(target.position.x, target.position.y, target.position.z)];
                
                // HDR Neon Glow: High-intensity color for bloom pass to pick up
                const glowColor = new THREE.Color(0x25D366).multiplyScalar(15);
                const mat = new THREE.LineBasicMaterial({ 
                    color: glowColor, 
                    transparent: true, 
                    opacity: 0.8, // High opacity for always-on look
                    blending: THREE.AdditiveBlending, // Lines add brightness where they cross
                    depthWrite: false // Prevents Z-fighting
                });
                const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), mat);
                line.userData = { source: wordObj.word, target: name };
                this.scene.add(line);
                this.connections.push(line);
                
                this.createSignal(points[0], points[1]);
            });
        });
    }

    createSignal(start, end) {
        // Signals are pure white, so they glow easily with low threshold
        const signal = new THREE.Mesh(
            new THREE.SphereGeometry(1.8, 8, 8), 
            new THREE.MeshBasicMaterial({ color: 0xffffff, blending: THREE.AdditiveBlending })
            
        );
        signal.userData = { start, end, progress: Math.random() };
        this.scene.add(signal);
        this.signals.push(signal);
    }

    performSearch() {
        this.highlightedWords.clear();
        const query = this.searchQuery.toLowerCase();
        if (!query) { this.resetHighlighting(); return; }

        this.wordData.forEach(w => {
            const inWord = w.word.toLowerCase().includes(query);
            const inCat = w.categories.some(c => c.toLowerCase().includes(query));
            if (inWord || inCat) {
                this.highlightedWords.add(w.word);
                w.similar_words.forEach(s => this.highlightedWords.add(s[0]));
            }
        });
        this.applyHighlighting();
    }

    applyHighlighting() {
        this.wordNodes.forEach(node => {
            const match = this.highlightedWords.has(node.userData.word);
            node.material.emissiveIntensity = match ? 1.5 : 0.15; // Extreme glow for searched words
            node.material.opacity = match ? 0.8 : 0.05;
            node.scale.setScalar(match ? 3.0 : 0.7);
        });
        this.wordLabels.forEach(label => label.visible = this.highlightedWords.has(label.userData.word));
        this.connections.forEach(line => {
            const match = this.highlightedWords.has(line.userData.from) && this.highlightedWords.has(line.userData.to);
            line.material.opacity = match ? 1.0 : 0.02;// Connections between matches glow bright
             line.material.linewidth = match ? 3 : 1;
        });
    }

    resetHighlighting() {
        this.wordNodes.forEach(node => { 
            node.material.emissiveIntensity = 1.5; 
            node.material.opacity = 0.9; 
            node.scale.setScalar(1); 
        });
        this.wordLabels.forEach(label => label.visible = true);
        this.connections.forEach(line => line.material.opacity = 0.4);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        const time = Date.now() * 0.001;
        
        // Neural Pulse: Subtle breathing effect on all connections
        const pulseIntensity = 0.5 + Math.sin(time * 2) * 0.3; // Cycles between 0.2 and 0.8
        this.connections.forEach(line => {
            // Only pulse if not currently "overloaded" by hover
            if (line.material.opacity < 1.0) {
                line.material.opacity = 0.3 + (pulseIntensity * 0.4);
            }
        });

        // 1. ANIMATE EXOTIC OBJECTS (Galaxies, Pulsars, Magnetars)
        if (this.exotics) {
            this.exotics.forEach(e => {
                // Orbital movement
                e.orbit.angle += e.orbit.speed;
                e.obj.position.x = Math.cos(e.orbit.angle) * e.orbit.radius;
                e.obj.position.z = Math.sin(e.orbit.angle) * e.orbit.radius;
                if (e.orbit.y !== undefined) e.obj.position.y = e.orbit.y; // Maintain vertical offset if set

                // Type-specific animations
                if (e.type === 'pulsar') {
                    e.obj.rotation.y += 0.08; // High speed internal spin
                    // Flicker the beams
                    if (e.obj.children[1]) e.obj.children[1].scale.x = 1 + Math.sin(time * 25) * 0.3;
                    if (e.obj.children[2]) e.obj.children[2].scale.x = 1 + Math.sin(time * 25) * 0.3;
                } else if (e.type === 'magnetar') {
                    e.obj.rotation.z += 0.01;
                    // Rotate the magnetic field rings
                    e.obj.children.forEach((child, i) => { 
                        if (i > 0) child.rotation.y += 0.03; 
                    });
                } else if (e.type === 'galaxy') {
                    // Slow majestic rotation of the galaxy itself
                    e.obj.rotation.y += 0.001;
                }
            });
        }

        // 2. ACCRETION DISK SWIRL
        if (this.accretionDisk) {
            this.accretionDisk.rotation.y += 0.0035;
        }

        // 3. NODE FLOAT ANIMATION
        this.wordNodes.forEach((node, i) => {
            node.position.y += Math.sin(time + i) * 0.05;
        });

        // 4. UPDATE LABELS
        this.wordLabels.forEach((label, i) => {
            if (this.wordNodes[i]) {
                label.position.copy(this.wordNodes[i].position);
                label.position.y -= 12;
            }
        });

        // 5. UPDATE SIGNALS (Communication pulses)
        if (this.signals) {
            this.signals.forEach(s => {
                s.userData.progress += 0.015;
                if (s.userData.progress >= 1) s.userData.progress = 0;
                s.position.lerpVectors(s.userData.start, s.userData.end, s.userData.progress);
            });
        }

        // Check hover intersections each frame
        this.handleHover();

        this.composer.render();
    }

    createGalaxyAtmosphere() {
        // 1. CREATE NODE ACCRETION RINGS
        this.wordNodes.forEach(node => {
            this.addGalaxyRing(node);
        });

        // 2. CREATE CONNECTION NEBULA STREAMS
        this.createConnectionNebula();
    }

    addGalaxyRing(node) {
        const ringCount = 200; // Slightly more particles for better glow
        const geometry = new THREE.BufferGeometry();
        const positions = [];
        const colors = [];
        
        const radius = 12 + Math.random() * 5;
        const colorA = new THREE.Color(0xff6600); // Glowing Orange
        const colorB = new THREE.Color(0xff0000); // Deep Red

        for (let i = 0; i < ringCount; i++) {
            const angle = (i / ringCount) * Math.PI * 2;
            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;
            const y = (Math.random() - 0.5) * 3;
            
            positions.push(x, y, z);
            const lerpColor = colorA.clone().lerp(colorB, Math.random());
            colors.push(lerpColor.r, lerpColor.g, lerpColor.b);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 5.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending,
            depthWrite: false     // Helps with glow transparency
        });

        const ring = new THREE.Points(geometry, material);
        ring.position.copy(node.position);
        ring.rotation.x = Math.random() * Math.PI;
        
        // NEW: Initialize pulse data
        ring.userData = { 
            baseScale: 1.0, 
            pulse: 0, 
            targetNode: node.userData.word 
        };
        
        node.userData.ring = ring;
        this.scene.add(ring);
    }

    createConnectionNebula() {
        const nebulaGeometry = new THREE.BufferGeometry();
        const nebulaPositions = [];
        const nebulaColors = [];
        
        const colorOrange = new THREE.Color(0xff8800);
        const colorRed = new THREE.Color(0xff0000);

        // For every connection, add "dust" particles along the path
        this.connections.forEach(line => {
            const start = line.geometry.attributes.position.array.slice(0, 3);
            const end = line.geometry.attributes.position.array.slice(3, 6);
            
            const vStart = new THREE.Vector3(start[0], start[1], start[2]);
            const vEnd = new THREE.Vector3(end[0], end[1], end[2]);
            
            const particlePerLine = 500; // More particles for denser nebula
            
            for (let i = 0; i < particlePerLine; i++) {
                const t = Math.random();
                const pos = new THREE.Vector3().lerpVectors(vStart, vEnd, t);
                
                // Add "swirl" offset around the line
                pos.x += (Math.random() - 0.5) * 20;
                pos.y += (Math.random() - 0.5) * 20;
                pos.z += (Math.random() - 0.5) * 20;
                
                nebulaPositions.push(pos.x, pos.y, pos.z);
                
                const col = colorRed.clone().lerp(colorOrange, Math.random());
                nebulaColors.push(col.r, col.g, col.b);
            }
        });

        nebulaGeometry.setAttribute('position', new THREE.Float32BufferAttribute(nebulaPositions, 3));
        nebulaGeometry.setAttribute('color', new THREE.Float32BufferAttribute(nebulaColors, 3));

        const nebulaMaterial = new THREE.PointsMaterial({
            size: 2.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending,
            //depthWrite: false
        });

        const nebula = new THREE.Points(nebulaGeometry, nebulaMaterial);
        this.scene.add(nebula);
    }

    normalizeData(words) {
        let minX = Infinity, minY = Infinity, minZ = Infinity, maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
        words.forEach(w => {
            minX = Math.min(minX, w.position.x); minY = Math.min(minY, w.position.y); minZ = Math.min(minZ, w.position.z);
            maxX = Math.max(maxX, w.position.x); maxY = Math.max(maxY, w.position.y); maxZ = Math.max(maxZ, w.position.z);
        });
        const center = new THREE.Vector3((minX+maxX)/2, (minY+maxY)/2, (minZ+maxZ)/2);
        const scale = 500 / Math.max(maxX-minX, maxY-minY, maxZ-minZ);
        words.forEach(w => {
            w.position.x = (w.position.x - center.x) * scale;
            w.position.y = (w.position.y - center.y) * scale;
            w.position.z = (w.position.z - center.z) * scale;
        });
    }
    setupControls() { this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement); this.controls.enableDamping = true; }
    updateStats() { document.getElementById('total-chunks').textContent = this.wordData.length; document.getElementById('connection-count').textContent = this.connections.length; }
    setupEventListeners() {
        document.getElementById('search-box').addEventListener('input', (e) => { this.searchQuery = e.target.value.toLowerCase().trim(); this.performSearch(); });

        // Track mouse position for raycasting
        window.addEventListener('mousemove', (event) => {
            // Convert mouse position to normalized device coordinates (-1 to +1)
            this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        });
    }

    handleHover() {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.wordNodes);

        if (intersects.length > 0) {
            const object = intersects[0].object;

            if (this.hoveredNode !== object) {
                if (this.hoveredNode) this.resetNodeState(this.hoveredNode);

                this.hoveredNode = object;
                const index = this.wordNodes.indexOf(object);
                const label = this.wordLabels[index];

                // 1. Node: Matte 2x Scale (Strictly NO Glow)
                object.scale.setScalar(2.0);
                object.material.emissiveIntensity = 0;

                // 2. Word: 5x Scale + High Glow
                if (label) {
                    label.scale.set(75, 37.5, 1);
                    label.position.copy(object.position);
                    label.position.y += 15;
                    label.material.color.set(0xffffff);
                    label.material.opacity = 1.0;
                }

                // 3. Outstanding Feature: Overload Connections & Send Signals
                this.triggerNeuralActivity(object);
                
                document.body.style.cursor = 'pointer';
            }
        } else {
            if (this.hoveredNode) {
                this.resetNodeState(this.hoveredNode);
                this.hoveredNode = null;
                document.body.style.cursor = 'default';
            }
        }
    }

    triggerNeuralActivity(targetNode) {
        const targetWord = this.wordData[this.wordNodes.indexOf(targetNode)].word;
        
        // HDR overload: Extreme brightness for active connections
        const activeGlow = new THREE.Color(0x25D366).multiplyScalar(50);
        const dimGlow = new THREE.Color(0x25D366).multiplyScalar(5);

        this.connections.forEach(line => {
            if (line.userData.source === targetWord || line.userData.target === targetWord) {
                // Maximum overload state: bright white core with intense green aura
                line.material.color.set(activeGlow);
                line.material.opacity = 1.0;
                
                // Spawn data spark along the neural pathway
                this.spawnSignal(line);
            } else {
                // Unrelated lines dim but stay visible (tunnel vision effect)
                line.material.color.set(dimGlow);
                line.material.opacity = 0.2;
            }
        });
    }

    spawnSignal(line) {
        const points = line.geometry.attributes.position.array;
        const start = new THREE.Vector3(points[0], points[1], points[2]);
        const end = new THREE.Vector3(points[3], points[4], points[5]);

        // Reduced brightness: smaller particle size and dimmer color
        const sparkGeo = new THREE.SphereGeometry(0.3, 8, 8); // Reduced from 0.8
        const sparkMat = new THREE.MeshBasicMaterial({ 
            color: new THREE.Color(0xffffff).multiplyScalar(0.3), // Reduced from full white (1.0)
            transparent: true,
            opacity: 0.3 // Slightly transparent for softer glow
        });
        const spark = new THREE.Mesh(sparkGeo, sparkMat);
        
        this.scene.add(spark);
        
        // Animate the spark along the line (Simple linear interpolation)
        let progress = 0;
        const animateSpark = () => {
            progress += 0.02;
            spark.position.lerpVectors(start, end, progress);
            
            if (progress < 1) {
                requestAnimationFrame(animateSpark);
            } else {
                this.scene.remove(spark);
            }
        };
        animateSpark();
    }

    resetNodeState(node) {
        const index = this.wordNodes.indexOf(node);
        const label = this.wordLabels[index];

        // 1. Reset Node
        node.scale.setScalar(1.0);
        node.material.emissiveIntensity = 0;

        // 2. Reset Word (Remove Glow)
        if (label) {
            label.scale.set(15, 7.5, 1);
            label.position.copy(node.position);
            label.position.y -= 8;
            label.material.color.set(0x25D366); // Back to matte green
            label.material.opacity = 0.7;
        }

        // 3. Reset Connections to persistent bio-luminescent glow
        this.connections.forEach(line => {
            line.material.color.set(0x25D366); // WhatsApp Green
            line.material.opacity = 0.4; // Always-on glow
        });
    }
}
window.addEventListener('DOMContentLoaded', () => new WordEmbeddingVisualization());