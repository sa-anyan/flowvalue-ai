"use client";
import { useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, Line, OrbitControls } from "@react-three/drei";
import { CanvasTexture } from "three";
export type FlowNode = {
  id: string;
  label: string;
  kind: string;
  position: { x: number; y: number };
};
export type FlowEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
};
function Label({ text }: { text: string }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 96;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, 512, 96);
    context.fillStyle = "#234f39";
    context.font = "bold 30px Arial";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text.slice(0, 32), 256, 48, 490);
    return new CanvasTexture(canvas);
  }, [text]);
  useEffect(() => () => texture.dispose(), [texture]);
  return (
    <sprite position={[0, 1.5, 0]} scale={[2.1, 0.39, 1]}>
      <spriteMaterial map={texture} depthTest={false} />
    </sprite>
  );
}
export default function Scene({
  nodes,
  edges,
  selected,
  onSelect,
}: {
  nodes: FlowNode[];
  edges: FlowEdge[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const centerX = nodes.length
      ? nodes.reduce((a, n) => a + n.position.x, 0) / nodes.length
      : 0,
    centerY = nodes.length
      ? nodes.reduce((a, n) => a + n.position.y, 0) / nodes.length
      : 0;
  const point = (n: FlowNode): [number, number, number] => [
    (n.position.x - centerX) / 100,
    0,
    -(n.position.y - centerY) / 100,
  ];
  return (
    <Canvas
      camera={{ position: [4, 9, 12], fov: 45 }}
      frameloop="demand"
      fallback={<div>3D requires WebGL. Select 2D to inspect the flow.</div>}
    >
      <color attach="background" args={["#f4f7f0"]} />
      <ambientLight intensity={1.5} />
      <directionalLight position={[5, 10, 3]} intensity={2} />
      <gridHelper args={[100, 100, "#c4d4bc", "#e3eadf"]} />
      <Bounds fit clip observe margin={1.4}>
        {edges.map((e) => {
          const from = nodes.find((n) => n.id === e.source),
            to = nodes.find((n) => n.id === e.target);
          return from && to ? (
            <Line
              key={e.id}
              points={[point(from), point(to)]}
              color="#729a77"
              lineWidth={2}
            />
          ) : null;
        })}
        {nodes.map((n) => (
          <group key={n.id} position={point(n)}>
            <mesh
              position={[0, 0.5, 0]}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(n.id);
              }}
            >
              {n.kind === "vessel" || n.kind === "reactor" ? (
                <cylinderGeometry args={[0.38, 0.38, 1.3, 24]} />
              ) : (
                <boxGeometry
                  args={[n.kind === "boundary" ? 0.45 : 1, 0.7, 0.65]}
                />
              )}
              <meshStandardMaterial
                color={
                  selected === n.id
                    ? "#d9aa5e"
                    : n.kind === "boundary"
                      ? "#9db4a3"
                      : "#36684e"
                }
                roughness={0.45}
              />
            </mesh>
            <Label text={n.label} />
          </group>
        ))}
      </Bounds>
      <OrbitControls makeDefault target={[0, 0, 0]} />
    </Canvas>
  );
}
