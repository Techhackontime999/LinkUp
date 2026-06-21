(function() {
  'use strict';

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (typeof THREE === 'undefined') return;

  let scene, camera, renderer;
  let nodeSystem, connectionSystem, auroraSystem, glowParticles;
  let dataStreams, geometricShape, sparkBursts;
  let mouseX = 0, mouseY = 0;
  let isActive = false;
  let frameId = null;
  let clock = new THREE.Clock();
  let nodePositions;

  const D = (function() {
    const isMobile = /Mobi|Android/i.test(navigator.userAgent);
    const dpr = Math.min(window.devicePixelRatio, 2);
    return {
      nodeCount: isMobile ? 80 : 160,
      connectionDistance: isMobile ? 10 : 14,
      nodeSize: 0.18,
      auroraLayers: 3,
      auroraPoints: 96,
      glowCount: isMobile ? 40 : 80,
      streamCount: isMobile ? 20 : 50,
      streamParticles: isMobile ? 4 : 8,
      dpr: dpr,
      isMobile: isMobile
    };
  })();

  function createCircleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.15, 'rgba(255,255,255,0.8)');
    gradient.addColorStop(0.5, 'rgba(255,255,255,0.3)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
  }

  function initNeuralAurora() {
    try {
      const container = document.getElementById('neural-aurora-bg');
      if (!container || isActive) return;

      if (!THREE.WebGLRenderer) {
        container.style.display = 'none';
        return;
      }

      const testCanvas = document.createElement('canvas');
      const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
      if (!gl) {
        container.style.display = 'none';
        return;
      }

      isActive = true;

      clock = new THREE.Clock();
      scene = new THREE.Scene();

      const W = window.innerWidth;
      const H = window.innerHeight;

      camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 200);
      camera.position.set(0, -1, 30);
      camera.lookAt(0, 0, 0);

      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: !D.isMobile,
        powerPreference: 'high-performance'
      });
      renderer.setSize(W, H);
      renderer.setPixelRatio(D.dpr);
      renderer.setClearColor(0x000000, 0);
      container.appendChild(renderer.domElement);

      container.style.opacity = '0';
      container.style.transition = 'opacity 0.8s ease';
      requestAnimationFrame(() => { container.style.opacity = '1'; });

      createNeuralNodes();
      createConnections();
      createAuroraWaves();
      createGlowParticles();
      createDataStreams();
      createGeometricShape();
      createSparkBursts();

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('resize', onResize);
      window.addEventListener('themeChanged', onThemeChange);

      animate();

      window.__neuralAurora = {
        init: initNeuralAurora,
        destroy: destroyNeuralAurora
      };
    } catch (e) {
      console.warn('Neural aurora init failed:', e);
      const container = document.getElementById('neural-aurora-bg');
      if (container) container.style.display = 'none';
    }
  }

  function createNeuralNodes() {
    const count = D.nodeCount;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    nodePositions = positions;

    const palette = [
      new THREE.Color(0.30, 0.85, 0.80),
      new THREE.Color(0.60, 0.30, 0.95),
      new THREE.Color(0.20, 0.90, 0.60),
      new THREE.Color(0.85, 0.35, 0.75),
      new THREE.Color(0.35, 0.65, 0.98)
    ];

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 40 + 2;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 35;

      const c = palette[i % palette.length];
      const v = 0.6 + Math.random() * 0.4;
      colors[i * 3] = c.r * v;
      colors[i * 3 + 1] = c.g * v;
      colors[i * 3 + 2] = c.b * v;

      sizes[i] = 1 + Math.random() * 2;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const texture = createCircleTexture();
    const material = new THREE.PointsMaterial({
      size: D.nodeSize,
      map: texture,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    nodeSystem = new THREE.Points(geometry, material);
    scene.add(nodeSystem);
  }

  function createConnections() {
    const count = D.nodeCount;
    const maxPairs = count * 4;
    const positions = new Float32Array(maxPairs * 6);
    const colors = new Float32Array(maxPairs * 6);
    let idx = 0;

    const distSq = D.connectionDistance * D.connectionDistance;

    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        if (idx >= maxPairs) break;
        const i3 = i * 3, j3 = j * 3;
        const dx = nodePositions[i3] - nodePositions[j3];
        const dy = nodePositions[i3 + 1] - nodePositions[j3 + 1];
        const dz = nodePositions[i3 + 2] - nodePositions[j3 + 2];
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 > distSq) continue;

        const alpha = 1 - Math.sqrt(d2) / D.connectionDistance;

        const ci = idx * 6;
        positions[ci] = nodePositions[i3];
        positions[ci + 1] = nodePositions[i3 + 1];
        positions[ci + 2] = nodePositions[i3 + 2];
        positions[ci + 3] = nodePositions[j3];
        positions[ci + 4] = nodePositions[j3 + 1];
        positions[ci + 5] = nodePositions[j3 + 2];

        const hue = 0.55 + alpha * 0.25;
        const c = new THREE.Color().setHSL(hue, 0.7, 0.5 + alpha * 0.3);
        colors[ci] = c.r;
        colors[ci + 1] = c.g;
        colors[ci + 2] = c.b;
        colors[ci + 3] = c.r;
        colors[ci + 4] = c.g;
        colors[ci + 5] = c.b;

        idx++;
      }
    }

    const connectionGeometry = new THREE.BufferGeometry();
    connectionGeometry.setAttribute('position', new THREE.BufferAttribute(positions.slice(0, idx * 6), 3));

    const connColors = colors.slice(0, idx * 6);
    connectionGeometry.setAttribute('color', new THREE.BufferAttribute(connColors, 3));

    const material = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    connectionSystem = new THREE.LineSegments(connectionGeometry, material);
    scene.add(connectionSystem);
  }

  function createAuroraWaves() {
    const layers = D.auroraLayers;
    const count = D.auroraPoints;
    auroraSystem = [];

    const waveColors = [
      new THREE.Color(0.15, 0.70, 0.65),
      new THREE.Color(0.45, 0.20, 0.80),
      new THREE.Color(0.10, 0.75, 0.50)
    ];

    for (let l = 0; l < layers; l++) {
      const positions = new Float32Array(count * 3);
      const colors = new Float32Array(count * 3);

      const baseY = -8 - l * 5;
      const spread = 40 + l * 5;
      const yRange = 8 + l * 3;

      for (let i = 0; i < count; i++) {
        const t = i / count;
        positions[i * 3] = (t - 0.5) * spread;
        positions[i * 3 + 1] = baseY + Math.sin(t * Math.PI * 6) * yRange * 0.3;
        positions[i * 3 + 2] = -15 - l * 5 + Math.sin(t * Math.PI * 4) * 5;

        const c = waveColors[l % waveColors.length];
        const alpha = 0.15 + 0.2 * (1 - Math.abs(t - 0.5) * 2);
        colors[i * 3] = c.r * alpha;
        colors[i * 3 + 1] = c.g * alpha;
        colors[i * 3 + 2] = c.b * alpha;
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const material = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        linewidth: 1,
      });

      const line = new THREE.Line(geometry, material);
      scene.add(line);
      auroraSystem.push({
        mesh: line,
        baseY: baseY,
        spread: spread,
        yRange: yRange,
        speed: 0.3 + Math.random() * 0.3,
        phase: Math.random() * Math.PI * 2,
        time: 0,
        positions: positions,
        count: count
      });
    }
  }

  function createGlowParticles() {
    const count = D.glowCount;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);

    const c = new THREE.Color(0.3, 0.8, 0.7);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 70;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 2] = -10 + Math.random() * 25;
      colors[i * 3] = c.r * (0.3 + Math.random() * 0.7);
      colors[i * 3 + 1] = c.g * (0.3 + Math.random() * 0.7);
      colors[i * 3 + 2] = c.b * (0.3 + Math.random() * 0.7);
      sizes[i] = 2 + Math.random() * 4;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const texture = createCircleTexture();
    const material = new THREE.PointsMaterial({
      size: 0.4,
      map: texture,
      vertexColors: true,
      transparent: true,
      opacity: 0.2,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    glowParticles = new THREE.Points(geometry, material);
    scene.add(glowParticles);
  }

  function createDataStreams() {
    const count = D.streamCount;
    const particlesPerStream = D.streamParticles;
    const total = count * particlesPerStream;
    const positions = new Float32Array(total * 3);
    const colors = new Float32Array(total * 3);
    const sizes = new Float32Array(total);
    const velocities = new Float32Array(total);
    const streamInfo = [];

    const palette = [
      new THREE.Color(0.30, 0.85, 0.80),
      new THREE.Color(0.60, 0.30, 0.95),
      new THREE.Color(0.20, 0.90, 0.60),
    ];

    for (let s = 0; s < count; s++) {
      const sx = (Math.random() - 0.5) * 60;
      const sz = -15 + Math.random() * 25;
      const speed = 0.3 + Math.random() * 0.7;
      const spread = 0.3 + Math.random() * 0.8;
      const color = palette[s % palette.length].clone();
      color.multiplyScalar(0.5 + Math.random() * 0.5);
      streamInfo.push({ sx, sz, speed, spread, color });
      const base = s * particlesPerStream * 3;
      for (let p = 0; p < particlesPerStream; p++) {
        const i = base + p * 3;
        const vy = Math.random() * 20 - 10;
        positions[i] = sx + (Math.random() - 0.5) * spread;
        positions[i + 1] = vy + (p / particlesPerStream) * 20 - 10;
        positions[i + 2] = sz + (Math.random() - 0.5) * spread * 0.3;
        const bright = 0.2 + Math.random() * 0.8;
        colors[i] = color.r * bright;
        colors[i + 1] = color.g * bright;
        colors[i + 2] = color.b * bright;
        sizes[p] = 0.6 + Math.random() * 1.2;
        velocities[base / 3 + p] = speed * (0.8 + Math.random() * 0.4);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const texture = createCircleTexture();
    const material = new THREE.PointsMaterial({
      size: 0.15,
      map: texture,
      vertexColors: true,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    dataStreams = {
      system: new THREE.Points(geometry, material),
      positions: positions,
      velocities: velocities,
      streamInfo: streamInfo,
      particlesPerStream: particlesPerStream,
      count: count
    };
    scene.add(dataStreams.system);
  }

  function createGeometricShape() {
    const geometry = new THREE.TorusKnotGeometry(1.8, 0.6, 64, 8, 2, 3);
    const material = new THREE.MeshBasicMaterial({
      color: 0x4a8fe7,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
    });
    geometricShape = new THREE.Mesh(geometry, material);
    geometricShape.position.set(6, 3, -15);
    geometricShape.scale.set(1, 1, 1);
    scene.add(geometricShape);
  }

  function createSparkBursts() {
    const count = 30;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const sparks = [];

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 40 + 2;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 30;
      sizes[i] = 1 + Math.random() * 3;
      const c = new THREE.Color(0.5, 0.85, 0.9);
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
      sparks.push({
        phase: Math.random() * Math.PI * 2,
        speed: 0.2 + Math.random() * 0.5,
        baseX: positions[i * 3],
        baseY: positions[i * 3 + 1],
        baseZ: positions[i * 3 + 2],
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const texture = createCircleTexture();
    const material = new THREE.PointsMaterial({
      size: 0.3,
      map: texture,
      vertexColors: true,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    sparkBursts = {
      system: new THREE.Points(geometry, material),
      sparks: sparks,
      positions: positions,
      time: 0
    };
    scene.add(sparkBursts.system);
  }

  function animate() {
    if (!isActive) return;
    frameId = requestAnimationFrame(animate);

    const elapsed = clock.getElapsedTime();

    if (nodeSystem) {
      const pos = nodeSystem.geometry.attributes.position.array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i + 1] += Math.sin(elapsed * 0.15 + i * 0.1) * 0.0015;
        pos[i] += Math.cos(elapsed * 0.12 + i * 0.15) * 0.0015;
        pos[i + 2] += Math.sin(elapsed * 0.08 + i * 0.05) * 0.0008;
      }
      nodeSystem.geometry.attributes.position.needsUpdate = true;

      nodeSystem.rotation.x += (mouseY * 0.015 - nodeSystem.rotation.x) * 0.008;
      nodeSystem.rotation.y += (mouseX * 0.015 - nodeSystem.rotation.y) * 0.008;
    }

    if (connectionSystem) {
      const pos = connectionSystem.geometry.attributes.position.array;
      const pulse = 0.3 + 0.15 * Math.sin(elapsed * 0.5);
      connectionSystem.material.opacity = pulse;

      if (!D.isMobile) {
        const nodePos = nodeSystem.geometry.attributes.position.array;
        for (let i = 0; i < pos.length / 6; i++) {
          const ci = i * 6;
          const midX = (pos[ci] + pos[ci + 3]) / 2;
          const midY = (pos[ci + 1] + pos[ci + 4]) / 2;
          const midZ = (pos[ci + 2] + pos[ci + 5]) / 2;
          let nearestIdx = 0;
          let minDist = Infinity;
          for (let j = 0; j < D.nodeCount; j++) {
            const j3 = j * 3;
            const d = (midX - nodePos[j3]) ** 2 + (midY - nodePos[j3 + 1]) ** 2 + (midZ - nodePos[j3 + 2]) ** 2;
            if (d < minDist) { minDist = d; nearestIdx = j; }
          }
          const n3 = nearestIdx * 3;
          pos[ci] += (nodePos[n3] - pos[ci]) * 0.002;
          pos[ci + 1] += (nodePos[n3 + 1] - pos[ci + 1]) * 0.002;
          pos[ci + 2] += (nodePos[n3 + 2] - pos[ci + 2]) * 0.002;
          pos[ci + 3] += (nodePos[n3] - pos[ci + 3]) * 0.002;
          pos[ci + 4] += (nodePos[n3 + 1] - pos[ci + 4]) * 0.002;
          pos[ci + 5] += (nodePos[n3 + 2] - pos[ci + 5]) * 0.002;
        }
        connectionSystem.geometry.attributes.position.needsUpdate = true;
      }
    }

    for (let l = 0; l < auroraSystem.length; l++) {
      const wave = auroraSystem[l];
      wave.time += 0.005 * wave.speed;
      const positions = wave.mesh.geometry.attributes.position.array;

      for (let i = 0; i < wave.count; i++) {
        const i3 = i * 3;
        const t = i / wave.count;
        const x = (t - 0.5) * wave.spread;
        positions[i3] = x;
        positions[i3 + 1] = wave.baseY +
          Math.sin(t * Math.PI * 6 + wave.time * 2 + wave.phase) * wave.yRange * 0.3 +
          Math.sin(t * Math.PI * 2 + wave.time + wave.phase) * wave.yRange * 0.15;
        positions[i3 + 2] = -15 - l * 5 +
          Math.sin(t * Math.PI * 4 + wave.time * 1.5 + wave.phase) * 5;
      }
      wave.mesh.geometry.attributes.position.needsUpdate = true;
    }

    if (glowParticles) {
      const pos = glowParticles.geometry.attributes.position.array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i] += Math.sin(elapsed * 0.05 + i) * 0.002;
        pos[i + 1] += Math.cos(elapsed * 0.06 + i * 0.5) * 0.002;
      }
      glowParticles.geometry.attributes.position.needsUpdate = true;
      glowParticles.material.opacity = 0.15 + 0.1 * Math.sin(elapsed * 0.3);
    }

    if (dataStreams) {
      const pos = dataStreams.positions;
      const pps = dataStreams.particlesPerStream;
      for (let s = 0; s < dataStreams.count; s++) {
        const base = s * pps * 3;
        for (let p = 0; p < pps; p++) {
          const i = base + p * 3;
          pos[i + 1] -= dataStreams.velocities[s * pps + p] * 0.03;
          if (pos[i + 1] < -12) {
            pos[i + 1] = 12;
            pos[i] = dataStreams.streamInfo[s].sx + (Math.random() - 0.5) * dataStreams.streamInfo[s].spread;
            pos[i + 2] = dataStreams.streamInfo[s].sz + (Math.random() - 0.5) * dataStreams.streamInfo[s].spread * 0.3;
          }
        }
      }
      dataStreams.system.geometry.attributes.position.needsUpdate = true;
      const streamPulse = 0.35 + 0.2 * Math.sin(elapsed * 0.4);
      dataStreams.system.material.opacity = streamPulse;
    }

    if (geometricShape) {
      geometricShape.rotation.x += 0.002;
      geometricShape.rotation.y += 0.005;
      geometricShape.rotation.z += 0.001;
      geometricShape.position.y = 3 + Math.sin(elapsed * 0.2) * 1.5;
      const shapePulse = 0.08 + 0.06 * Math.sin(elapsed * 0.5);
      geometricShape.material.opacity = shapePulse;
    }

    if (sparkBursts) {
      sparkBursts.time += 0.01;
      const pos = sparkBursts.positions;
      for (let i = 0; i < sparkBursts.sparks.length; i++) {
        const s = sparkBursts.sparks[i];
        const i3 = i * 3;
        const burst = Math.sin(sparkBursts.time * s.speed + s.phase);
        pos[i3] = s.baseX + burst * 3;
        pos[i3 + 1] = s.baseY + Math.cos(sparkBursts.time * s.speed * 0.7 + s.phase) * 2;
        pos[i3 + 2] = s.baseZ + Math.sin(sparkBursts.time * s.speed * 0.5 + s.phase) * 2;
      }
      sparkBursts.system.geometry.attributes.position.needsUpdate = true;
      const sparkOpacity = 0.15 + 0.12 * Math.sin(sparkBursts.time * 0.6);
      sparkBursts.system.material.opacity = Math.max(0, sparkOpacity);
    }

    renderer.render(scene, camera);
  }

  function onMouseMove(event) {
    mouseX = (event.clientX / window.innerWidth) * 2 - 1;
    mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
  }

  let resizeTimeout;
  function onResize() {
    if (resizeTimeout) cancelAnimationFrame(resizeTimeout);
    resizeTimeout = requestAnimationFrame(function() {
      if (!camera || !renderer) return;
      const W = window.innerWidth;
      const H = window.innerHeight;
      camera.aspect = W / H;
      camera.updateProjectionMatrix();
      renderer.setSize(W, H);
      renderer.setPixelRatio(D.dpr);
    });
  }

  function onThemeChange(e) {
    const isDark = e.detail.isDark;
    if (auroraSystem) {
      auroraSystem.forEach(wave => {
        wave.mesh.material.opacity = isDark ? 0.55 : 0.25;
      });
    }
    if (nodeSystem) {
      nodeSystem.material.opacity = isDark ? 0.9 : 0.55;
    }
    if (connectionSystem) {
      connectionSystem.material.opacity = isDark ? 0.35 : 0.15;
    }
    if (glowParticles) {
      glowParticles.material.opacity = isDark ? 0.25 : 0.1;
    }
    if (dataStreams) {
      dataStreams.system.material.opacity = isDark ? 0.5 : 0.25;
    }
    if (geometricShape) {
      geometricShape.material.opacity = isDark ? 0.12 : 0.06;
    }
    if (sparkBursts) {
      sparkBursts.system.material.opacity = isDark ? 0.2 : 0.08;
    }
  }

  function destroyNeuralAurora() {
    if (!isActive) return;
    isActive = false;

    if (frameId) cancelAnimationFrame(frameId);

    document.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onResize);
    window.removeEventListener('themeChanged', onThemeChange);

    if (renderer) {
      renderer.dispose();
      const container = document.getElementById('neural-aurora-bg');
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
    }

    scene = null;
    camera = null;
    renderer = null;
    nodeSystem = null;
    connectionSystem = null;
    auroraSystem = null;
    glowParticles = null;
    dataStreams = null;
    geometricShape = null;
    sparkBursts = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNeuralAurora);
  } else {
    initNeuralAurora();
  }
})();
