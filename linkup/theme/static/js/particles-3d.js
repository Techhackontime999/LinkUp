(function() {
  'use strict';

  let scene, camera, renderer, particles, particleSystem;
  let mouseX = 0, mouseY = 0;
  let isActive = false;

  function initParticles() {
    const container = document.getElementById('particles-bg');
    if (!container) return;

    isActive = true;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 30;

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const geometry = new THREE.BufferGeometry();
    const count = 200;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 40;

      const color = new THREE.Color();
      color.setHSL(0.42 + Math.random() * 0.08, 0.6, 0.5 + Math.random() * 0.2);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;

      sizes[i] = Math.random() * 3 + 1;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const material = new THREE.PointsMaterial({
      size: 0.15,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    particleSystem = new THREE.Points(geometry, material);
    scene.add(particleSystem);

    const centerColor = new THREE.Color().setHSL(0.42, 0.5, 0.08);
    scene.background = new THREE.Color(0x000000);
    scene.background = null;

    document.addEventListener('mousemove', onMouseMove);
    window.addEventListener('resize', onResize);
    animate();
  }

  function onMouseMove(event) {
    mouseX = (event.clientX / window.innerWidth) * 2 - 1;
    mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
  }

  function onResize() {
    if (!camera || !renderer) return;
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  function animate() {
    if (!isActive) return;
    requestAnimationFrame(animate);

    if (particleSystem) {
      const positions = particleSystem.geometry.attributes.position.array;
      for (let i = 0; i < positions.length; i += 3) {
        positions[i + 1] += Math.sin(Date.now() * 0.0005 + i) * 0.002;
        positions[i] += Math.cos(Date.now() * 0.0007 + i * 0.5) * 0.002;
      }
      particleSystem.geometry.attributes.position.needsUpdate = true;

      particleSystem.rotation.x += 0.0002;
      particleSystem.rotation.y += 0.0003;
      particleSystem.rotation.x += (mouseY * 0.02 - particleSystem.rotation.x) * 0.01;
      particleSystem.rotation.y += (mouseX * 0.02 - particleSystem.rotation.y) * 0.01;
    }

    renderer.render(scene, camera);
  }

  function destroyParticles() {
    isActive = false;
    document.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onResize);
    if (renderer) {
      renderer.dispose();
      const container = document.getElementById('particles-bg');
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
    }
    scene = null;
    camera = null;
    renderer = null;
    particleSystem = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initParticles);
  } else {
    initParticles();
  }

  window.__particles3D = { init: initParticles, destroy: destroyParticles };
})();
