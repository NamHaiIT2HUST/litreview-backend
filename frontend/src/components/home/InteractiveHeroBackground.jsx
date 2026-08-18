import React, { useEffect, useRef } from 'react';

export default function InteractiveHeroBackground({ darkMode }) {
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

    // Particle nodes definition
    const particleCount = Math.min(Math.floor((width * height) / 9000), 75);
    const particles = [];

    const mouse = {
      x: null,
      y: null,
      radius: 140
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

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.7,
        vy: (Math.random() - 0.5) * 0.7,
        radius: Math.random() * 2 + 1.5,
        baseColor: darkMode ? 'rgba(59, 130, 246, 0.7)' : 'rgba(37, 99, 235, 0.6)',
      });
    }

    // Animation loop
    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw and update particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Move
        p.x += p.vx;
        p.y += p.vy;

        // Bounce on edges
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Mouse interaction (gently push away or connect)
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            const angle = Math.atan2(dy, dx);
            p.x -= Math.cos(angle) * force * 1.5;
            p.y -= Math.sin(angle) * force * 1.5;

            // Draw line to mouse
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.strokeStyle = darkMode 
              ? `rgba(96, 165, 250, ${(1 - dist / mouse.radius) * 0.4})` 
              : `rgba(37, 99, 235, ${(1 - dist / mouse.radius) * 0.35})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }

        // Draw particle dot with glow
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = darkMode ? '#60A5FA' : '#2563EB';
        ctx.shadowBlur = 8;
        ctx.shadowColor = darkMode ? 'rgba(96, 165, 250, 0.8)' : 'rgba(37, 99, 235, 0.5)';
        ctx.fill();
        ctx.shadowBlur = 0; // reset

        // Connect nearby particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxDist = 110;

          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * (darkMode ? 0.25 : 0.18);
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = darkMode ? `rgba(96, 165, 250, ${alpha})` : `rgba(37, 99, 235, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
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
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/15 dark:bg-blue-600/20 rounded-full blur-3xl animate-pulse duration-1000" />
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-500/10 dark:bg-indigo-600/15 rounded-full blur-3xl animate-pulse delay-700 duration-1000" />
      <div className="absolute top-1/2 right-10 w-72 h-72 bg-sky-400/10 dark:bg-sky-500/15 rounded-full blur-3xl animate-pulse delay-300 duration-1000" />

      {/* Cyber Grid Pattern Lines */}
      <div 
        className={`absolute inset-0 opacity-[0.04] dark:opacity-[0.07] ${
          darkMode 
            ? 'bg-[linear-gradient(to_right,#60a5fa_1px,transparent_1px),linear-gradient(to_bottom,#60a5fa_1px,transparent_1px)]' 
            : 'bg-[linear-gradient(to_right,#2563eb_1px,transparent_1px),linear-gradient(to_bottom,#2563eb_1px,transparent_1px)]'
        } bg-[size:4rem_4rem]`} 
      />

      {/* Interactive Canvas */}
      <canvas ref={canvasRef} className="w-full h-full block opacity-70 dark:opacity-90" />
    </div>
  );
}
