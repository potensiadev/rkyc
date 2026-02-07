import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Environment, Float, Stars, Sparkles } from "@react-three/drei";
import * as THREE from "three";
import { MotionValue } from "framer-motion";

// Helper to generate random positions
const randomPos = (scale: number) => [
    (Math.random() - 0.5) * scale,
    (Math.random() - 0.5) * scale,
    (Math.random() - 0.5) * scale,
] as [number, number, number];

interface DocumentShardProps {
    startPos: [number, number, number];
    endPos: [number, number, number];
    rotationSpeed: [number, number, number];
    progress: MotionValue<number>;
    color: string;
}

const DocumentShard = ({ startPos, endPos, rotationSpeed, progress, color }: DocumentShardProps) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const currentPos = useRef(new THREE.Vector3());
    const targetStart = useRef(new THREE.Vector3(...startPos));
    const targetEnd = useRef(new THREE.Vector3(...endPos));

    // Transformation: Paper White -> Verified Blue
    const baseColor = new THREE.Color("#f8fafc"); // Slate-50 (Paper)
    const activeColor = new THREE.Color("#3b82f6"); // Blue-500 (Verified)

    useFrame((state, delta) => {
        if (!meshRef.current) return;
        const p = progress.get();

        // SCROLL SEQUENCING (Chaos -> Scan -> Dashboard)
        // 0.0 - 0.2: Chaos (Floating)
        // 0.2 - 0.8: Assembly (Scanning)
        // 0.8 - 1.0: Locked (Dashboard)

        const smoothP = THREE.MathUtils.smoothstep(p, 0.1, 0.8);
        const t = THREE.MathUtils.clamp(smoothP, 0, 1);
        const ease = t * t * (3 - 2 * t);

        // Position: Move from Chaos to Grid
        currentPos.current.lerpVectors(targetStart.current, targetEnd.current, ease);
        meshRef.current.position.copy(currentPos.current);

        // Rotation: Spin wildly -> Align perfectly flat (0,0,0)
        // We lerp the extra rotation down to 0
        meshRef.current.rotation.x += rotationSpeed[0] * delta * (1 - ease);
        meshRef.current.rotation.y += rotationSpeed[1] * delta * (1 - ease);
        meshRef.current.rotation.z += rotationSpeed[2] * delta * (1 - ease);

        // Force alignment at the end
        if (ease > 0.9) {
            meshRef.current.rotation.x = THREE.MathUtils.lerp(meshRef.current.rotation.x, 0, 0.1);
            meshRef.current.rotation.y = THREE.MathUtils.lerp(meshRef.current.rotation.y, 0, 0.1);
            meshRef.current.rotation.z = THREE.MathUtils.lerp(meshRef.current.rotation.z, 0, 0.1);
        }

        // Color: Flash blue when "Scanning" (middle of animation)
        // Then settle to clean white or blue interface color
        if (meshRef.current.material) {
            const mat = meshRef.current.material as THREE.MeshPhysicalMaterial;

            // At 0.5 (Scanning), glow brightest? 
            // Or just graduate to Blue?
            // Let's graduate to Blue.
            mat.color.lerpColors(baseColor, activeColor, ease);
            mat.emissive.lerpColors(new THREE.Color("#000000"), activeColor, ease);
            mat.emissiveIntensity = ease * 0.5;
        }
    });

    return (
        <mesh ref={meshRef} castShadow receiveShadow>
            {/* THIN BOX = DOCUMENT PAPER Shape */}
            <boxGeometry args={[1.2, 1.6, 0.05]} />
            <meshPhysicalMaterial
                color={color}
                transmission={0.2} // Slight frost
                opacity={0.9}
                metalness={0.1}
                roughness={0.4} // Paper-like
                thickness={0.5}
                clearcoat={0.5}
            />
        </mesh>
    );
};

export const DataResurrectionScene = ({ progress }: { progress: MotionValue<number> }) => {
    const { camera } = useThree();

    // Camera Dolly: Zoom in to read the papers
    useFrame(() => {
        const p = progress.get();
        // Move from far (Chaos view) to close (Dashboard view)
        const targetZ = THREE.MathUtils.lerp(20, 12, p);
        camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetZ, 0.05);
    });

    const shardCount = 100;
    const shards = useMemo(() => {
        const items = [];
        const cols = 10;
        const rows = 10;
        const spacingX = 1.4;
        const spacingY = 1.8;
        const offsetX = (cols * spacingX) / 2;
        const offsetY = (rows * spacingY) / 2;

        for (let i = 0; i < shardCount; i++) {
            // Target: PLANAR GRID (Dashboard Interface)
            const x = (i % cols) * spacingX - offsetX;
            const y = (Math.floor(i / cols)) * spacingY - offsetY;
            const z = 0; // Flat plane

            // Start: CHAOS CLOUD
            const startX = (Math.random() - 0.5) * 50;
            const startY = (Math.random() - 0.5) * 50;
            const startZ = (Math.random() - 0.5) * 30; // Deep depth

            items.push({
                startPos: [startX, startY, startZ] as [number, number, number],
                endPos: [x, y, z] as [number, number, number],
                rotationSpeed: [Math.random() * 2, Math.random() * 2, Math.random() * 2] as [number, number, number],
                color: "#f8fafc",
            });
        }
        return items;
    }, []);

    return (
        <>
            <ambientLight intensity={0.5} />
            <pointLight position={[0, 0, 10]} intensity={1.0} color="#ffffff" />
            <pointLight position={[10, 10, 10]} intensity={1.5} color="#3b82f6" />

            {/* Data Dust - Particles */}
            <Sparkles count={150} scale={25} size={2} speed={0.5} opacity={0.3} color="#60a5fa" />

            <Float speed={2} rotationIntensity={0.2} floatIntensity={0.2}>
                <group>
                    {shards.map((s, i) => (
                        <DocumentShard
                            key={i}
                            progress={progress}
                            startPos={s.startPos}
                            endPos={s.endPos}
                            rotationSpeed={s.rotationSpeed}
                            color={s.color}
                        />
                    ))}
                </group>
            </Float>
        </>
    );
};
