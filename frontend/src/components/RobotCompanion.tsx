import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { defaultColors } from '../content.ts';
import { getPointer } from '../lib/pointerStore.ts';

interface RobotCompanionProps {
  size?: number;
  calm?: boolean;
  clientX?: number;
  clientY?: number;
  isIdle?: boolean;
  onInteractiveHoverStart?: (label?: string) => void;
  onInteractiveHoverEnd?: () => void;
  className?: string;
}

export const RobotCompanion: React.FC<RobotCompanionProps> = ({
  size = 280,
  calm = false,
  clientX,
  clientY,
  isIdle,
  onInteractiveHoverStart,
  onInteractiveHoverEnd,
  className = '',
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const shadowRef = useRef<HTMLDivElement | null>(null);

  const propsRef = useRef({
    clientX,
    clientY,
    isIdle,
    calm,
  });

  useEffect(() => {
    propsRef.current = {
      clientX,
      clientY,
      isIdle,
      calm,
    };
  }, [clientX, clientY, isIdle, calm]);

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
    const width = size;
    const height = size;

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

    // 1. Off-white glossy Sphere Head
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
    const faceCanvas = document.createElement('canvas');
    faceCanvas.width = 1024;
    faceCanvas.height = 1024;
    const ctx = faceCanvas.getContext('2d', { willReadFrequently: true })!;

    const faceTexture = new THREE.CanvasTexture(faceCanvas);
    faceTexture.colorSpace = THREE.SRGBColorSpace;
    faceTexture.wrapS = THREE.ClampToEdgeWrapping;
    faceTexture.wrapT = THREE.ClampToEdgeWrapping;
    faceTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();

    const faceGeom = new THREE.SphereGeometry(1.005, 96, 96, 0, Math.PI * 2, 0, Math.PI * 0.48);
    faceGeom.rotateX(Math.PI / 2);

    const posAttr = faceGeom.attributes.position;
    const uvAttr = faceGeom.attributes.uv;

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

    const isCalm = propsRef.current.calm;
    const maxYaw = isCalm ? 0.38 : 0.94;
    const maxPitch = isCalm ? 0.21 : 0.46;

    let currentYaw = 0;
    let currentPitch = 0;
    let yawVel = 0;
    let pitchVel = 0;

    let introProgress = isCalm ? 1.0 : 0.0;
    const introDuration = 1.4;

    let blinkValue = 1.0;
    let nextBlinkTime = 2.5 + Math.random() * 2;
    let isBlinking = false;
    let blinkStartTime = 0;

    const raycaster = new THREE.Raycaster();
    const mouseVector = new THREE.Vector2(-99, -99);
    let isRobotHovered = false;

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

    let clock = new THREE.Clock();
    let frameId = 0;

    const render = () => {
      frameId = requestAnimationFrame(render);

      const delta = Math.min(clock.getDelta(), 0.1);
      const time = clock.getElapsedTime();
      const currentProps = propsRef.current;
      const calmActive = currentProps.calm;

      if (introProgress < 1.0) {
        introProgress += delta / introDuration;
        if (introProgress > 1.0) introProgress = 1.0;
      }

      const p = introProgress;
      const introY = p < 1.0 ? -3.2 * Math.pow(1 - p, 2.5) : 0;
      const introScale = p < 1.0 ? 0.6 + 0.45 * Math.sin(p * Math.PI * 0.95) : 1.0;

      const bobFreq = calmActive ? 1.6 : 2.1;
      const bobAmp = calmActive ? 0.04 : 0.085;
      const bobY = Math.sin(time * bobFreq) * bobAmp;
      const effectiveY = introY + (introProgress >= 0.9 ? bobY : 0);

      if (shadowRef.current) {
        const shadowScale = 1.0 - (effectiveY / 0.12) * 0.15;
        const shadowOpacity = Math.max(0.18, 0.42 - (effectiveY / 0.12) * 0.16);
        const introShadowOpacity = Math.min(1.0, introProgress * 1.5) * shadowOpacity;
        shadowRef.current.style.transform = `scale(${Math.max(0.7, shadowScale * introScale)})`;
        shadowRef.current.style.opacity = `${introShadowOpacity}`;
      }

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

      const activeMaxYaw = calmActive ? 0.38 : 0.94;
      const activeMaxPitch = calmActive ? 0.21 : 0.46;

      let targetYaw = 0;
      let targetPitch = 0;

      if (!currentlyIdle) {
        targetYaw = dx * activeMaxYaw;
        targetPitch = dy * activeMaxPitch;
      }

      const stiffness = calmActive ? 65.0 : 85.0;
      const damping = calmActive ? 0.88 : 0.82;

      const yawForce = (targetYaw - currentYaw) * stiffness;
      yawVel = (yawVel + yawForce * delta) * damping;
      currentYaw += yawVel * delta;

      const pitchForce = (targetPitch - currentPitch) * stiffness;
      pitchVel = (pitchVel + pitchForce * delta) * damping;
      currentPitch += pitchVel * delta;

      headGroup.rotation.y = currentYaw;
      headGroup.rotation.x = currentPitch;

      const parallaxScale = calmActive ? 0.06 : 0.12;
      headGroup.position.x = dx * parallaxScale;
      headGroup.position.y = effectiveY - dy * (parallaxScale * 0.65);
      headGroup.scale.set(introScale, introScale, introScale);

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

      ctx.clearRect(0, 0, 1024, 1024);

      const vWidth = 760;
      const vHeight = 510;
      const vRadius = 210;
      const vX = (1024 - vWidth) / 2;
      const vY = (1024 - vHeight) / 2;

      const rimGradient = ctx.createLinearGradient(vX, vY, vX + vWidth, vY + vHeight);
      const [c0, c1, c2] = defaultColors.rimColors;
      rimGradient.addColorStop(0, c0);
      rimGradient.addColorStop(0.5, c1);
      rimGradient.addColorStop(1, c2);

      ctx.save();
      drawSquircle(ctx, vX, vY, vWidth, vHeight, vRadius);
      ctx.fillStyle = rimGradient;
      ctx.shadowColor = c1;
      ctx.shadowBlur = 16;
      ctx.fill();
      ctx.restore();

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

      const sheenGrad = ctx.createLinearGradient(innerX, innerY, innerX, innerY + innerH * 0.55);
      sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.16)');
      sheenGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.04)');
      sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = sheenGrad;
      ctx.fill();
      ctx.restore();

      const eyeShiftX = (currentYaw / activeMaxYaw) * 36;
      const eyeShiftY = (currentPitch / activeMaxPitch) * 26;

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

    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth || size;
      const newH = container.clientHeight || size;
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
  }, [size]);

  const shadowW = Math.round(size * 0.7);
  const shadowH = Math.round(size * 0.1);

  return (
    <div className={`relative flex flex-col items-center justify-center select-none ${className}`}>
      <div
        ref={mountRef}
        data-cursor="interactive"
        style={{ width: `${size}px`, height: `${size}px` }}
        className="relative z-10 flex items-center justify-center cursor-pointer"
        onMouseEnter={() => onInteractiveHoverStart?.('robot')}
        onMouseLeave={onInteractiveHoverEnd}
      />

      <div
        ref={shadowRef}
        style={{
          width: `${shadowW}px`,
          height: `${shadowH}px`,
          filter: 'blur(16px)',
          opacity: 0.38,
        }}
        className="-mt-5 rounded-[100%] bg-[#9696A3] pointer-events-none transition-transform duration-300 ease-out will-change-transform"
        aria-hidden="true"
      />
    </div>
  );
};
