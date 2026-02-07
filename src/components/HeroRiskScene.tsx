import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import { Float, Environment } from "@react-three/drei";
import * as THREE from "three";

const RiskShard = ({ position, rotationSpeed, color, scale }: any) => {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!meshRef.current) return;
        // Slow, ominous rotation
        meshRef.current.rotation.x += rotationSpeed[0] * delta * 0.2;
        meshRef.current.rotation.y += rotationSpeed[1] * delta * 0.2;
        meshRef.current.rotation.z += rotationSpeed[2] * delta * 0.1;
    });

    return (
        <mesh ref={meshRef} position={position} castShadow>
            {/* Sharp octahedron shapes */}
            <octahedronGeometry args={[scale, 0]} />
            <meshPhysicalMaterial
                color={color}
                emissive={color}
                emissiveIntensity={0.5} // Self-illuminated to be seen in dark
                transmission={0.2} // Less transparent, more solid
                opacity={1}
                roughness={0.1}
                metalness={0.8} // Metallic shine
                thickness={2}
                clearcoat={1}
            />
        </mesh>
    );
};

export const HeroRiskScene = () => {
    const count = 40; // Increased count for visibility
    const shards = useMemo(() => {
        const items = [];
        for (let i = 0; i < count; i++) {
            items.push({
                position: [
                    (Math.random() - 0.5) * 20, // Tighter Spread X
                    (Math.random() - 0.5) * 12, // Tighter Spread Y
                    (Math.random() - 0.5) * 8 - 2, // Z depth
                ] as [number, number, number],
                rotationSpeed: [Math.random(), Math.random(), Math.random()],
                // Lighter colors for visibility: Blue-300, Slate-300, and Red-400
                color: Math.random() > 0.9 ? "#f87171" : Math.random() > 0.5 ? "#94a3b8" : "#60a5fa",
                scale: 0.3 + Math.random() * 0.5,
            });
        }
        return items;
    }, []);

    return (
        <>
            {/* Essential for Glass Material visibility */}
            <Environment preset="city" />

            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={2.0} color="#3b82f6" />
            <pointLight position={[-10, -5, 5]} intensity={3.0} color="#ef4444" />

            <Float speed={2} rotationIntensity={1} floatIntensity={1} floatingRange={[-0.5, 0.5]}>
                <group>
                    {shards.map((s, i) => (
                        <RiskShard
                            key={i}
                            position={s.position}
                            rotationSpeed={s.rotationSpeed}
                            color={s.color}
                            scale={s.scale}
                        />
                    ))}
                </group>
            </Float>
        </>
    );
};
