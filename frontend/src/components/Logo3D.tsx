"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

// 7didan speech bubble path in unit square
function bubblePath(p: THREE.Shape, r = 0.34) {
  p.moveTo(-0.5 + r, 0.5);
  p.lineTo(0.5 - r, 0.5);
  p.quadraticCurveTo(0.5, 0.5, 0.5, 0.5 - r);
  p.lineTo(0.5, -0.5 + r);
  p.quadraticCurveTo(0.5, -0.5, 0.5 - r, -0.5);
  p.lineTo(-0.1, -0.5);
  p.lineTo(-0.44, -0.76);
  p.quadraticCurveTo(-0.5, -0.6, -0.5, -0.5 + r * 0.45);
  p.lineTo(-0.5, 0.5 - r);
  p.quadraticCurveTo(-0.5, 0.5, -0.5 + r, 0.5);
  return p;
}

const SEVEN_PTS: [number, number][] = [
  [-0.25, 0.3],
  [0.27, 0.3],
  [0.27, 0.17],
  [0.03, -0.31],
  [-0.13, -0.31],
  [0.1, 0.17],
  [-0.25, 0.17],
];

function sparkPoints(R = 0.2, r = 0.055) {
  const pts: [number, number][] = [];
  for (let k = 0; k < 8; k += 1) {
    const a = Math.PI / 2 + (k * Math.PI) / 4;
    const rr = k % 2 ? r : R;
    pts.push([Math.cos(a) * rr, Math.sin(a) * rr]);
  }
  return pts;
}

function polyShape(pts: [number, number][]) {
  const s = new THREE.Shape();
  pts.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y)));
  s.closePath();
  return s;
}

function extrude(shape: THREE.Shape, depth: number, bevel: number) {
  const g = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 4,
    curveSegments: 24,
  });
  g.center();
  return g;
}

export function Logo3D({ className = "h-72 w-72" }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 300;
    const height = container.clientHeight || 300;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0, 3.6);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lighting
    const amb = new THREE.AmbientLight(0xfff6ed, 1.2);
    scene.add(amb);

    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(3, 4, 5);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xff6b1a, 1.5);
    fill.position.set(-4, -2, 2);
    scene.add(fill);

    const topSpark = new THREE.PointLight(0xffc83d, 2.5, 8);
    topSpark.position.set(1.5, 1.8, 2);
    scene.add(topSpark);

    // Materials
    const bubMatCap = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#ff6b1a"),
      roughness: 0.26,
      clearcoat: 0.8,
      emissive: new THREE.Color("#ff6b1a"),
      emissiveIntensity: 0.12,
    });
    const bubMatSide = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#7a2e0d"),
      roughness: 0.45,
      clearcoat: 0.2,
    });

    const sevenMatCap = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#f6f0e6"),
      roughness: 0.2,
      clearcoat: 0.6,
      emissive: new THREE.Color("#f6f0e6"),
      emissiveIntensity: 0.05,
    });
    const sevenMatSide = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#d9cfbf"),
      roughness: 0.35,
    });

    const sparkMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#ffc83d"),
      roughness: 0.15,
      emissive: new THREE.Color("#ffc83d"),
      emissiveIntensity: 0.4,
    });

    const grp = new THREE.Group();

    const bubGeo = extrude(bubblePath(new THREE.Shape()), 0.26, 0.07);
    const bubMesh = new THREE.Mesh(bubGeo, [bubMatCap, bubMatSide]);
    grp.add(bubMesh);

    const sevenGeo = extrude(polyShape(SEVEN_PTS), 0.07, 0.025);
    const sevenMesh = new THREE.Mesh(sevenGeo, [sevenMatCap, sevenMatSide]);
    sevenMesh.position.z = 0.19;
    grp.add(sevenMesh);

    const sparkGeo = extrude(polyShape(sparkPoints(0.24, 0.065)), 0.08, 0.03);
    const sparkMesh = new THREE.Mesh(sparkGeo, sparkMat);
    sparkMesh.position.set(0.48, 0.48, 0.2);
    grp.add(sparkMesh);

    scene.add(grp);

    // Mouse interaction tracking with smooth critically-damped lerp
    let targetRx = 0.12;
    let targetRy = -0.25;
    let currentRx = targetRx;
    let currentRy = targetRy;

    const onPointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const nx = (e.clientX - (rect.left + rect.width / 2)) / (window.innerWidth / 2);
      const ny = (e.clientY - (rect.top + rect.height / 2)) / (window.innerHeight / 2);
      targetRy = nx * 0.7 - 0.25;
      targetRx = -ny * 0.5 + 0.12;
    };
    window.addEventListener("mousemove", onPointerMove, { passive: true });

    let reqId = 0;
    let t0 = performance.now();

    const render = () => {
      reqId = requestAnimationFrame(render);
      const t = (performance.now() - t0) * 0.001;

      // Soft breathing float
      const floatY = Math.sin(t * 1.5) * 0.06;
      const pulseSpark = 1 + Math.sin(t * 3.2) * 0.15;
      sparkMesh.scale.set(pulseSpark, pulseSpark, pulseSpark);
      sparkMesh.rotation.z = Math.sin(t * 1.2) * 0.15;

      // Critically damped rotation towards mouse target
      currentRx += (targetRx - currentRx) * 0.06;
      currentRy += (targetRy - currentRy) * 0.06;

      grp.position.y = floatY;
      grp.rotation.x = currentRx;
      grp.rotation.y = currentRy + Math.sin(t * 0.7) * 0.08;
      grp.rotation.z = Math.sin(t * 0.9) * 0.03;

      renderer.render(scene, camera);
    };
    render();

    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener("mousemove", onPointerMove);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      bubGeo.dispose();
      sevenGeo.dispose();
      sparkGeo.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} className={className} aria-hidden="true" />;
}

