import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { defaultColors } from '../content.ts';
import { getPointer } from '../lib/pointerStore.ts';

interface RobotProps {
  clientX?: number;
  clientY?: number;
  isIdle?: boolean;
  onInteractiveHoverStart?: (label?: string) => void;
  onInteractiveHoverEnd?: () => void;
  className?: string;
  canvasClassName?: string;
  shadowClassName?: string;
}

export const Robot: React.FC<RobotProps> = ({
  clientX,
  clientY,
  isIdle,
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
  className = '',
  canvasClassName,
  shadowClassName,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const shadowRef = useRef<HTMLDivElement | null>(null);

  const propsRef = useRef({
    clientX,
    clientY,
    isIdle,
  });

  useEffect(() => {
    propsRef.current = {
      clientX,
      clientY,
      isIdle,
    };
  }, [clientX, clientY, isIdle]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Detect software WebGL
    const isSoftwareGl = (() => {
      try {
        const probeCanvas = document.createElement('canvas');
        const gl = probeCanvas.getContext('webgl2') || probeCanvas.getContext('webgl');
        if (!gl) return true;
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
        const gpu = String(gl.getParameter(param));
        gl.getExtension('WEBGL_lose_context')?.loseContext();
        return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
      } catch {
        return false;
      }
    })();

    // Setup Scene, Camera & Renderer
    const scene = new THREE.Scene();
    const width = container.clientWidth || 360;
    const height = container.clientHeight || 360;

    const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 100);
    camera.position.set(0, 0, 5.2);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: !isSoftwareGl,
      powerPreference: 'high-performance',
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Studio 3-point Lighting
    const keyLight = new THREE.DirectionalLight(0xfffbf5, 2.2);
    keyLight.position.set(-3.5, 4.5, 5.0);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xdee5f0, 0.85);
    fillLight.position.set(3.5, -3.0, 3.5);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xffffff, 0.6);
    rimLight.position.set(0, 4.0, -3.0);
    scene.add(rimLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xcfcfd4, 0.95);
    scene.add(hemiLight);

    // Robot Head Group (pivot center)
    const headGroup = new THREE.Group();
    scene.add(headGroup);

    // 1. Off-white glossy Sphere Head (high resolution 96x96)
    const headGeom = new THREE.SphereGeometry(1.0, 96, 96);
    const headMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xf5f5f7,
      roughness: 0.35,
      metalness: 0.02,
      clearcoat: 0.45,
      clearcoatRoughness: 0.2,
    });
    const headMesh = new THREE.Mesh(headGeom, headMaterial);
    headGroup.add(headMesh);

    // 2. Front Planar-projected Face Shell for Visor & Eyes
    // Built from front spherical cap only to guarantee ZERO ridge or seam line
    const faceCanvas = document.createElement('canvas');
    faceCanvas.width = 1024;
    faceCanvas.height = 1024;
    const ctx = faceCanvas.getContext('2d', { willReadFrequently: true })!;

    const faceTexture = new THREE.CanvasTexture(faceCanvas);
    faceTexture.colorSpace = THREE.SRGBColorSpace;
    faceTexture.wrapS = THREE.ClampToEdgeWrapping;
    faceTexture.wrapT = THREE.ClampToEdgeWrapping;
    faceTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();

    // Spherical cap theta 0 to Math.PI * 0.48, rotated so pole points forward (+Z)
    const faceGeom = new THREE.SphereGeometry(1.005, 96, 96, 0, Math.PI * 2, 0, Math.PI * 0.48);
    faceGeom.rotateX(Math.PI / 2);

    const posAttr = faceGeom.attributes.position;
    const uvAttr = faceGeom.attributes.uv;

    // Planar UV projection with 8% transparent margin at texture edges
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i);
      const y = posAttr.getY(i);
      const u = 0.5 + (x / 1.005) * 0.42;
      const v = 0.5 + (y / 1.005) * 0.42;
      uvAttr.setXY(i, u, v);
    }
    uvAttr.needsUpdate = true;

    const faceMaterial = new THREE.MeshPhysicalMaterial({
      map: faceTexture,
      transparent: true,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
      roughness: 0.12,
      metalness: 0.05,
      clearcoat: 0.85,
      clearcoatRoughness: 0.1,
    });
    const faceMesh = new THREE.Mesh(faceGeom, faceMaterial);
    headGroup.add(faceMesh);

    // Max tracking angles: yaw ~54°, pitch ~26°
    const maxYaw = 0.94;
    const maxPitch = 0.46;

    let currentYaw = 0;
    let currentPitch = 0;
    let yawVel = 0;
    let pitchVel = 0;

    // Intro rise animation
    let introProgress = 0;
    const introDuration = 1.4;

    // Eye blink tracking
    let blinkValue = 1.0;
    let nextBlinkTime = 2.5 + Math.random() * 2;
    let isBlinking = false;
    let blinkStartTime = 0;

    const raycaster = new THREE.Raycaster();
    const mouseVector = new THREE.Vector2(-99, -99);
    let isRobotHovered = false;

    // Smooth rounded superellipse with continuous arc corners
    function drawSquircle(
      c: CanvasRenderingContext2D,
      x: number,
      y: number,
      w: number,
      h: number,
      radius: number
    ) {
      const r = Math.min(radius, w / 2, h / 2);
      c.beginPath();
      c.moveTo(x + r, y);
      c.lineTo(x + w - r, y);
      c.arcTo(x + w, y, x + w, y + r, r);
      c.lineTo(x + w, y + h - r);
      c.arcTo(x + w, y + h, x + w - r, y + h, r);
      c.lineTo(x + r, y + h);
      c.arcTo(x, y + h, x, y + h - r, r);
      c.lineTo(x, y + r);
      c.arcTo(x, y, x + r, y, r);
      c.closePath();
    }

    // Animation Loop
    let clock = new THREE.Clock();
    let frameId = 0;

    const render = () => {
      frameId = requestAnimationFrame(render);

      const delta = Math.min(clock.getDelta(), 0.1);
      const time = clock.getElapsedTime();

      // 1. Intro Animation Logic
      if (introProgress < 1.0) {
        introProgress += delta / introDuration;
        if (introProgress > 1.0) introProgress = 1.0;
      }

      const p = introProgress;
      const introY = p < 1.0 ? -3.2 * Math.pow(1 - p, 2.5) : 0;
      const introScale = p < 1.0 ? 0.6 + 0.45 * Math.sin(p * Math.PI * 0.95) : 1.0;

      // 2. Idle Floating Bob (±8px, ~3s sine)
      const bobY = Math.sin(time * 2.1) * 0.085;
      const effectiveY = introY + (introProgress >= 0.9 ? bobY : 0);

      // Floor shadow scale & opacity
      if (shadowRef.current) {
        const shadowScale = 1.0 - (effectiveY / 0.12) * 0.15;
        const shadowOpacity = Math.max(0.18, 0.42 - (effectiveY / 0.12) * 0.16);
        const introShadowOpacity = Math.min(1.0, introProgress * 1.5) * shadowOpacity;
        shadowRef.current.style.transform = `scale(${Math.max(0.7, shadowScale * introScale)})`;
        shadowRef.current.style.opacity = `${introShadowOpacity}`;
      }

      // 3. Pointer Relative to Robot's Actual On-Screen Center (using live coordinates)
      const rect = container.getBoundingClientRect();
      const robotCenterX = rect.left + rect.width / 2;
      const robotCenterY = rect.top + rect.height / 2;
      const halfW = (window.innerWidth || 1) * 0.5;
      const halfH = (window.innerHeight || 1) * 0.5;

      const livePointer = getPointer();
      const currentClientX = livePointer.clientX;
      const currentClientY = livePointer.clientY;
      const currentlyIdle = livePointer.isIdle;

      const dx = Math.max(-1, Math.min(1, (currentClientX - robotCenterX) / halfW));
      const dy = Math.max(-1, Math.min(1, (currentClientY - robotCenterY) / halfH));

      let targetYaw = 0;
      let targetPitch = 0;

      if (!currentlyIdle) {
        // Pointer right (dx > 0) -> looks right
        targetYaw = dx * maxYaw;
        // Pointer down (dy > 0) -> looks down
        targetPitch = dy * maxPitch;
      }

      // 4. Spring physics for head rotation
      const stiffness = 85.0;
      const damping = 0.82;

      const yawForce = (targetYaw - currentYaw) * stiffness;
      yawVel = (yawVel + yawForce * delta) * damping;
      currentYaw += yawVel * delta;

      const pitchForce = (targetPitch - currentPitch) * stiffness;
      pitchVel = (pitchVel + pitchForce * delta) * damping;
      currentPitch += pitchVel * delta;

      headGroup.rotation.y = currentYaw;
      headGroup.rotation.x = currentPitch;

      headGroup.position.x = dx * 0.12;
      headGroup.position.y = effectiveY - dy * 0.08;
      headGroup.scale.set(introScale, introScale, introScale);

      // 5. Eye Blink Logic
      if (!isBlinking && time >= nextBlinkTime) {
        isBlinking = true;
        blinkStartTime = time;
      }
      if (isBlinking) {
        const blinkElapsed = time - blinkStartTime;
        const blinkDuration = 0.13;
        if (blinkElapsed < blinkDuration) {
          const phase = (blinkElapsed / blinkDuration) * Math.PI;
          blinkValue = 1.0 - Math.sin(phase) * 0.92;
        } else {
          blinkValue = 1.0;
          isBlinking = false;
          nextBlinkTime = time + 3.0 + Math.random() * 3.5;
        }
      }

      // 6. Draw 2D Face Texture (Full clearRect and redraw each frame)
      ctx.clearRect(0, 0, 1024, 1024);

      // Visor dimensions: 760px x 510px with smooth 210px radius, drawn comfortably inside 1024x1024
      const vWidth = 760;
      const vHeight = 510;
      const vRadius = 210;
      const vX = (1024 - vWidth) / 2;
      const vY = (1024 - vHeight) / 2;

      // Outer gradient RIM (purple -> indigo -> sky blue)
      const rimGradient = ctx.createLinearGradient(vX, vY, vX + vWidth, vY + vHeight);
      const [c0, c1, c2] = defaultColors.rimColors;
      rimGradient.addColorStop(0, c0);
      rimGradient.addColorStop(0.5, c1);
      rimGradient.addColorStop(1, c2);

      // Draw Outer Rim with soft glowing bevel
      ctx.save();
      drawSquircle(ctx, vX, vY, vWidth, vHeight, vRadius);
      ctx.fillStyle = rimGradient;
      ctx.shadowColor = c1;
      ctx.shadowBlur = 16;
      ctx.fill();
      ctx.restore();

      // Draw Inner Black Visor
      const rimInset = 36;
      const innerX = vX + rimInset;
      const innerY = vY + rimInset;
      const innerW = vWidth - rimInset * 2;
      const innerH = vHeight - rimInset * 2;
      const innerR = Math.max(20, vRadius - rimInset);

      ctx.save();
      drawSquircle(ctx, innerX, innerY, innerW, innerH, innerR);
      ctx.fillStyle = '#0B0B0E';
      ctx.fill();

      // Visor subtle specular curved sheen
      const sheenGrad = ctx.createLinearGradient(innerX, innerY, innerX, innerY + innerH * 0.55);
      sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.16)');
      sheenGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.04)');
      sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = sheenGrad;
      ctx.fill();
      ctx.restore();

      // Eye shift inside visor matches head rotation direction
      const eyeShiftX = (currentYaw / maxYaw) * 36;
      const eyeShiftY = (currentPitch / maxPitch) * 26;

      const eyeBaseW = 104;
      const eyeBaseH = 190 * blinkValue;
      const eyeSep = 260;

      const eyeCenterY = 512 + eyeShiftY;
      const leftEyeX = 512 - eyeSep / 2 + eyeShiftX;
      const rightEyeX = 512 + eyeSep / 2 + eyeShiftX;

      const drawEye = (centerX: number) => {
        ctx.save();
        ctx.translate(centerX, eyeCenterY);
        ctx.beginPath();
        const rx = eyeBaseW / 2;
        const ry = Math.max(1, eyeBaseH / 2);
        ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#FFFFFF';
        ctx.shadowColor = 'rgba(255, 255, 255, 0.45)';
        ctx.shadowBlur = 8;
        ctx.fill();

        // Soft specular eye glint
        if (blinkValue > 0.6) {
          ctx.beginPath();
          ctx.ellipse(rx * 0.32, -ry * 0.32, rx * 0.28, ry * 0.22, 0, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
          ctx.shadowBlur = 0;
          ctx.fill();
        }

        ctx.restore();
      };

      drawEye(leftEyeX);
      drawEye(rightEyeX);

      faceTexture.needsUpdate = true;

      // 7. Raycasting for hover detection on the Robot
      const normMouseX = (currentClientX / (window.innerWidth || 1)) * 2 - 1;
      const normMouseY = -((currentClientY / (window.innerHeight || 1)) * 2 - 1);
      mouseVector.set(normMouseX, normMouseY);
      raycaster.setFromCamera(mouseVector, camera);
      const intersects = raycaster.intersectObject(headMesh);

      if (intersects.length > 0) {
        if (!isRobotHovered) {
          isRobotHovered = true;
          onInteractiveHoverStart?.('robot');
        }
      } else {
        if (isRobotHovered) {
          isRobotHovered = false;
          onInteractiveHoverEnd?.();
        }
      }

      renderer.render(scene, camera);
    };

    frameId = requestAnimationFrame(render);

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth || 360;
      const newH = container.clientHeight || 360;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      headGeom.dispose();
      faceGeom.dispose();
      headMaterial.dispose();
      faceMaterial.dispose();
      faceTexture.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div className={`relative flex flex-col items-center justify-center select-none ${className}`}>
      {/* 3D Canvas Mount Point */}
      <div
        ref={mountRef}
        data-cursor="interactive"
        className={
          canvasClassName ||
          'w-[280px] h-[280px] sm:w-[350px] sm:h-[350px] md:w-[clamp(340px,36vw,450px)] md:h-[clamp(340px,36vw,450px)] relative z-10 flex items-center justify-center cursor-pointer'
        }
        onMouseEnter={() => onInteractiveHoverStart?.('robot')}
        onMouseLeave={onInteractiveHoverEnd}
      />

      {/* Floor Contact Soft Elliptical Shadow */}
      <div
        ref={shadowRef}
        className={
          shadowClassName ||
          'w-[190px] sm:w-[240px] md:w-[280px] h-7 sm:h-9 md:h-11 -mt-5 sm:-mt-6 rounded-[100%] bg-[#9696A3] pointer-events-none transition-transform duration-300 ease-out will-change-transform'
        }
        style={{
          filter: 'blur(16px)',
          opacity: 0.38,
        }}
        aria-hidden="true"
      />
    </div>
  );
};
