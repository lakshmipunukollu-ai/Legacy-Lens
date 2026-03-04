"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";

type GraphNode = { id: string; type: string; file: string };
type GraphEdge = { source: string; target: string; type: string };

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick: (nodeName: string) => void;
  width?: number;
  height?: number;
};

const FILE_COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16",
];

export default function DependencyGraph({
  nodes,
  edges,
  onNodeClick,
  width = 800,
  height = 600,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const fileToColor = new Map<string, string>();
    const getColor = (file: string) => {
      if (!fileToColor.has(file)) {
        fileToColor.set(file, FILE_COLORS[fileToColor.size % FILE_COLORS.length]);
      }
      return fileToColor.get(file)!;
    };

    const g = d3.select(svgRef.current);
    g.selectAll("*").remove();

    const nodeData = nodes.map((n) => ({ ...n })) as (d3.SimulationNodeDatum & { id: string; file: string; type: string })[];
    const linkData = edges.map((e) => ({ ...e }));

    const simulation = d3
      .forceSimulation(nodeData)
      .force(
        "link",
        d3.forceLink(linkData).id((d) => (d as { id: string }).id)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(40));

    const defs = g.append("defs");
    defs
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M 0,-5 L 10 ,0 L 0,5")
      .attr("fill", "#6b7280");

    const link = g
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(linkData)
      .join("line")
      .attr("stroke", "#6b7280")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrowhead)");

    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodeData)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3.drag<SVGGElement, (typeof nodeData)[0]>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x ?? 0;
            d.fy = d.y ?? 0;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as never
      );

    node
      .append("circle")
      .attr("r", 20)
      .attr("fill", (d) => getColor(d.file))
      .attr("stroke", "#374151")
      .attr("stroke-width", 2);

    node
      .append("text")
      .text((d) => d.id)
      .attr("x", 0)
      .attr("y", 0)
      .attr("dy", "0.35em")
      .attr("text-anchor", "middle")
      .attr("fill", "#f9fafb")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .clone(true)
      .lower()
      .attr("stroke", "#111")
      .attr("stroke-width", 3);

    node.on("click", (event, d) => {
      event.stopPropagation();
      onNodeClick(d.id);
    });

    node.on("mouseover", function (event, d) {
      d3.select(this).select("circle").attr("stroke-width", 4).attr("stroke", "#60a5fa");
      const nodeId = d.id;
      link.attr("stroke-opacity", (l: unknown) => {
        const link = l as { source: { id?: string } | string; target: { id?: string } | string };
        const srcId = typeof link.source === "object" && link.source ? (link.source as { id?: string }).id : link.source;
        const tgtId = typeof link.target === "object" && link.target ? (link.target as { id?: string }).id : link.target;
        return srcId === nodeId || tgtId === nodeId ? 1 : 0.15;
      });
    });

    node.on("mouseout", function () {
      d3.select(this).select("circle").attr("stroke-width", 2).attr("stroke", "#374151");
      link.attr("stroke-opacity", 0.6);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d as { source: { x?: number }; target: { x?: number } }).source.x ?? 0)
        .attr("y1", (d) => (d as { source: { y?: number }; target: { y?: number } }).source.y ?? 0)
        .attr("x2", (d) => (d as { source: { x?: number }; target: { x?: number } }).target.x ?? 0)
        .attr("y2", (d) => (d as { source: { y?: number }; target: { y?: number } }).target.y ?? 0);

      node.attr("transform", (d) => `translate(${(d as { x?: number; y?: number }).x ?? 0},${(d as { x?: number; y?: number }).y ?? 0})`);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, width, height, onNodeClick]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-[600px] items-center justify-center rounded-lg border border-gray-700 bg-gray-900 text-gray-500">
        No dependency relationships found in retrieved chunks. Try a more specific query.
      </div>
    );
  }

  const fileSet = new Set(nodes.map((n) => n.file));
  const fileColors = new Map<string, string>();
  FILE_COLORS.forEach((c, i) => {
    const files = Array.from(fileSet);
    if (files[i]) fileColors.set(files[i], c);
  });

  return (
    <div ref={containerRef} className="space-y-3">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="rounded-lg border border-gray-700 bg-gray-900"
      />
      <div className="flex flex-wrap gap-3 text-xs">
        {Array.from(fileSet).map((file, i) => (
          <span key={file} className="flex items-center gap-1.5">
            <span
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: FILE_COLORS[i % FILE_COLORS.length] }}
            />
            {file}
          </span>
        ))}
      </div>
    </div>
  );
}
