import React, { useEffect, useRef } from 'react';

export default function AcademicMeshCanvas({ darkMode }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    let width = (canvas.width = canvas.parentElement.offsetWidth);
    let height = (canvas.height = canvas.parentElement.offsetHeight);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.offsetWidth;
      height = canvas.height = canvas.parentElement.offsetHeight;
    };

    window.addEventListener('resize', handleResize);

    // Academic Paper Nodes definition
    const paperTopics = [
      'Deep Learning in Healthcare',
      'PRISMA Systematic Review',
      'Transformer Attention Models',
      'Citation Snowballing Graph',
      'Clinical Trial Synthesis',
      'Research Gap Matrix',
      'Scopus Verified Q1 Index',
      'Grounded Evidence Trail',
      'Meta-Analysis Pooling',
      'Biomedical NLP Embeddings'
    ];

    const nodeCount = Math.min(Math.floor((width * height) / 10000), 55);
    const nodes = [];

    // Mouse tracker
    const mouse = {
      x: null,
      y: null,
      radius: 170
    };

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = null;
      mouse.y = null;
    };

    canvas.parentElement.addEventListener('mousemove', handleMouseMove);
    canvas.parentElement.addEventListener('mouseleave', handleMouseLeave);

    // Initialize nodes
    for (let i = 0; i < nodeCount; i++) {
      const isHub = i < 6; // First 6 are major paper hubs
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        radius: isHub ? Math.random() * 3 + 4 : Math.random() * 2 + 2,
        isHub,
        label: isHub ? paperTopics[i % paperTopics.length] : null,
        citations: Math.floor(Math.random() * 200 + 40),
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.03 + Math.random() * 0.02
      });
    }

    // Packet animation along citation lines
    const packets = [];
    for (let k = 0; k < 15; k++) {
      packets.push({
        from: Math.floor(Math.random() * nodeCount),
        to: Math.floor(Math.random() * nodeCount),
        progress: Math.random(),
        speed: 0.005 + Math.random() * 0.008
      });
    }

    // Main animation loop
    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // 1. Move & Update Nodes
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];

        node.x += node.vx;
        node.y += node.vy;
        node.pulse += node.pulseSpeed;

        if (node.x < 20 || node.x > width - 20) node.vx *= -1;
        if (node.y < 20 || node.y > height - 20) node.vy *= -1;

        // Mouse gravity / repulsion
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - node.x;
          const dy = mouse.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            const angle = Math.atan2(dy, dx);
            node.x -= Math.cos(angle) * force * 2;
            node.y -= Math.sin(angle) * force * 2;

            // Electric connection to mouse
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.strokeStyle = `rgba(96, 165, 250, ${(1 - dist / mouse.radius) * 0.5})`;
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }
        }

        // Draw connections between nodes (Citation graph)
        for (let j = i + 1; j < nodes.length; j++) {
          const node2 = nodes[j];
          const dx = node.x - node2.x;
          const dy = node.y - node2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxDist = 135;

          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * 0.28;
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(node2.x, node2.y);
            ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
            ctx.lineWidth = node.isHub || node2.isHub ? 1.2 : 0.7;
            ctx.stroke();
          }
        }
      }

      // 2. Draw Moving Citation Data Packets (Photons moving along citation links)
      for (let k = 0; k < packets.length; k++) {
        const pkt = packets[k];
        pkt.progress += pkt.speed;
        if (pkt.progress >= 1) {
          pkt.progress = 0;
          pkt.from = Math.floor(Math.random() * nodeCount);
          pkt.to = Math.floor(Math.random() * nodeCount);
        }

        const n1 = nodes[pkt.from];
        const n2 = nodes[pkt.to];
        if (n1 && n2) {
          const px = n1.x + (n2.x - n1.x) * pkt.progress;
          const py = n1.y + (n2.y - n1.y) * pkt.progress;

          ctx.beginPath();
          ctx.arc(px, py, 2, 0, Math.PI * 2);
          ctx.fillStyle = '#38BDF8';
          ctx.shadowBlur = 10;
          ctx.shadowColor = '#38BDF8';
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }

      // 3. Draw Paper Nodes & Floating Labels
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        const pulseFactor = Math.sin(node.pulse) * 0.3 + 1;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * pulseFactor, 0, Math.PI * 2);
        ctx.fillStyle = node.isHub ? '#60A5FA' : '#3B82F6';
        ctx.shadowBlur = node.isHub ? 16 : 8;
        ctx.shadowColor = '#60A5FA';
        ctx.fill();
        ctx.shadowBlur = 0;

        // Draw Paper Node Ring
        if (node.isHub) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, (node.radius + 5) * pulseFactor, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(147, 197, 253, 0.4)';
          ctx.lineWidth = 1;
          ctx.stroke();

          // Render Floating Academic Paper Label
          if (node.label && width > 768) {
            ctx.font = '10px "Plus Jakarta Sans", sans-serif';
            ctx.fillStyle = 'rgba(224, 242, 254, 0.85)';
            ctx.fillText(`📄 ${node.label}`, node.x + 12, node.y + 3);
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (canvas.parentElement) {
        canvas.parentElement.removeEventListener('mousemove', handleMouseMove);
        canvas.parentElement.removeEventListener('mouseleave', handleMouseLeave);
      }
      cancelAnimationFrame(animationFrameId);
    };
  }, [darkMode]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
      {/* Background Animated Gradient Aura Blobs */}
      <div className="absolute top-1/4 left-1/4 w-[450px] h-[450px] bg-blue-600/20 rounded-full blur-[120px] animate-pulse duration-1000" />
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] bg-indigo-600/20 rounded-full blur-[120px] animate-pulse delay-700 duration-1000" />
      <div className="absolute top-1/2 right-10 w-[350px] h-[350px] bg-sky-500/15 rounded-full blur-[100px] animate-pulse delay-300 duration-1000" />

      {/* Cyber Grid Lines */}
      <div 
        className="absolute inset-0 opacity-[0.05] dark:opacity-[0.08] bg-[linear-gradient(to_right,#3b82f6_1px,transparent_1px),linear-gradient(to_bottom,#3b82f6_1px,transparent_1px)] bg-[size:3.5rem_3.5rem]" 
      />

      {/* Interactive Academic Canvas */}
      <canvas ref={canvasRef} className="w-full h-full block opacity-85 dark:opacity-95" />
    </div>
  );
}
