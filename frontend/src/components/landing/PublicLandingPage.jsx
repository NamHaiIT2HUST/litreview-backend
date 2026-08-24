import React, { useState, useEffect, useRef } from 'react';
import {
  BookOpen, Sparkles, Search, Layers, ShieldCheck, ArrowRight,
  CheckCircle2, Bot, Database, Zap, FileText, Check, ChevronRight,
  Sun, Moon, Languages, Users, BarChart2, Star, Key, Target,
  Cpu, FileCheck, HelpCircle, ExternalLink, Activity, Award,
  Compass, ArrowUpRight, Copy, CheckCheck, Play, Pause, RotateCcw,
  Table, SplitSquareVertical, AlertCircle, FileCode, CheckSquare,
  Sparkle, ChevronDown, MessageSquare, Download, Share2
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useDarkMode } from '../../contexts/DarkModeContext';

import member1Img from '../../assets/member1.jpeg';
import member2Img from '../../assets/member2.jpg';
import member3Img from '../../assets/member3.JPG';
import member4Img from '../../assets/member4.jpg';

// ── Minimalist Clean Interactive Constellation Canvas with Parallax ──────
function AcademicConstellationCanvas({ darkMode, scrollY = 0 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const mouse = { x: width / 2, y: height / 2, radius: 200, isHovering: false };

    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.isHovering = true;
    };

    const handleMouseLeave = () => {
      mouse.isHovering = false;
    };

    const pulses = [];
    const handleClick = (e) => {
      pulses.push({
        x: e.clientX,
        y: e.clientY,
        radius: 10,
        maxRadius: 220,
        opacity: 0.7
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('click', handleClick);

    // Minimalist node distribution (clear, spaced out, larger nodes)
    const particleCount = Math.min(Math.floor((width * height) / 38000), 32);
    const particles = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 2.5 + 2.5,
        isMajorHub: i % 4 === 0,
        color: i % 3 === 0 ? '#6366F1' : i % 3 === 1 ? '#10B981' : '#8B5CF6'
      });
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Render expanding smooth aura ripples
      for (let pIdx = pulses.length - 1; pIdx >= 0; pIdx--) {
        const p = pulses[pIdx];
        p.radius += 3.2;
        p.opacity -= 0.012;

        if (p.opacity <= 0 || p.radius >= p.maxRadius) {
          pulses.splice(pIdx, 1);
          continue;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.strokeStyle = darkMode
          ? `rgba(99, 102, 241, ${p.opacity * 0.45})`
          : `rgba(79, 70, 229, ${p.opacity * 0.3})`;
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }

      // Draw lines and nodes
      for (let i = 0; i < particles.length; i++) {
        const pt = particles[i];

        pt.x += pt.vx;
        pt.y += pt.vy;

        if (pt.x < 0 || pt.x > width) pt.vx *= -1;
        if (pt.y < 0 || pt.y > height) pt.vy *= -1;

        // Subtle mouse attraction
        if (mouse.isHovering) {
          const dx = mouse.x - pt.x;
          const dy = mouse.y - pt.y;
          const dist = Math.hypot(dx, dy);

          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            const angle = Math.atan2(dy, dx);
            pt.x -= Math.cos(angle) * force * 0.9;
            pt.y -= Math.sin(angle) * force * 0.9;

            ctx.beginPath();
            ctx.moveTo(pt.x, pt.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.strokeStyle = darkMode
              ? `rgba(129, 140, 248, ${(1 - dist / mouse.radius) * 0.45})`
              : `rgba(79, 70, 229, ${(1 - dist / mouse.radius) * 0.28})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }

        // Connection lines between nearby nodes
        for (let j = i + 1; j < particles.length; j++) {
          const pt2 = particles[j];
          const dist = Math.hypot(pt.x - pt2.x, pt.y - pt2.y);
          const maxDist = 180;

          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * (darkMode ? 0.35 : 0.2);
            ctx.beginPath();
            ctx.moveTo(pt.x, pt.y);
            ctx.lineTo(pt2.x, pt2.y);
            ctx.strokeStyle = darkMode ? `rgba(99, 102, 241, ${alpha})` : `rgba(79, 70, 229, ${alpha})`;
            ctx.lineWidth = pt.isMajorHub && pt2.isMajorHub ? 2 : 1;
            ctx.stroke();
          }
        }

        // Draw soft ambient halo
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, pt.isMajorHub ? pt.radius * 3 : pt.radius * 2, 0, Math.PI * 2);
        ctx.fillStyle = darkMode ? 'rgba(99, 102, 241, 0.12)' : 'rgba(79, 70, 229, 0.08)';
        ctx.fill();

        // Draw main node
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, pt.radius, 0, Math.PI * 2);
        ctx.fillStyle = pt.color;
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('click', handleClick);
      cancelAnimationFrame(animationFrameId);
    };
  }, [darkMode]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        transform: `translateY(${Math.min(scrollY * 0.08, 100)}px)`,
        transition: 'transform 0.1s linear'
      }}
      className="fixed inset-0 pointer-events-none z-0 opacity-70 transition-opacity duration-1000"
    />
  );
}

// ── Professional Multi-Variant Scroll Reveal Observer Component ───────────
function ScrollReveal({ children, className = '', delay = 0, threshold = 0.12, variant = 'up' }) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold, rootMargin: '0px 0px -40px 0px' }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [threshold]);

  const variantClass =
    variant === 'left'
      ? `reveal-left-init ${isVisible ? 'reveal-left-visible' : ''}`
      : variant === 'right'
      ? `reveal-right-init ${isVisible ? 'reveal-right-visible' : ''}`
      : variant === 'zoom'
      ? `reveal-zoom-init ${isVisible ? 'reveal-zoom-visible' : ''}`
      : variant === 'cascade'
      ? `reveal-cascade-init ${isVisible ? 'reveal-cascade-visible' : ''}`
      : variant === 'morph'
      ? `reveal-morph-init ${isVisible ? 'reveal-morph-visible' : ''}`
      : `reveal-up-init ${isVisible ? 'reveal-up-visible' : ''}`;

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`${variantClass} ${className}`}
    >
      {children}
    </div>
  );
}

// ── Animated Counter on Viewport Scroll ───────────────────────────────────
function AnimatedCounter({ target, duration = 1600, suffix = '', prefix = '' }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setCount(parseInt(target, 10) || 0);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.2 }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [started, target]);

  useEffect(() => {
    if (!started) return;
    let startTimestamp = null;
    const numTarget = parseInt(target, 10) || 0;

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeProgress * numTarget));

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setCount(numTarget);
      }
    };

    const animId = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(animId);
  }, [started, target, duration]);

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}{count}{suffix}
    </span>
  );
}

// ── Realistic Multi-Topic Presets ─────────────────────────────────────────
const TOPIC_PRESETS = {
  ecg: {
    label: '🩺 Deep Learning ECG Arrhythmia',
    query: '1D-CNN and Transformer architectures for real-time arrhythmia detection in ECG signals',
    pico: {
      p: 'Bệnh nhân có nguy cơ loạn nhịp tim từ tín hiệu điện tâm đồ đa đạo trình (Multi-lead ECG).',
      i: 'Kiến trúc học sâu: 1D-CNN, Spatial-Temporal Attention và Vision Transformer.',
      c: 'Mô hình học máy cổ điển (SVM, Random Forest, Rule-based QRS detection).',
      o: 'Độ nhạy (Sensitivity ≥ 98%), F1-Score, khả năng chẩn đoán thời gian thực trên thiết bị nhúng.',
      inclusion: 'Bài báo công bố 2022–2025; có mã nguồn/dataset chuẩn (MIT-BIH, PTB-XL); có đối chuẩn định lượng.',
      exclusion: 'Tài liệu không qua bình duyệt (preprints không kiểm chứng); bài khảo sát thuần túy; thiếu dữ liệu thực nghiệm.',
      booleanQuery: '("1D-CNN" OR "Transformer" OR "Deep Learning") AND ("ECG" OR "Arrhythmia") AND ("Attention" OR "Spatial-Temporal")',
    },
    rows: [
      { title: 'Automated arrhythmia classification using 1D convolutional neural network', venue: 'IEEE TBME 2023 · Scopus Q1', status: 'valid' },
      { title: 'Heuristic rule-based thresholding for QRS complex detection', venue: 'Preprint 2020 · No Code', status: 'criteria_excluded', tag: 'Không khớp Tiêu chí' },
      { title: 'Deep transformer networks for multi-lead electrocardiogram analysis', venue: 'Nature Sci Rep 2024 · Scopus Q1', status: 'valid' },
      { title: 'A survey on wearable IoT heart rate monitors without empirical evaluation', venue: 'Conference 2021', status: 'unverified', tag: 'Ngoài Scopus' },
      { title: 'Spatial-temporal attention networks for cardiac anomaly localization', venue: 'Biomed. Signal Process. 2024 · Scopus Q1', status: 'valid' },
      { title: 'Automated arrhythmia classification using 1D CNN (Duplicate entry)', venue: 'Google Scholar 2023', status: 'duplicate', tag: 'Trùng lặp' },
    ],
    summaryP1: 'Tổng hợp từ các bài báo Scopus Q1: Kiến trúc 1D-CNN kết hợp Attention đạt độ nhạy 98.6% trên tập MIT-BIH ',
    summaryCite1: { id: '[1]', title: 'Automated arrhythmia classification using 1D CNN', venue: 'IEEE TBME (Scopus Q1)', author: 'Wang et al., 2023', doi: '10.1109/TBME.2023.102', page: 'p.142', quote: '1D-CNN combined with Attention achieves 98.6% sensitivity on MIT-BIH, significantly outperforming legacy SVM classifiers.' },
    summaryP2: ', vượt trội hơn các mô hình phân loại SVM truyền thống. Mô hình Transformer đa kênh cho phép nắm bắt phụ thuộc dài hạn giữa các đạo trình ',
    summaryCite2: { id: '[2]', title: 'Deep transformer networks for multi-lead ECG', venue: 'Nature Sci Rep (Scopus Q1)', author: 'Ferreira et al., 2024', doi: '10.1038/s41598-024-512', page: 'p.89', quote: 'Multi-lead spatial-temporal transformer captures inter-lead dependencies with 97.9% overall accuracy on PTB-XL.' },
    summaryP3: ', kết hợp mạng không-thời gian giúp định vị chính xác vùng bất thường ',
    summaryCite3: { id: '[3]', title: 'Spatial-temporal attention networks for ECG', venue: 'Biomed. Signal Process. (Scopus Q1)', author: 'Nguyen et al., 2024', doi: '10.1016/j.bspc.2024.106', page: 'p.210', quote: 'Bi-LSTM with Attention achieves 98.1% sensitivity on CPSC 2018 with interpretability heatmaps.' },
    summaryP4: '. Điểm nghẽn chính nằm ở chi phí tính toán khi triển khai trên thiết bị nhúng thời gian thực.',
    matrix: [
      { author: 'Wang et al. (2023)', method: '1D-CNN + Channel Attention', dataset: 'MIT-BIH (48 records)', metrics: 'Accuracy: 98.6%, F1: 98.2%', gap: 'Chưa kiểm thử đa trung tâm trên thiết bị đeo' },
      { author: 'Ferreira et al. (2024)', method: 'Spatial-Temporal Transformer', dataset: 'PTB-XL (21,837 ECGs)', metrics: 'Accuracy: 97.9%, F1: 97.4%', gap: 'Chi phí tính toán cao trên bộ nhớ hạn chế' },
      { author: 'Nguyen et al. (2024)', method: 'Bi-LSTM + Multi-Head Attention', dataset: 'CPSC 2018 Benchmark', metrics: 'Sensitivity: 98.1%, Spec: 99.0%', gap: 'Khả năng giải thích (XAI) còn hạn chế' },
    ],
    gaps: [
      { title: 'Thiếu kiểm định đa trung tâm (Multi-center cross-validation)', desc: 'Phần lớn các nghiên cứu chỉ huấn luyện trên dataset đơn lẻ (MIT-BIH), độ chính xác giảm khi áp dụng trên bệnh viện thực tế.' },
      { title: 'Tối ưu hóa độ trễ tính toán trên thiết bị biên (Edge Devices)', desc: 'Cần các kỹ thuật nén mô hình (Knowledge Distillation) để chạy chẩn đoán tức thời trên vi điều khiển nhúng.' },
    ],
    ragSample: {
      question: 'Kiến trúc nào đạt độ nhạy cao nhất trên tập dữ liệu MIT-BIH và nguyên văn kết quả?',
      answer: 'Theo công bố của Wang et al. (2023) trên IEEE TBME (Scopus Q1), kiến trúc 1D-CNN kết hợp Channel Attention đạt độ nhạy cao nhất (98.6%) trên tập MIT-BIH, vượt trội hơn các mô hình phân loại SVM truyền thống.',
      pageAnchor: 'Wang et al., 2023 · IEEE TBME, p.142',
      quote: '"1D-CNN combined with Attention achieves 98.6% sensitivity on MIT-BIH, significantly outperforming legacy SVM classifiers."'
    },
    bibtex: `@article{wang2023automated,
  title={Automated arrhythmia classification using 1D convolutional neural network},
  author={Wang, Lin and Zhang, Wei and Liu, Chen},
  journal={IEEE Transactions on Biomedical Engineering},
  volume={70},
  number={4},
  pages={140--149},
  year={2023},
  publisher={IEEE},
  doi={10.1109/TBME.2023.102}
}`
  },
  llm: {
    label: '🧠 Chain-of-Thought in LLMs',
    query: 'chain-of-thought and tree-of-thoughts multi-step reasoning benchmarks in large language models',
    pico: {
      p: 'Mô hình ngôn ngữ lớn (LLMs như GPT-4, LLaMA-3, Claude) thực hiện các tác vụ suy luận nhiều bước.',
      i: 'Kỹ thuật Prompting cấu trúc: Chain-of-Thought (CoT), Tree-of-Thoughts (ToT), Self-Consistency.',
      c: 'Standard Zero-shot / Few-shot Direct Prompting.',
      o: 'Tỷ lệ giải bài toán chính xác trên GSM8K, MATH, SVAMP; giảm thiểu ảo giác suy luận.',
      inclusion: 'Các công trình NeurIPS, ICML, ICLR, ACL (2022–2025); có ablation study kiểm tra tính logic.',
      exclusion: 'Tài liệu hướng dẫn prompt không có benchmark học thuật; blog thương mại.',
      booleanQuery: '("Chain-of-Thought" OR "Tree-of-Thoughts" OR "Self-Consistency") AND ("Large Language Models" OR "LLMs") AND ("Reasoning" OR "GSM8K")',
    },
    rows: [
      { title: 'Chain-of-thought prompting elicits reasoning in large language models', venue: 'NeurIPS 2022 · Scopus Q1', status: 'valid' },
      { title: 'Simple customer service chatbot without logical evaluation', venue: 'Preprint 2022', status: 'criteria_excluded', tag: 'Không khớp Tiêu chí' },
      { title: 'Tree of thoughts: Deliberate problem solving with large language models', venue: 'NeurIPS 2023 · Scopus Q1', status: 'valid' },
      { title: 'General prompt tips for creative copywriting', venue: 'Blog 2023', status: 'unverified', tag: 'Ngoài Scopus' },
      { title: 'Self-consistency improves chain of thought reasoning in language models', venue: 'ICLR 2023 · Scopus Q1', status: 'valid' },
      { title: 'Chain-of-thought prompting elicits reasoning in LLMs (Duplicate)', venue: 'arXiv Mirror', status: 'duplicate', tag: 'Trùng lặp' },
    ],
    summaryP1: 'Tổng hợp từ các công bố NeurIPS & ICLR: Kỹ thuật Chain-of-Thought (CoT) cải thiện đáng kể độ chính xác toán học trên GSM8K ',
    summaryCite1: { id: '[1]', title: 'Chain-of-thought prompting in LLMs', venue: 'NeurIPS 2022 (Scopus Q1)', author: 'Wei et al., 2022', doi: '10.48550/arXiv.2201.11903', page: 'p.4', quote: 'CoT prompting dramatically improves multi-step reasoning accuracy on GSM8K from 17.9% to 60.1%.' },
    summaryP2: '. Kiến trúc Tree-of-Thoughts (ToT) mở rộng thành không gian tìm kiếm cây giúp giải các bài toán tổ hợp phức tạp ',
    summaryCite2: { id: '[2]', title: 'Tree of thoughts: Deliberate problem solving', venue: 'NeurIPS 2023 (Scopus Q1)', author: 'Yao et al., 2023', doi: '10.48550/arXiv.2305.10601', page: 'p.7', quote: 'ToT allows deliberate exploration with lookahead, increasing Game of 24 success rate from 4% to 74%.' },
    summaryP3: ', trong khi cơ chế Self-Consistency lấy mẫu đa lộ trình để loại bỏ lỗi suy luận đơn lẻ ',
    summaryCite3: { id: '[3]', title: 'Self-consistency improves CoT reasoning', venue: 'ICLR 2023 (Scopus Q1)', author: 'Wang et al., 2023', doi: '10.48550/arXiv.2203.11171', page: 'p.5', quote: 'Marginalizing out multiple reasoning paths improves accuracy consistently across arithmetic benchmarks by +17.9%.' },
    summaryP4: '. Thách thức lớn là sự bùng nổ số lượng token và chi phí API khi duyệt cây nhiều nhánh.',
    matrix: [
      { author: 'Wei et al. (2022)', method: 'Few-shot CoT Prompting', dataset: 'GSM8K, SVAMP, MATH', metrics: 'GSM8K: 17.9% → 60.1%', gap: 'Dễ bị sai dây chuyền ở bước trung gian' },
      { author: 'Yao et al. (2023)', method: 'Tree-of-Thoughts (ToT) Search', dataset: 'Game of 24, Creative Writing', metrics: 'Success rate: 4% → 74%', gap: 'Bùng nổ chi phí tính toán và token latency' },
      { author: 'Wang et al. (2023)', method: 'Self-Consistency Sampling', dataset: 'GSM8K, SVAMP, AQuA', metrics: 'GSM8K: +17.9% accuracy', gap: 'Độ đa dạng của mẫu câu trả lời chưa tối ưu' },
    ],
    gaps: [
      { title: 'Độ tin cậy của bước suy luận trung gian (Intermediate verification)', desc: 'Mô hình có thể đưa ra kết quả cuối đúng nhưng các bước suy luận trung gian chứa lỗi ngụy biện logic.' },
      { title: 'Chi phí tính toán và độ trễ khi tìm kiếm nhánh sâu', desc: 'Các thuật toán tìm kiếm cây (ToT, MCTS) tiêu tốn nhiều tài nguyên token cho các bài toán thời gian thực.' },
    ],
    ragSample: {
      question: 'Kỹ thuật Tree of Thoughts (ToT) vượt trội so với CoT truyền thống ở điểm nào?',
      answer: 'Theo Yao et al. (2023) tại NeurIPS, ToT mở rộng khả năng giải quyết vấn đề bằng cách tự đánh giá và quay lui (backtracking) trên cây suy luận, nâng tỷ lệ thành công của bài toán Game of 24 từ 4% lên 74%.',
      pageAnchor: 'Yao et al., 2023 · NeurIPS, p.7',
      quote: '"ToT allows deliberate exploration with lookahead, increasing Game of 24 success rate from 4% to 74%."'
    },
    bibtex: `@inproceedings{wei2022chain,
  title={Chain-of-thought prompting elicits reasoning in large language models},
  author={Wei, Jason and Wang, Xuezhi and Schuurmans, Dale and Bosma, Maarten and Chi, Ed and Le, Quoc and Zhou, Denny},
  booktitle={Advances in Neural Information Processing Systems (NeurIPS)},
  volume={35},
  pages={24824--24837},
  year={2022}
}`
  },
  robot: {
    label: '🤖 Autonomous Robot SLAM',
    query: 'deep reinforcement learning and visual-inertial SLAM for autonomous drone navigation in GPS-denied environments',
    pico: {
      p: 'Thiết bị bay tự hành (Micro Aerial Vehicles / Drones) di chuyển trong môi trường không có GPS (GPS-denied).',
      i: 'Kết hợp Visual-Inertial SLAM (VI-SLAM) với Deep Feature Tracking và Deep Reinforcement Learning (DRL).',
      c: 'Hệ thống định vị quán tính thuần túy (INS) hoặc ORB-SLAM truyền thống.',
      o: 'Độ trôi tích lũy (ATE RMSE < 0.05m), tần số điều khiển né vật cản > 50Hz, tỷ lệ sống sót trong không gian hẹp.',
      inclusion: 'Các công trình IEEE T-RO, ICRA, IROS, RSS (2023–2025); có kiểm chứng trên drone thực tế.',
      exclusion: 'Mô phỏng 2D đơn giản không tính động lực học vật lý; drone đồ chơi không gắn cảm biến IMU.',
      booleanQuery: '("Visual-Inertial SLAM" OR "VI-SLAM") AND ("Deep Reinforcement Learning" OR "DRL") AND ("Autonomous Drone" OR "GPS-denied")',
    },
    rows: [
      { title: 'Visual-inertial SLAM with deep feature tracking for micro aerial vehicles', venue: 'IEEE T-RO 2024 · Scopus Q1', status: 'valid' },
      { title: 'Simple 2D grid simulation for toy robots without physics', venue: 'Preprint 2021', status: 'criteria_excluded', tag: 'Không khớp Tiêu chí' },
      { title: 'End-to-end deep reinforcement learning for dynamic obstacle avoidance', venue: 'IEEE ICRA 2024 · Scopus Q1', status: 'valid' },
      { title: 'General hobby drones battery life analysis', venue: 'Conference 2022', status: 'unverified', tag: 'Ngoài Scopus' },
      { title: 'Real-time dense 3D mapping using neural radiance fields on edge GPUs', venue: 'IEEE IROS 2024 · Scopus Q1', status: 'valid' },
      { title: 'Visual-inertial SLAM with deep feature tracking (Duplicate)', venue: 'Scholar Mirror', status: 'duplicate', tag: 'Trùng lặp' },
    ],
    summaryP1: 'Tổng hợp từ các nghiên cứu IEEE T-RO và ICRA: Kết hợp Deep Feature Tracking vào Visual-Inertial SLAM giúp duy trì quỹ đạo chính xác khi bay tốc độ cao ',
    summaryCite1: { id: '[1]', title: 'Visual-inertial SLAM for MAVs', venue: 'IEEE T-RO 2024 (Scopus Q1)', author: 'Zhang et al., 2024', doi: '10.1109/TRO.2024.312', page: 'p.18', quote: 'Deep feature tracking maintains feature persistence through aggressive maneuvers with ATE RMSE of 0.042m.' },
    summaryP2: '. Mô hình học tăng cường sâu (Deep RL) cho phép phản xạ né vật cản động với tần số điều khiển > 50Hz ',
    summaryCite2: { id: '[2]', title: 'End-to-end DRL obstacle avoidance', venue: 'IEEE ICRA 2024 (Scopus Q1)', author: 'Kaufmann et al., 2024', doi: '10.1109/ICRA.2024.108', page: 'p.112', quote: 'End-to-end policy directly maps camera observations to motor commands with 98.2% collision-free rate at 10 m/s.' },
    summaryP3: ', trong khi mạng NeRF tái tạo bản đồ 3D đậm đặc thời gian thực trên chip đồ họa nhúng ',
    summaryCite3: { id: '[3]', title: 'Real-time dense 3D NeRF mapping', venue: 'IEEE IROS 2024 (Scopus Q1)', author: 'Rosinol et al., 2024', doi: '10.1109/IROS.2024.954', page: 'p.45', quote: 'Real-time dense 3D reconstruction operates at 30 FPS on Nvidia Jetson Orin.' },
    summaryP4: '. Khó khăn lớn nhất là hiện tượng trôi dạt (drift) tích lũy trong môi trường thiếu ánh sáng hoặc không có texture.',
    matrix: [
      { author: 'Zhang et al. (2024)', method: 'Deep Feature VI-SLAM', dataset: 'EuRoC MAV, Real Drone Flight', metrics: 'ATE RMSE: 0.042m, Latency: 18ms', gap: 'Độ nhạy cao khi ánh sáng thay đổi đột ngột' },
      { author: 'Kaufmann et al. (2024)', method: 'Model-free DRL (PPO)', dataset: 'Flightmare Simulator & Real Quad', metrics: 'Success rate: 98.2% @ 10m/s', gap: 'Sim-to-real transfer trong môi trường gió mạnh' },
      { author: 'Rosinol et al. (2024)', method: 'Instant NeRF-SLAM', dataset: 'TUM-VI, Replica Benchmark', metrics: 'PSNR: 31.4 dB @ 30 FPS', gap: 'Tiêu thụ năng lượng cao trên pin drone' },
    ],
    gaps: [
      { title: 'Khoảng cách Sim-to-Real trong điều kiện nhiễu động phức tạp', desc: 'Chính sách RL huấn luyện trong môi trường mô phỏng thường bị giảm hiệu năng khi đối mặt gió giật thực tế.' },
      { title: 'Khả năng đóng vòng lặp (Loop Closure) trong môi trường nghèo đặc trưng', desc: 'Các thuật toán SLAM dễ mất dấu khi hoạt động trong đường hầm hoặc môi trường thiếu texture thị giác.' },
    ],
    ragSample: {
      question: 'Chính sách Deep RL của Kaufmann et al. đạt tốc độ phản xạ và hiệu năng bay thế nào?',
      answer: 'Theo công bố tại IEEE ICRA 2024, mô hình Deep RL ánh xạ trực tiếp hình ảnh camera thành tín hiệu điều khiển động cơ với tần số > 50Hz, đạt tỷ lệ bay không va chạm 98.2% ở vận tốc 10 m/s.',
      pageAnchor: 'Kaufmann et al., 2024 · IEEE ICRA, p.112',
      quote: '"End-to-end policy directly maps camera observations to motor commands with 98.2% collision-free rate at 10 m/s."'
    },
    bibtex: `@article{zhang2024visual,
  title={Visual-inertial SLAM with deep feature tracking for micro aerial vehicles},
  author={Zhang, Tao and Gao, Wei and Shen, Shaojie},
  journal={IEEE Transactions on Robotics (T-RO)},
  volume={40},
  pages={1120--1135},
  year={2024},
  publisher={IEEE}
}`
  }
};

const DICTIONARY = {
  vi: {
    nav: {
      simulator: 'Mô phỏng',
      agents: 'Quy trình 4 Bước',
      matrix: 'So sánh Bài báo',
      prisma: 'Chuẩn PRISMA',
      demoProfiles: 'Tài khoản Mẫu',
      faq: 'Hỏi đáp',
      team: 'Đội ngũ',
      acknowledgments: 'Lời cảm ơn',
      login: 'Đăng nhập',
      startFree: 'Bắt đầu Miễn phí',
    },
    hero: {
      badge: 'QUY TRÌNH TỔNG QUAN TÀI LIỆU KHOA HỌC (SLR)',
      title1: 'Tự động hóa Tổng quan Tài liệu',
      titleHighlight: 'Chuẩn Scopus & PRISMA',
      desc: 'Khai phóng hàng trăm giờ đọc thủ công: Tự động định hình PICO, sàng lọc Scopus, trích xuất PDF và dựng ma trận so sánh phương pháp 100% neo trên DOI thực tế.',
      btnDemo: 'Trải nghiệm Không gian Mẫu',
      btnSimulate: 'Xem Mô phỏng SLR',
      trust1: '100% DOI Thật',
      trust2: 'Chuẩn mực PRISMA',
      trust3: 'Đối chiếu Scopus Q1',
      trust4: 'Xuất BibTeX / CSV',
      previewBadge: 'PHIÊN TỔNG HỢP TRỰC QUAN · CHUẨN PRISMA',
      previewStatus: 'Scopus Q1 Verified',
      previewQuery: '1D-CNN + Spatial-Temporal Attention for Arrhythmia Detection',
      previewQuote: 'Kiến trúc 1D-CNN kết hợp Attention đạt độ nhạy 98.6% trên tập MIT-BIH, vượt trội hơn các mô hình phân loại truyền thống.',
      previewCitation: 'Wang et al., 2023 · IEEE TBME, Vol. 70, p.142',
      previewStatRecords: '100+ Bản ghi',
      previewStatFiltered: '14 Scopus Q1',
      previewStatIncluded: '4 Trong Ma trận',
    },
    demo: {
      badge: 'TRÌNH MÔ PHỎNG SÀNG LỌC & TỔNG HỢP THỜI GIAN THỰC',
      title: 'Trực quan hóa Quy trình Tự động hóa Systematic Review',
      desc: 'Chọn một chủ đề nghiên cứu mẫu bên dưới để xem hệ thống phân tích khung PICO, đối chiếu Scopus và loại bỏ nguồn không đạt chuẩn:',
      queryLabel: 'CÂU HỎI TRUY VẤN ĐỀ TÀI (QUERY)',
      replayBtn: 'Chạy lại ↻',
      statusText: 'Đang trích xuất toàn văn PDF và đối chiếu cơ sở dữ liệu Scopus...',
      arrowText: 'Bản thảo tổng hợp hoàn tất trong 4 phút',
      tagOffTopic: 'Không khớp Tiêu chí',
      tagRetracted: 'Ngoài Scopus',
      tagNoPeer: 'Trùng lặp',
      meterLabel: 'Tỷ lệ bài báo vượt qua vòng Sàng lọc Tiêu chí PRISMA & Scopus:',
      stat1Num: '92', stat1Unit: '%', stat1Label: 'Độ chính xác đối chiếu Scopus Q1 & sàng lọc PRISMA',
      stat2Num: '340', stat2Unit: ' trang', stat2Label: 'Trung bình số trang PDF trích xuất trong chưa đầy 1 phút',
      stat3Num: '4', stat3Unit: ' phút', stat3Label: 'Thời gian hoàn thiện bản dự thảo Literature Review đầu tiên',
    },
    agents: {
      badge: 'KIẾN TRÚC QUY TRÌNH HỌC THUẬT ĐA PHÂN HỆ',
      title: 'Bốn Phân Hệ Chuyên Biệt Vận Hành Chuẩn Mực Nghiên Cứu',
      desc: 'Bốn phân hệ phối hợp chặt chẽ theo đúng chuẩn mực của một bài báo Systematic Literature Review quốc tế:',
      a1Title: 'Phân hệ 1: Cố vấn Đề tài & Khung PICO',
      a1Desc: 'Phân tích câu hỏi nghiên cứu, tự động thiết lập tiêu chí Đưa vào / Loại trừ (Inclusion/Exclusion) và tổng hợp chuỗi truy vấn Boolean tối ưu.',
      a2Title: 'Phân hệ 2: Tra cứu & Đối chiếu Scopus',
      a2Desc: 'Tìm kiếm đa nguồn học thuật trên Google Scholar, tự động đối chiếu chỉ số Scopus (Q1–Q4), lọc trùng lặp và loại bỏ nguồn không đạt chuẩn.',
      a3Title: 'Phân hệ 3: Sàng lọc PRISMA & Ma trận So sánh',
      a3Desc: 'Đọc toàn văn bài báo, đánh giá độ phù hợp theo tiêu chuẩn PRISMA và tự động trích xuất bảng ma trận so sánh Dataset, Model, Metrics.',
      a4Title: 'Phân hệ 4: Thẩm định Y văn & Khoảng trống Đề tài',
      a4Desc: 'Phát hiện các điểm nghẽn và mâu thuẫn chưa giải quyết (Research Gaps) trong y văn; hỏi đáp tra cứu với trích dẫn số trang và câu trích nguyên bản 100%.',
    },
    matrixSection: {
      badge: 'MA TRẬN PHƯƠNG PHÁP & RADAR KHOẢNG TRỐNG',
      title: 'Tự động So sánh Đa chiều & Khám phá Cơ hội Nghiên cứu',
      desc: 'Hệ thống tự động đọc toàn văn PDF và dựng bảng so sánh đa chiều giữa các công trình nghiên cứu đã được chọn lọc:',
      colAuthor: 'Bài báo & Tác giả',
      colMethod: 'Phương pháp / Kiến trúc',
      colDataset: 'Tập dữ liệu (Dataset)',
      colMetrics: 'Kết quả Định lượng',
      colGap: 'Hạn chế & Điểm nghẽn',
      gapsTitle: 'Khoảng trống Nghiên cứu Được Phát hiện (Research Gaps Radar):',
    },
    prismaSection: {
      badge: 'TIÊU CHUẨN XUẤT BẢN QUỐC TẾ',
      title: 'Lưu đồ Thu thập & Sàng lọc Chuẩn PRISMA',
      desc: 'Toàn bộ quy trình thu thập và sàng lọc tài liệu được ghi nhận minh bạch theo đúng tiêu chuẩn xuất bản quốc tế:',
      s1Num: '01', s1Title: 'Nhận diện (Identification)', s1Desc: 'Thu thập tất cả bản ghi từ Google Scholar và các nguồn học thuật uy tín.',
      s2Num: '02', s2Title: 'Đối chiếu Scopus (Verification)', s2Desc: 'Lọc trùng lặp tự động và xác minh trạng thái chỉ mục Scopus (Q1–Q4).',
      s3Num: '03', s3Title: 'Sàng lọc Tiêu chí (Screening)', s3Desc: 'Chấm điểm độ phù hợp theo tiêu chí Inclusion & Exclusion đã thiết lập.',
      s4Num: '04', s4Title: 'Đưa vào Tổng hợp (Included)', s4Desc: 'Trích xuất toàn văn PDF, nạp vào Ma trận So sánh và Không gian Chat tra cứu.',
    },
    demoAccounts: {
      badge: 'TRẢI NGHIỆM TỨC THÌ',
      title: 'Đăng nhập Nhanh với Hồ sơ Nghiên cứu Mẫu',
      desc: 'Không cần tạo tài khoản — chọn 1 trong các hồ sơ có sẵn dữ liệu đề tài thực tế để trải nghiệm ngay:',
      u1Name: 'TS. Nguyễn Hải',
      u1Role: 'Senior AI Researcher',
      u1Inst: 'VinUniversity & VinAI Research',
      u1Project: '📂 Đề tài: Ứng dụng Deep Learning trong Phân loại Tín hiệu Điện tim ECG (14 bài báo Scopus, 4 khoảng trống đề tài).',
      u1Btn: 'Đăng nhập với vai trò TS. Nguyễn Hải',
      u2Name: 'Minh Phạm',
      u2Role: 'Graduate Student',
      u2Inst: 'Đại học Bách Khoa Hà Nội (HUST)',
      u2Project: '📂 Đề tài: Khảo sát Chuỗi Tư duy (Chain-of-Thought) trong LLMs (9 bài báo NeurIPS/ICML, 2 bài tổng hợp).',
      u2Btn: 'Đăng nhập với vai trò Minh Phạm',
    },
    faq: {
      badge: 'HỎI ĐÁP THƯỜNG GẶP',
      title: 'Những Thắc mắc Phổ biến về Nền tảng',
      q1: 'Hệ thống hỗ trợ những định dạng xuất bản nào?',
      a1: 'LitReview hỗ trợ xuất bản gói trích dẫn BibTeX (.bib) chuẩn cho LaTeX/Overleaf, bảng tính CSV, tài liệu Markdown (.md) và định dạng JSON có cấu trúc.',
      q2: 'Cơ chế chống ảo giác và trích dẫn chuẩn xác hoạt động ra sao?',
      a2: 'Mọi câu trả lời trong Workspace đều neo trực tiếp vào số trang và đoạn trích nguyên bản từ các file PDF đã tải lên. Hệ thống không bịa nguồn hay sử dụng các bài báo không có thật.',
      q3: 'Làm thế nào để hệ thống lọc được các bài báo Scopus?',
      a3: 'Hệ thống tích hợp quy trình đối chiếu tên tạp chí và nhà xuất bản với danh mục Scopus chính thức, chỉ giữ lại các bài báo đã được xác minh chỉ số.',
      q4: 'Tôi có thể tải lên tài liệu PDF của riêng mình không?',
      a4: 'Có. Trong WorkspaceTab, bạn có thể tải lên trực tiếp các file PDF tài liệu toàn văn để hệ thống trích xuất nội dung, đưa vào ma trận so sánh và phân tích chuyên sâu.',
    },
    team: {
      badge: 'ĐỘI NGŨ PHÁT TRIỂN',
      title: 'Đội ngũ Phát triển Sản phẩm',
      desc: 'Dự án Nghiên cứu & Phát triển thuộc Khóa 3 — Chương trình AI Thực Chiến',
      members: [
        {
          name: 'Nguyễn Đình Liêm',
          studentId: '2A202601421',
          role: 'Học viên khóa 3',
          course: 'Chương trình AI thực chiến',
          img: member1Img,
          imgPublic: '/assets/member1.jpeg',
          imgPosition: 'center 8%',
          initials: 'NL',
          color: 'from-blue-600 to-indigo-700'
        },
        {
          name: 'Tạ Thị Nga',
          studentId: '2A202601125',
          role: 'Học viên khóa 3',
          course: 'Chương trình AI thực chiến',
          img: member2Img,
          imgPublic: '/assets/member2.jpg',
          imgPosition: 'center 15%',
          initials: 'TN',
          color: 'from-purple-600 to-pink-600'
        },
        {
          name: 'Nguyễn Văn Hưng',
          studentId: '2A202601970',
          role: 'Học viên khóa 3',
          course: 'Chương trình AI thực chiến',
          img: member3Img,
          imgPublic: '/assets/member3.JPG',
          imgPosition: 'center 15%',
          initials: 'NH',
          color: 'from-emerald-600 to-teal-700'
        },
        {
          name: 'Nguyễn Đào Nam Hải',
          studentId: '2A202601037',
          role: 'Học viên khóa 3',
          course: 'Chương trình AI thực chiến',
          img: member4Img,
          imgPublic: '/assets/member4.jpg',
          imgPosition: 'center 20%',
          initials: 'NH',
          color: 'from-primary-600 to-cyan-700'
        }
      ]
    },
    acknowledgments: {
      badge: 'LỜI TRI ÂN & CẢM ƠN',
      title: 'Lời Cảm Ơn Sâu Sắc',
      p1: 'Nhóm chúng em xin gửi lời cảm ơn chân thành và sâu sắc nhất tới Ban Tổ chức Chương trình AI Thực Chiến (Khóa 3) đã kiến tạo nên một môi trường đào tạo chuyên sâu, bài bản và giàu tính thực tiễn — nơi chúng em được trao cơ hội quý giá để tiếp cận công nghệ đỉnh cao, thử thách bản thân và trưởng thành vượt bậc qua từng dự án thực chiến.',
      p2: 'Chúng em xin bày tỏ lòng tri ân sâu sắc tới Quý Thầy Cô đã tâm huyết truyền đạt nền tảng tri thức chuyên sâu và tư duy nghiên cứu chuẩn mực; cảm ơn các anh chị Mentor và Lab Coach đã không quản ngày đêm sát cánh, hỗ trợ giải đáp kỹ thuật, định hướng kiến trúc hệ thống và đóng góp những phản biện sắc sảo để Đề tài P-165 (LitReview AI) được hoàn thiện một cách toàn diện và vượt bậc.',
      p3: 'Những trải nghiệm thực chiến và kỷ luật kỹ thuật được tôi luyện tại khóa học sẽ mãi là bệ phóng vững chắc, là hành trang vô giá để chúng em vững bước trên con đường nghiên cứu khoa học và phát triển công nghệ. Kính chúc Ban Tổ chức, Quý Thầy Cô, các anh chị Mentor & Lab Coach dồi dào sức khỏe, hạnh phúc; chúc Chương trình AI Thực Chiến ngày càng phát triển rực rỡ, tiếp tục là bệ phóng tài năng hàng đầu giúp kỹ sư AI Việt Nam vươn tầm quốc tế!',
      signature: 'Trân trọng, Nhóm tác giả Đề tài P-165 — Học viên Khóa 3 Chương trình AI Thực Chiến',
    },
    final: {
      title: 'Bản tổng quan tài liệu tiếp theo của bạn, hoàn thành nhanh gấp 5 lần.',
      desc: 'Trải nghiệm ngay quy trình tổng quan tài liệu khoa học chuẩn mực PRISMA.',
      btn: 'Bắt đầu Nghiên cứu Miễn phí',
      footerTagline: 'LitReview — Nền tảng Tự động hóa Tổng quan Tài liệu Khoa học Chuẩn Quốc tế.',
      footerSub: 'VinUni AI Team 165. Built for High-Impact Scientific Research.',
    }
  },
  en: {
    nav: {
      simulator: 'Live Simulation',
      agents: '4-Step Workflow',
      matrix: 'Literature Matrix',
      prisma: 'PRISMA Standard',
      demoProfiles: 'Demo Profiles',
      faq: 'FAQ',
      team: 'Team',
      acknowledgments: 'Special Thanks',
      login: 'Sign In',
      startFree: 'Start Free',
    },
    hero: {
      badge: 'ACADEMIC SYSTEMATIC LITERATURE REVIEW',
      title1: 'Automate Literature Reviews',
      titleHighlight: 'PRISMA & Scopus Grounded',
      desc: 'Eliminate hundreds of hours of manual reading: Automate PICO scoping, Scopus screening, PDF extraction, and methodology synthesis matrices — 100% grounded on real DOIs.',
      btnDemo: 'Explore Demo Workspace',
      btnSimulate: 'Watch Live Simulator',
      trust1: '100% Real DOIs',
      trust2: 'PRISMA Protocol',
      trust3: 'Scopus Q1 Verified',
      trust4: 'BibTeX / CSV Export',
      previewBadge: 'LIVE SLR SESSION · PRISMA PROTOCOL',
      previewStatus: 'Scopus Q1 Verified',
      previewQuery: '1D-CNN + Spatial-Temporal Attention for Arrhythmia Detection',
      previewQuote: 'Spatial-temporal attention combined with 1D-CNN achieves 98.6% sensitivity on MIT-BIH, significantly outperforming legacy SVM classifiers.',
      previewCitation: 'Wang et al., 2023 · IEEE TBME, Vol. 70, p.142',
      previewStatRecords: '100+ Records',
      previewStatFiltered: '14 Scopus Q1',
      previewStatIncluded: '4 In Matrix',
    },
    demo: {
      badge: 'REAL-TIME SLR SCREENING & SYNTHESIS SIMULATOR',
      title: 'Experience Systematic Literature Review Workflow',
      desc: 'Select a research sample topic below to watch the workflow decompose the PICO framework, verify Scopus sources, and synthesize verified evidence:',
      queryLabel: 'RESEARCH QUESTION / QUERY',
      replayBtn: 'Replay ↻',
      statusText: 'Extracting full-text PDFs and cross-referencing Scopus database...',
      arrowText: 'Synthesis draft completed in 4 minutes',
      tagOffTopic: 'PRISMA Excluded',
      tagRetracted: 'Not Indexed',
      tagNoPeer: 'Duplicate',
      meterLabel: 'Papers Passing PRISMA Screening & Scopus Verification:',
      stat1Num: '92', stat1Unit: '%', stat1Label: 'Scopus Q1 Verification & PRISMA Precision',
      stat2Num: '340', stat2Unit: ' pgs', stat2Label: 'Full-text PDF pages extracted in under 60 seconds',
      stat3Num: '4', stat3Unit: ' mins', stat3Label: 'Time to generate first grounded synthesis draft',
    },
    agents: {
      badge: 'MULTI-MODULE WORKFLOW ARCHITECTURE',
      title: 'Four Specialized Modules Executing Rigorous Academic SLR',
      desc: 'Four specialized modules collaborate strictly following systematic literature review standards:',
      a1Title: 'Module 1: Topic Refiner & PICO Scoping',
      a1Desc: 'Analyzes research questions, sets PRISMA inclusion/exclusion criteria, and synthesizes optimal Boolean query strings.',
      a2Title: 'Module 2: Search & Scopus Verification',
      a2Desc: 'Searches multi-academic sources, verifies Scopus indexing (Q1–Q4), removes duplicates, and filters unverified venues.',
      a3Title: 'Module 3: PRISMA Screening & Comparison Matrix',
      a3Desc: 'Evaluates full-text eligibility based on PRISMA standards and automatically builds methodology comparison tables (Dataset, Model, Metrics).',
      a4Title: 'Module 4: Evidence Synthesis & Gap Discovery',
      a4Desc: 'Discovers unsolved bottlenecks and research opportunities in literature; answers inquiries with exact page quotes and 100% DOI grounding.',
    },
    matrixSection: {
      badge: 'METHODOLOGY COMPARISON & RESEARCH GAP RADAR',
      title: 'Multi-Dimensional Matrix & Unsolved Research Opportunities',
      desc: 'The system automatically ingests full-text PDFs and extracts multi-dimensional comparison tables:',
      colAuthor: 'Paper & Authors',
      colMethod: 'Methodology / Architecture',
      colDataset: 'Benchmark Dataset',
      colMetrics: 'Quantitative Results',
      colGap: 'Identified Bottlenecks & Gaps',
      gapsTitle: 'Discovered Research Opportunities (Gap Radar):',
    },
    prismaSection: {
      badge: 'INTERNATIONAL PUBLICATION STANDARDS',
      title: 'PRISMA Identification & Screening Flowchart',
      desc: 'Every step of document retrieval and screening is transparently tracked according to PRISMA standards:',
      s1Num: '01', s1Title: 'Identification', s1Desc: 'Retrieve candidate records from Google Scholar and academic databases.',
      s2Num: '02', s2Title: 'Scopus Verification', s2Desc: 'Automatically filter duplicates and verify Scopus indexing status (Q1–Q4).',
      s3Num: '03', s3Title: 'Criteria Screening', s3Desc: 'Score relevance against established Inclusion & Exclusion criteria.',
      s4Num: '04', s4Title: 'Included in Synthesis', s4Desc: 'Extract full text, populate synthesis matrix, and feed analysis workspace.',
    },
    demoAccounts: {
      badge: 'INSTANT ONBOARDING',
      title: 'Quick Sign-In with Academic Demo Profiles',
      desc: 'No registration needed — pick an account pre-populated with real systematic review projects:',
      u1Name: 'Dr. Nguyen Hai',
      u1Role: 'Senior AI Researcher',
      u1Inst: 'VinUniversity & VinAI Research',
      u1Project: '📂 Active Project: Deep Learning in Cardiac Arrhythmia ECG (14 Scopus papers, 4 research gaps).',
      u1Btn: 'Sign In as Dr. Nguyen Hai',
      u2Name: 'Minh Pham',
      u2Role: 'Graduate Student',
      u2Inst: 'Hanoi University of Science & Technology (HUST)',
      u2Project: '📂 Active Project: Chain-of-Thought in LLMs (9 NeurIPS/ICML papers, 2 synthesis drafts).',
      u2Btn: 'Sign In as Minh Pham',
    },
    faq: {
      badge: 'FREQUENTLY ASKED QUESTIONS',
      title: 'Everything You Need to Know',
      q1: 'Which export formats are supported?',
      a1: 'LitReview supports standard BibTeX (.bib) packages for LaTeX/Overleaf, CSV tables, Markdown (.md) reports, and structured JSON.',
      q2: 'How does the anti-hallucination mechanism work?',
      a2: 'All responses in the Workspace are anchored directly to specific page numbers and verbatim text quotes from uploaded PDFs. No synthetic references are ever generated.',
      q3: 'How does the platform verify Scopus indexing?',
      a3: 'The system cross-references journal names, ISSNs, and publisher metadata against verified Scopus databases, retaining only confirmed publications.',
      q4: 'Can I upload my own PDF documents directly?',
      a4: 'Yes. In the WorkspaceTab, you can directly upload full-text PDF files to extract structured tables, populate the comparison matrix, and query via grounded RAG.',
    },
    team: {
      badge: 'DEVELOPMENT TEAM',
      title: 'Product Development Team',
      desc: 'Research & Development Project under AI Engineering Cohort 3 Program',
      members: [
        {
          name: 'Nguyễn Đình Liêm',
          studentId: '2A202601421',
          role: 'Cohort 3 Student',
          course: 'AI Engineering Program',
          img: member1Img,
          imgPublic: '/assets/member1.jpeg',
          imgPosition: 'center 8%',
          initials: 'NL',
          color: 'from-blue-600 to-indigo-700'
        },
        {
          name: 'Tạ Thị Nga',
          studentId: '2A202601125',
          role: 'Cohort 3 Student',
          course: 'AI Engineering Program',
          img: member2Img,
          imgPublic: '/assets/member2.jpg',
          imgPosition: 'center 15%',
          initials: 'TN',
          color: 'from-purple-600 to-pink-600'
        },
        {
          name: 'Nguyễn Văn Hưng',
          studentId: '2A202601970',
          role: 'Cohort 3 Student',
          course: 'AI Engineering Program',
          img: member3Img,
          imgPublic: '/assets/member3.JPG',
          imgPosition: 'center 15%',
          initials: 'NH',
          color: 'from-emerald-600 to-teal-700'
        },
        {
          name: 'Nguyễn Đào Nam Hải',
          studentId: '2A202601037',
          role: 'Cohort 3 Student',
          course: 'AI Engineering Program',
          img: member4Img,
          imgPublic: '/assets/member4.jpg',
          imgPosition: 'center 20%',
          initials: 'NH',
          color: 'from-primary-600 to-cyan-700'
        }
      ]
    },
    acknowledgments: {
      badge: 'SPECIAL ACKNOWLEDGMENTS',
      title: 'Our Sincere Gratitude',
      p1: 'Our team would like to express our deepest gratitude to the Organizing Committee of the AI Engineering Program (Cohort 3) for creating such an intensive, rigorous, and practical learning environment — giving us the invaluable opportunity to master state-of-the-art technologies and grow through real-world engineering challenges.',
      p2: 'We extend our heartfelt appreciation to our Professors for imparting profound academic foundations and rigorous research methodologies; and to our dedicated Mentors and Lab Coaches for their continuous, hands-on guidance — troubleshooting complex technical roadblocks, providing insightful architectural critiques, and empowering Project P-165 (LitReview AI) to achieve its highest standards.',
      p3: 'The real-world engineering discipline and invaluable insights gained from this program will serve as a lifelong launching pad for our future pursuits in AI innovation and scientific research. We wish the program continued excellence in nurturing top-tier AI engineering talents on the global stage!',
      signature: 'Respectfully, Project Team P-165 — AI Engineering Program (Cohort 3)',
    },
    final: {
      title: 'Your next systematic literature review, completed 5x faster.',
      desc: 'Experience the gold standard in academic literature review with PRISMA protocol.',
      btn: 'Start Your Review Free',
      footerTagline: 'LitReview — International Academic Systematic Literature Review Platform.',
      footerSub: 'VinUni AI Team 165. Built for High-Impact Scientific Research.',
    }
  }
};

export default function PublicLandingPage({ onOpenAuth }) {
  const { language, setLanguage } = useLanguage();
  const { darkMode, setDarkMode } = useDarkMode();

  const d = DICTIONARY[language] || DICTIONARY.vi;

  // ── Scroll Tracking ────────────────────────────────────────────────────
  const [scrollY, setScrollY] = useState(0);
  const [activeSection, setActiveSection] = useState('hero');

  useEffect(() => {
    const handleScroll = () => {
      const currentScroll = window.scrollY;
      setScrollY(currentScroll);

      // Determine active section for scrollytelling navigator
      const sections = ['hero', 'simulator', 'agents', 'matrix', 'prisma', 'demo-accounts', 'faq'];
      for (const sId of sections) {
        const el = document.getElementById(sId);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= window.innerHeight * 0.45 && rect.bottom >= window.innerHeight * 0.15) {
            setActiveSection(sId);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // ── Active Topic State ─────────────────────────────────────────────────
  const [activeTopicKey, setActiveTopicKey] = useState('ecg');
  const activeTopic = TOPIC_PRESETS[activeTopicKey] || TOPIC_PRESETS.ecg;

  // ── Autonomous Live Demo Engine ──────────────────────────────────────────
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const [cockpitTab, setCockpitTab] = useState('pico');
  const [copiedQuery, setCopiedQuery] = useState(false);
  const [copiedBib, setCopiedBib] = useState(false);

  // Sub-stage micro-animations
  const [typedQuery, setTypedQuery] = useState('');
  const [picoActiveIdx, setPicoActiveIdx] = useState(0); // 1: P, 2: I, 3: C, 4: O, 5: Boolean query
  const [screeningRowsShown, setScreeningRowsShown] = useState(0);
  const [screeningProcessed, setScreeningProcessed] = useState(false);
  const [meterValue, setMeterValue] = useState(0);
  const [matrixScanIdx, setMatrixScanIdx] = useState(-1);
  const [autoTooltipCite, setAutoTooltipCite] = useState(false);
  const [ragSimActive, setRagSimActive] = useState(false);
  const [autoStatusText, setAutoStatusText] = useState('');

  // Autonomous Cycle Runner
  const runAutonomousCycle = (topicKey = activeTopicKey) => {
    const topic = TOPIC_PRESETS[topicKey] || TOPIC_PRESETS.ecg;

    // Reset baseline
    setCockpitTab('pico');
    setTypedQuery('');
    setPicoActiveIdx(0);
    setScreeningRowsShown(0);
    setScreeningProcessed(false);
    setMeterValue(0);
    setMatrixScanIdx(-1);
    setAutoTooltipCite(false);
    setRagSimActive(false);
    setAutoStatusText(
      language === 'vi'
        ? '🟢 ĐANG TỰ ĐỘNG CHẠY: [Bước 1/4] Phân rã câu hỏi PICO & tối ưu chuỗi Boolean...'
        : '🟢 AUTOPLAY: [Step 1/4] Scoping PICO Framework & Synthesizing Boolean...'
    );

    // Typing query
    let charIdx = 0;
    const typeInterval = setInterval(() => {
      charIdx++;
      setTypedQuery(topic.query.slice(0, charIdx));
      if (charIdx >= topic.query.length) {
        clearInterval(typeInterval);
      }
    }, 16);

    // STAGE 1: PICO Cards sequence
    const t1 = setTimeout(() => setPicoActiveIdx(1), 900);
    const t2 = setTimeout(() => setPicoActiveIdx(2), 1600);
    const t3 = setTimeout(() => setPicoActiveIdx(3), 2300);
    const t4 = setTimeout(() => setPicoActiveIdx(4), 3000);
    const t5 = setTimeout(() => setPicoActiveIdx(5), 3600);

    // ── STAGE 2: PRISMA Screening (at 4.6s) ──
    const t6 = setTimeout(() => {
      setCockpitTab('screening');
      setAutoStatusText(
        language === 'vi'
          ? '🟢 ĐANG TỰ ĐỘNG CHẠY: [Bước 2/4] Sàng lọc PRISMA & đối chiếu Scopus Q1...'
          : '🟢 AUTOPLAY: [Step 2/4] PRISMA Screening & Scopus Verification...'
      );
      setScreeningRowsShown(topic.rows.length);
    }, 4600);

    const t7 = setTimeout(() => {
      setScreeningProcessed(true);
      // Meter animation 0 -> 75%
      let curM = 0;
      const mInterval = setInterval(() => {
        curM += 4;
        setMeterValue(Math.min(curM, 75));
        if (curM >= 75) clearInterval(mInterval);
      }, 20);
    }, 5800);

    // ── STAGE 3: Methodology Matrix (at 9.2s) ──
    const t8 = setTimeout(() => {
      setCockpitTab('matrix');
      setAutoStatusText(
        language === 'vi'
          ? '🟢 ĐANG TỰ ĐỘNG CHẠY: [Bước 3/4] Trích xuất toàn văn PDF vào Ma trận So sánh...'
          : '🟢 AUTOPLAY: [Step 3/4] Extracting Full-Text PDFs into Methodology Matrix...'
      );
      setMatrixScanIdx(0);
    }, 9200);

    const t9 = setTimeout(() => setMatrixScanIdx(1), 10400);
    const t10 = setTimeout(() => setMatrixScanIdx(2), 11600);
    const t11 = setTimeout(() => setMatrixScanIdx(3), 12800);

    // ── STAGE 4: Synthesis & Fact-Checking RAG (at 14.0s) ──
    const t12 = setTimeout(() => {
      setCockpitTab('synthesis');
      setAutoStatusText(
        language === 'vi'
          ? '🟢 ĐANG TỰ ĐỘNG CHẠY: [Bước 4/4] Tổng hợp luận điểm & hỏi đáp Fact-Checking RAG...'
          : '🟢 AUTOPLAY: [Step 4/4] Grounded Evidence Synthesis & RAG Fact-Checking...'
      );
    }, 14000);

    // Pop open citation tooltip automatically to showcase verbatim page quote
    const t13 = setTimeout(() => setAutoTooltipCite(true), 15200);
    const t14 = setTimeout(() => {
      setAutoTooltipCite(false);
      setRagSimActive(true);
    }, 17500);

    // Cycle repeat
    const t15 = setTimeout(() => {
      setAutoStatusText(
        language === 'vi'
          ? '✓ Quy trình hoàn tất! Tự động lặp lại quy trình...'
          : '✓ Full SLR Cycle Complete! Restarting loop...'
      );
    }, 19800);

    const t16 = setTimeout(() => {
      if (isAutoPlaying) {
        runAutonomousCycle(activeTopicKey);
      }
    }, 21500);

    return () => {
      clearInterval(typeInterval);
      [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16].forEach(clearTimeout);
    };
  };

  useEffect(() => {
    if (isAutoPlaying) {
      const cleanup = runAutonomousCycle(activeTopicKey);
      return cleanup;
    } else {
      // If user paused, ensure current view is complete and readable
      setPicoActiveIdx(5);
      setScreeningRowsShown(activeTopic.rows.length);
      setScreeningProcessed(true);
      setMeterValue(75);
      setMatrixScanIdx(activeTopic.matrix.length);
      setRagSimActive(true);
      setAutoStatusText(
        language === 'vi'
          ? '⏸ Đã tạm dừng tự động. Bạn có thể tự do khám phá hoặc nhấn "▶ Tự động chạy".'
          : '⏸ Autoplay paused. Feel free to explore or click "▶ Resume Autoplay".'
      );
    }
  }, [isAutoPlaying, activeTopicKey, language]);

  const handleSelectTopic = (key) => {
    setActiveTopicKey(key);
    if (!isAutoPlaying) {
      setIsAutoPlaying(true);
    }
  };

  const handleSelectTabManual = (tabId) => {
    setIsAutoPlaying(false);
    setCockpitTab(tabId);
    setPicoActiveIdx(5);
    setScreeningRowsShown(activeTopic.rows.length);
    setScreeningProcessed(true);
    setMeterValue(75);
    setMatrixScanIdx(activeTopic.matrix.length);
    setRagSimActive(true);
  };

  // ── FAQ Accordion ──────────────────────────────────────────────────────
  const [openFaq, setOpenFaq] = useState(0);

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#080E1A] text-surface-900 dark:text-surface-100 font-sans selection:bg-primary-500 selection:text-white transition-colors relative overflow-x-hidden w-full">

      {/* ── 0. Minimalist Interactive Constellation Background with Parallax */}
      <AcademicConstellationCanvas darkMode={darkMode} scrollY={scrollY} />

      {/* ── 1. Top Glassmorphic Navigation Bar ─────────────────────────── */}
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-800/80 transition-colors shadow-2xs w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 sm:h-20 flex items-center justify-between gap-2 lg:gap-4 relative z-10 w-full">
          
          {/* Brand */}
          <div className="flex items-center gap-2.5 sm:gap-3 cursor-pointer select-none group shrink-0" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform shrink-0">
              <BookOpen className="w-4.5 h-4.5 sm:w-5 sm:h-5" />
            </div>
            <div>
              <span className="font-display font-extrabold text-base sm:text-lg text-slate-900 dark:text-white leading-none tracking-tight block">
                LitReview
              </span>
              <p className="text-[10.5px] sm:text-[11.5px] font-semibold text-blue-600 dark:text-blue-400 mt-1 leading-none whitespace-nowrap">
                {language === 'vi' ? 'Nền tảng Nghiên cứu & Tổng quan Tài liệu' : 'Academic Literature Review Platform'}
              </p>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden xl:flex items-center gap-2.5 2xl:gap-4 text-xs 2xl:text-[13px] font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
            <a href="#simulator" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5">{d.nav.simulator}</a>
            <a href="#agents" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5">{d.nav.agents}</a>
            <a href="#matrix" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5 hidden 2xl:inline-block">{d.nav.matrix}</a>
            <a href="#prisma" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5">{d.nav.prisma}</a>
            <a href="#demo-accounts" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5 hidden 2xl:inline-block">{d.nav.demoProfiles}</a>
            <a href="#faq" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5">{d.nav.faq}</a>
            <a href="#team" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5 hidden 2xl:inline-block">{d.nav.team}</a>
            <a href="#acknowledgments" className="hover:text-blue-600 dark:hover:text-blue-400 hover:scale-105 transition-all py-1 px-1.5 hidden 2xl:inline-block">{d.nav.acknowledgments}</a>
          </nav>

          {/* Controls & Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            
            {/* Language Switch */}
            <button
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
              className="px-2 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-xs font-bold flex items-center gap-1 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 cursor-pointer shadow-2xs shrink-0"
              title="Chuyển đổi ngôn ngữ / Switch language"
            >
              <Languages className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="uppercase font-mono">{language}</span>
            </button>

            {/* Dark Mode Switch */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 cursor-pointer shadow-2xs shrink-0"
              title="Giao diện Sáng/Tối"
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-600" />}
            </button>

            {/* Auth Buttons */}
            <button
              onClick={() => onOpenAuth('login')}
              className="btn btn-secondary px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-bold cursor-pointer shrink-0 whitespace-nowrap"
            >
              {d.nav.login}
            </button>

            <button
              onClick={() => onOpenAuth('demo')}
              className="btn btn-primary px-3.5 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 inline-flex items-center gap-1.5 cursor-pointer hover:scale-105 transition-all shrink-0 whitespace-nowrap"
            >
              <BookOpen className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>{d.nav.startFree}</span>
            </button>
          </div>

        </div>
      </header>

      {/* ── 2. Full-Screen Majestic Two-Column Split Hero Section ─────── */}
      <section id="hero" className="relative overflow-hidden min-h-[calc(100vh-4rem)] flex flex-col justify-between pt-6 sm:pt-8 pb-8 border-b border-surface-200/80 dark:border-surface-800/80 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-1 flex items-center my-auto">
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center w-full py-4 sm:py-6">
            
            {/* Left Column: Prestigious Value Proposition */}
            <ScrollReveal variant="left" className="lg:col-span-7 space-y-6 text-left" delay={50}>
              
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800/80 shadow-xs backdrop-blur-md">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-[11px] font-extrabold text-blue-700 dark:text-blue-300 uppercase tracking-wider">
                  {d.hero.badge}
                </span>
              </div>

              {/* Headline */}
              <h1 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[40px] xl:text-[45px] text-slate-900 dark:text-white tracking-tight leading-[1.32] space-y-2">
                <span className="block">{d.hero.title1}</span>
                <span className="block text-shimmer gradient-text pb-1">
                  {d.hero.titleHighlight}
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-xl leading-relaxed pt-1">
                {d.hero.desc}
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3.5 pt-2">
                <button
                  onClick={() => onOpenAuth('demo')}
                  className="btn btn-primary btn-lg shadow-primary-md hover:scale-105 transition-all cursor-pointer font-bold"
                >
                  <BookOpen className="w-4 h-4" />
                  <span>{d.hero.btnDemo}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                
                <a
                  href="#simulator"
                  className="btn btn-secondary btn-lg flex items-center gap-2 font-semibold"
                >
                  <Play className="w-4 h-4 text-blue-600" />
                  <span>{d.hero.btnSimulate}</span>
                </a>
              </div>

              {/* Trust Badges */}
              <div className="pt-2 flex flex-wrap items-center gap-2.5">
                {[
                  { icon: ShieldCheck, text: d.hero.trust1, color: 'text-emerald-500' },
                  { icon: CheckCircle2, text: d.hero.trust2, color: 'text-blue-500' },
                  { icon: Database, text: d.hero.trust3, color: 'text-sky-500' },
                  { icon: FileCode, text: d.hero.trust4, color: 'text-amber-500' },
                ].map((pill, i) => {
                  const Icon = pill.icon;
                  return (
                    <div
                      key={i}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 shadow-xs hover:border-blue-400 transition-colors"
                    >
                      <Icon className={`w-3.5 h-3.5 ${pill.color}`} />
                      <span>{pill.text}</span>
                    </div>
                  );
                })}
              </div>

            </ScrollReveal>

            {/* Right Column: Hero Interactive 3D Preview Card */}
            <ScrollReveal variant="right" className="lg:col-span-5 relative" delay={150}>
              
              {/* Ambient halo behind preview card */}
              <div className="absolute -inset-3 bg-gradient-to-r from-primary-500/25 to-indigo-600/25 rounded-3xl blur-2xl -z-10 animate-pulse" />

              
                <div className="card p-6 sm:p-7 shadow-2xl border-primary-500/40 bg-white/90 dark:bg-surface-900/90 backdrop-blur-xl space-y-4 scrolly-card">
                  
                  {/* Card Header */}
                  <div className="flex items-center justify-between pb-3 border-b border-surface-200 dark:border-surface-800 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="font-mono font-bold text-xs text-surface-800 dark:text-surface-200">{d.hero.previewBadge}</span>
                    </div>
                    <span className="badge badge-success text-[10px] uppercase font-bold tracking-wider">{d.hero.previewStatus}</span>
                  </div>

                  {/* Active Query Pill */}
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-800/80 border border-surface-200 dark:border-surface-700 space-y-1">
                    <span className="text-[9.5px] font-mono text-primary-600 dark:text-primary-400 font-bold uppercase block">Query Input:</span>
                    <p className="text-xs sm:text-sm font-mono font-semibold text-surface-900 dark:text-white truncate">
                      {d.hero.previewQuery}
                    </p>
                  </div>

                  {/* Grounded Quote Snippet */}
                  <div className="p-4 rounded-xl bg-primary-50/50 dark:bg-primary-950/40 border border-primary-200/80 dark:border-primary-900/60 space-y-2">
                    <div className="flex items-center justify-between text-[9.5px] text-primary-700 dark:text-primary-300 font-mono font-bold">
                      <span>GROUNDED CITATION (100% DOI)</span>
                      <span className="badge badge-primary text-[9px]">P.142 EXACT QUOTE</span>
                    </div>
                    <p className="text-xs sm:text-sm text-surface-800 dark:text-surface-200 italic leading-relaxed">
                      "{d.hero.previewQuote}"
                    </p>
                    <div className="flex items-center gap-2 text-xs font-medium text-primary-600 dark:text-primary-400 pt-0.5">
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>{d.hero.previewCitation}</span>
                    </div>
                  </div>

                  {/* Mini Funnel Counters */}
                  <div className="grid grid-cols-3 gap-2.5 pt-1 text-center">
                    <div className="p-2.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700">
                      <span className="font-mono font-bold text-sm text-surface-800 dark:text-white block">{d.hero.previewStatRecords}</span>
                      <span className="text-[9px] text-surface-500 uppercase font-semibold">Identified</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50">
                      <span className="font-mono font-bold text-sm text-emerald-600 dark:text-emerald-400 block">{d.hero.previewStatFiltered}</span>
                      <span className="text-[9px] text-emerald-700 dark:text-emerald-300 uppercase font-semibold">Scopus Verified</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-primary-50/50 dark:bg-primary-950/30 border border-primary-200 dark:border-primary-900/50">
                      <span className="font-mono font-bold text-sm text-primary-600 dark:text-primary-400 block">{d.hero.previewStatIncluded}</span>
                      <span className="text-[9px] text-primary-700 dark:text-primary-300 uppercase font-semibold">Synthesized</span>
                    </div>
                  </div>

                </div>
              

            </ScrollReveal>

          </div>

        </div>

        {/* Downward Exploration Scroll Indicator */}
        <div className="w-full flex justify-center pb-2 pt-4">
          <a
            href="#simulator"
            className="inline-flex flex-col items-center gap-1 text-[11px] font-semibold text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors animate-bounce cursor-pointer group"
          >
            <span>{language === 'vi' ? 'Khám phá Mô phỏng Thực tế' : 'Explore Live Simulator'}</span>
            <ChevronDown className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
          </a>
        </div>
      </section>

      {/* ── 3. Interactive Comprehensive SLR Cockpit Simulator ───────── */}
      <section id="simulator" className="py-20 bg-white/70 dark:bg-surface-900/70 backdrop-blur-xl border-b border-surface-200 dark:border-surface-800 relative z-10 morph-section-bridge">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          
          <ScrollReveal variant="morph" className="text-center space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-950/70 border border-primary-200 dark:border-primary-800 text-[10px] font-bold text-primary-700 dark:text-primary-300 uppercase tracking-wider">
              <Sparkles className="w-3 h-3" />
              <span>{d.demo.badge}</span>
            </div>
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white">
              <span className="text-shimmer">{d.demo.title}</span>
            </h2>
            <p className="text-xs sm:text-sm text-surface-500 max-w-2xl mx-auto">
              {d.demo.desc}
            </p>
          </ScrollReveal>

          {/* Topic Selector Chips */}
          <ScrollReveal variant="cascade" className="flex flex-wrap items-center justify-center gap-2 pt-1" delay={100}>
            {Object.keys(TOPIC_PRESETS).map(key => {
              const t = TOPIC_PRESETS[key];
              const isSelected = activeTopicKey === key;
              return (
                <button
                  key={key}
                  onClick={() => handleSelectTopic(key)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-primary-600 text-white shadow-primary-sm scale-105 ring-2 ring-primary-500/30'
                      : 'bg-surface-100 dark:bg-surface-800 text-surface-700 dark:text-surface-300 hover:bg-surface-200 dark:hover:bg-surface-700'
                  }`}
                >
                  {t.label}
                </button>
              );
            })}
          </ScrollReveal>

          {/* Live Simulator Cockpit Card with Camera Zoom & 3D Depth */}
          <ScrollReveal variant="zoom" delay={150}>
            
              <div className="card shadow-2xl border-primary-500/40 bg-white/95 dark:bg-surface-900/95 backdrop-blur-2xl overflow-hidden scrolly-card">
                
                {/* Autonomous Status Bar */}
                <div className="px-4 sm:px-6 py-2.5 bg-gradient-to-r from-primary-500/10 via-indigo-500/10 to-emerald-500/10 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2 font-mono font-medium text-surface-800 dark:text-surface-200 truncate">
                    <span className={`w-2.5 h-2.5 rounded-full ${isAutoPlaying ? 'bg-emerald-500 animate-ping' : 'bg-amber-500'}`} />
                    <span className="truncate">{autoStatusText}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setIsAutoPlaying(!isAutoPlaying)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold font-mono flex items-center gap-1.5 transition-all cursor-pointer ${
                        isAutoPlaying
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                          : 'bg-emerald-600 text-white shadow-xs'
                      }`}
                      title={isAutoPlaying ? 'Tạm dừng chạy tự động' : 'Tiếp tục chạy tự động'}
                    >
                      {isAutoPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                      <span>{isAutoPlaying ? (language === 'vi' ? 'Tạm dừng' : 'Pause') : (language === 'vi' ? 'Tự động chạy' : 'Play')}</span>
                    </button>
                    <button
                      onClick={() => {
                        setIsAutoPlaying(true);
                        runAutonomousCycle(activeTopicKey);
                      }}
                      className="p-1 rounded-lg border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-600 dark:text-surface-300 transition-colors cursor-pointer"
                      title="Chạy lại từ đầu"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Cockpit Top Bar: Stage Navigation Tabs */}
                <div className="px-4 sm:px-6 pt-3.5 pb-3 border-b border-surface-200 dark:border-surface-800 bg-surface-50/70 dark:bg-surface-800/50 flex flex-wrap items-center justify-between gap-3">
                  
                  {/* 4 Stage Pills */}
                  <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
                    {[
                      { id: 'pico', label: language === 'vi' ? '1. Khung PICO & Boolean' : '1. PICO & Boolean', icon: Target },
                      { id: 'screening', label: language === 'vi' ? '2. Sàng lọc PRISMA & Scopus' : '2. PRISMA Screening', icon: Search },
                      { id: 'matrix', label: language === 'vi' ? '3. Ma trận So sánh PDF' : '3. Methodology Matrix', icon: Table },
                      { id: 'synthesis', label: language === 'vi' ? '4. Tổng hợp & Chat RAG' : '4. Synthesis & Grounded RAG', icon: Bot },
                    ].map((stage, i) => {
                      const Icon = stage.icon;
                      const isActive = cockpitTab === stage.id;
                      return (
                        <button
                          key={stage.id}
                          onClick={() => handleSelectTabManual(stage.id)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                            isActive
                              ? 'bg-primary-600 text-white shadow-xs ring-2 ring-primary-500/30'
                              : 'bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 border border-surface-200 dark:border-surface-700'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span>{stage.label}</span>
                        </button>
                      );
                    })}
                  </div>

                </div>

                {/* Cockpit Content Body */}
                <div className="p-6 sm:p-8 space-y-6">

                  {/* ── STAGE 1: PICO Framework & Boolean Query ──────────────── */}
                  {cockpitTab === 'pico' && (
                    <div className="space-y-6 animate-slide-up">
                      
                      {/* Active Question Bar */}
                      <div className="p-4 rounded-xl bg-surface-50 dark:bg-surface-800/70 border border-surface-200 dark:border-surface-700 space-y-1">
                        <span className="text-[10px] font-mono text-primary-600 font-bold uppercase block">{d.demo.queryLabel}</span>
                        <p className="font-mono text-sm sm:text-base text-surface-900 dark:text-white font-semibold flex items-center">
                          <span>{typedQuery || activeTopic.query}</span>
                          {isAutoPlaying && typedQuery.length < activeTopic.query.length && (
                            <span className="inline-block w-0.5 h-4 bg-primary-600 ml-1 animate-pulse" />
                          )}
                        </p>
                      </div>

                      {/* PICO 4-Quadrant Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        
                        {/* Population */}
                        <div className={`p-4 rounded-xl border space-y-1.5 transition-all duration-500 ${
                          picoActiveIdx >= 1
                            ? 'bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 ring-2 ring-indigo-500/40 shadow-sm scale-[1.01]'
                            : 'bg-surface-50 dark:bg-surface-800/40 border-surface-200 dark:border-surface-700 opacity-60'
                        }`}>
                          <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-bold text-xs">
                            <span className="w-5 h-5 rounded-md bg-indigo-600 text-white flex items-center justify-center text-[11px] font-mono shadow-xs">P</span>
                            <span>{language === 'vi' ? 'Population (Đối tượng / Vấn đề)' : 'Population (Subject)'}</span>
                            {picoActiveIdx >= 1 && <span className="badge badge-primary text-[8.5px] ml-auto">Matched ✓</span>}
                          </div>
                          <p className="text-xs text-surface-700 dark:text-surface-300 leading-relaxed">
                            {activeTopic.pico.p}
                          </p>
                        </div>

                        {/* Intervention */}
                        <div className={`p-4 rounded-xl border space-y-1.5 transition-all duration-500 ${
                          picoActiveIdx >= 2
                            ? 'bg-sky-50/80 dark:bg-sky-950/40 border-sky-300 dark:border-sky-800 ring-2 ring-sky-500/40 shadow-sm scale-[1.01]'
                            : 'bg-surface-50 dark:bg-surface-800/40 border-surface-200 dark:border-surface-700 opacity-60'
                        }`}>
                          <div className="flex items-center gap-2 text-sky-700 dark:text-sky-300 font-bold text-xs">
                            <span className="w-5 h-5 rounded-md bg-sky-600 text-white flex items-center justify-center text-[11px] font-mono shadow-xs">I</span>
                            <span>{language === 'vi' ? 'Intervention (Giải pháp AI)' : 'Intervention (Method)'}</span>
                            {picoActiveIdx >= 2 && <span className="badge badge-primary text-[8.5px] ml-auto">Matched ✓</span>}
                          </div>
                          <p className="text-xs text-surface-700 dark:text-surface-300 leading-relaxed">
                            {activeTopic.pico.i}
                          </p>
                        </div>

                        {/* Comparison */}
                        <div className={`p-4 rounded-xl border space-y-1.5 transition-all duration-500 ${
                          picoActiveIdx >= 3
                            ? 'bg-amber-50/80 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800 ring-2 ring-amber-500/40 shadow-sm scale-[1.01]'
                            : 'bg-surface-50 dark:bg-surface-800/40 border-surface-200 dark:border-surface-700 opacity-60'
                        }`}>
                          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300 font-bold text-xs">
                            <span className="w-5 h-5 rounded-md bg-amber-600 text-white flex items-center justify-center text-[11px] font-mono shadow-xs">C</span>
                            <span>{language === 'vi' ? 'Comparison (Đối chứng baseline)' : 'Comparison (Baseline)'}</span>
                            {picoActiveIdx >= 3 && <span className="badge badge-warning text-[8.5px] ml-auto">Matched ✓</span>}
                          </div>
                          <p className="text-xs text-surface-700 dark:text-surface-300 leading-relaxed">
                            {activeTopic.pico.c}
                          </p>
                        </div>

                        {/* Outcome */}
                        <div className={`p-4 rounded-xl border space-y-1.5 transition-all duration-500 ${
                          picoActiveIdx >= 4
                            ? 'bg-emerald-50/80 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 ring-2 ring-emerald-500/40 shadow-sm scale-[1.01]'
                            : 'bg-surface-50 dark:bg-surface-800/40 border-surface-200 dark:border-surface-700 opacity-60'
                        }`}>
                          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-bold text-xs">
                            <span className="w-5 h-5 rounded-md bg-emerald-600 text-white flex items-center justify-center text-[11px] font-mono shadow-xs">O</span>
                            <span>{language === 'vi' ? 'Outcome (Chỉ số đo lường)' : 'Outcome (Metrics)'}</span>
                            {picoActiveIdx >= 4 && <span className="badge badge-success text-[8.5px] ml-auto">Matched ✓</span>}
                          </div>
                          <p className="text-xs text-surface-700 dark:text-surface-300 leading-relaxed">
                            {activeTopic.pico.o}
                          </p>
                        </div>

                      </div>

                      {/* Inclusion & Exclusion Criteria */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 space-y-1">
                          <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>{language === 'vi' ? 'Tiêu chí Thu nhận (Inclusion Criteria)' : 'Inclusion Criteria'}</span>
                          </div>
                          <p className="text-xs text-surface-600 dark:text-surface-300">{activeTopic.pico.inclusion}</p>
                        </div>

                        <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 space-y-1">
                          <div className="flex items-center gap-1.5 text-xs font-bold text-rose-600 dark:text-rose-400">
                            <AlertCircle className="w-3.5 h-3.5" />
                            <span>{language === 'vi' ? 'Tiêu chí Loại trừ (Exclusion Criteria)' : 'Exclusion Criteria'}</span>
                          </div>
                          <p className="text-xs text-surface-600 dark:text-surface-300">{activeTopic.pico.exclusion}</p>
                        </div>
                      </div>

                      {/* Generated Boolean Query Box */}
                      <div className={`p-4 rounded-xl bg-surface-900 text-surface-100 dark:bg-surface-950 border transition-all duration-500 space-y-2 ${
                        picoActiveIdx >= 5
                          ? 'border-emerald-500 ring-2 ring-emerald-500/30 shadow-lg'
                          : 'border-surface-800 opacity-80'
                      }`}>
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2 font-mono text-primary-400 font-bold">
                            <FileCode className="w-4 h-4" />
                            <span>{language === 'vi' ? 'CHUỖI TRUY VẤN BOOLEAN TỐI ƯU (GENERATED BOOLEAN QUERY)' : 'SYNTHESIZED BOOLEAN SEARCH QUERY'}</span>
                            {picoActiveIdx >= 5 && <span className="badge badge-success text-[8.5px]">SYNTHESIZED ✓</span>}
                          </div>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(activeTopic.pico.booleanQuery);
                              setCopiedQuery(true);
                              setTimeout(() => setCopiedQuery(false), 2000);
                            }}
                            className="px-2.5 py-1 rounded bg-surface-800 hover:bg-surface-700 text-surface-200 font-mono text-xs flex items-center gap-1 cursor-pointer transition-colors"
                          >
                            {copiedQuery ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedQuery ? 'Đã sao chép' : 'Sao chép'}</span>
                          </button>
                        </div>
                        <code className="block font-mono text-xs text-emerald-400 p-2 rounded bg-black/40 break-all leading-relaxed">
                          {activeTopic.pico.booleanQuery}
                        </code>
                      </div>

                      {/* Next Step Manual CTA */}
                      <div className="flex items-center justify-end pt-1">
                        <button
                          onClick={() => handleSelectTabManual('screening')}
                          className="btn btn-primary btn-sm flex items-center gap-1.5 cursor-pointer shadow-primary-sm"
                        >
                          <span>{language === 'vi' ? 'Khám phá Bước 2: Sàng lọc PRISMA & Scopus →' : 'Explore Step 2: PRISMA Screening →'}</span>
                        </button>
                      </div>

                    </div>
                  )}

                  {/* ── STAGE 2: PRISMA Screening & Scopus Verification ──────── */}
                  {cockpitTab === 'screening' && (
                    <div className="space-y-6 animate-slide-up">
                      
                      {/* Query Header */}
                      <div className="space-y-1">
                        <span className="section-label block">{d.demo.queryLabel}</span>
                        <div className="font-mono text-sm sm:text-base text-surface-900 dark:text-white font-medium min-h-[28px] flex items-center">
                          <span>{activeTopic.query}</span>
                        </div>
                      </div>

                      {/* Candidate Paper Rows */}
                      <div className="space-y-2">
                        {activeTopic.rows.map((row, idx) => {
                          const isExcluded = row.status !== 'valid';
                          const isTagged = screeningProcessed && isExcluded;

                          return (
                            <div
                              key={idx}
                              className={`p-3 rounded-lg bg-surface-50 dark:bg-surface-800/70 border border-surface-200 dark:border-surface-700 flex items-center justify-between gap-3 text-xs font-medium transition-all duration-500 ${
                                isTagged ? 'opacity-60 bg-rose-50/30 dark:bg-rose-950/10 border-rose-300 dark:border-rose-900/40' : 'hover:border-primary-500/50'
                              }`}
                            >
                              <span className={`text-surface-800 dark:text-surface-200 truncate flex-1 ${isTagged ? 'line-through text-surface-400' : ''}`}>
                                {row.title}
                              </span>

                              {row.tag && screeningProcessed && (
                                <span className="badge badge-danger text-[10px] uppercase font-bold shrink-0 animate-scale-in">
                                  {row.tag}
                                </span>
                              )}

                              {!isExcluded && screeningProcessed && (
                                <span className="badge badge-success text-[10px] uppercase font-bold shrink-0 flex items-center gap-1 animate-scale-in">
                                  <Check className="w-2.5 h-2.5" /> Scopus Q1
                                </span>
                              )}

                              <span className="font-mono text-[11px] text-surface-400 shrink-0">
                                {row.venue}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Acceptance Ratio Meter */}
                      <div className="p-4 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-surface-900 dark:text-white">
                            {d.demo.meterLabel}
                          </span>
                          <span className="font-mono font-bold text-base text-emerald-600 dark:text-emerald-400">
                            {meterValue}% (3/4 Studies Qualified)
                          </span>
                        </div>

                        <div className="h-2.5 rounded-full bg-surface-200 dark:bg-surface-700 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-primary-600 to-emerald-500 transition-all duration-300"
                            style={{ width: `${meterValue}%` }}
                          />
                        </div>

                        <p className="text-[11px] text-surface-500 dark:text-surface-400">
                          💡 Hệ thống tự động phân tách tài liệu, loại bỏ nguồn không đạt chuẩn và chỉ giữ các bài báo Scopus Q1 có kiểm định định lượng.
                        </p>
                      </div>

                      {/* Navigation CTAs */}
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => handleSelectTabManual('pico')}
                          className="btn btn-secondary btn-sm text-xs cursor-pointer"
                        >
                          <span>← Quay lại PICO</span>
                        </button>
                        <button
                          onClick={() => handleSelectTabManual('matrix')}
                          className="btn btn-primary btn-sm flex items-center gap-1.5 cursor-pointer shadow-primary-sm"
                        >
                          <span>{language === 'vi' ? 'Khám phá Bước 3: Ma trận So sánh PDF →' : 'Explore Step 3: Methodology Matrix →'}</span>
                        </button>
                      </div>

                    </div>
                  )}

                  {/* ── STAGE 3: Full-Text PDF Methodology Matrix ─────────────── */}
                  {cockpitTab === 'matrix' && (
                    <div className="space-y-6 animate-slide-up">
                      
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-bold text-sm text-surface-900 dark:text-white flex items-center gap-2">
                            <Table className="w-4 h-4 text-primary-600" />
                            <span>{language === 'vi' ? 'Ma trận So sánh Phương pháp Trích xuất từ Toàn văn PDF' : 'Extracted Methodology Comparison Matrix'}</span>
                          </h3>
                          <p className="text-xs text-surface-500 mt-0.5">
                            {language === 'vi' ? 'Tự động bóc tách cấu trúc Dataset, Kiến trúc mô hình, Chỉ số đo lường và Hạn chế từ file PDF gốc.' : 'Automatically extracted model structures, datasets, metrics, and limitations from original PDFs.'}
                          </p>
                        </div>
                      </div>

                      {/* Comparison Matrix Table */}
                      <div className="overflow-x-auto rounded-xl border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800/40 shadow-xs">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-surface-100/80 dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700 text-surface-600 dark:text-surface-300 font-semibold">
                              <th className="p-3">Bài báo &amp; Tác giả</th>
                              <th className="p-3">Kiến trúc / Phương pháp</th>
                              <th className="p-3">Tập dữ liệu (Dataset)</th>
                              <th className="p-3">Kết quả Định lượng</th>
                              <th className="p-3">Hạn chế Trích xuất</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                            {activeTopic.matrix.map((row, idx) => {
                              const isScanned = matrixScanIdx >= idx;
                              return (
                                <tr
                                  key={idx}
                                  className={`transition-all duration-500 ${
                                    isScanned
                                      ? 'bg-primary-50/30 dark:bg-primary-950/20'
                                      : 'opacity-70'
                                  }`}
                                >
                                  <td className="p-3 font-semibold text-primary-700 dark:text-primary-300 whitespace-nowrap">
                                    {row.author}
                                  </td>
                                  <td className="p-3 font-mono text-[11px] text-surface-800 dark:text-surface-200">
                                    <span className="px-2 py-0.5 rounded bg-surface-100 dark:bg-surface-700 font-medium">
                                      {row.method}
                                    </span>
                                  </td>
                                  <td className="p-3 text-surface-600 dark:text-surface-300">
                                    {row.dataset}
                                  </td>
                                  <td className="p-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                                    <span className={isScanned ? 'bg-emerald-100 dark:bg-emerald-950/60 px-1.5 py-0.5 rounded' : ''}>
                                      {row.metrics}
                                    </span>
                                  </td>
                                  <td className="p-3 text-rose-600 dark:text-rose-400 italic">
                                    {row.gap}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      {/* Navigation CTAs */}
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => handleSelectTabManual('screening')}
                          className="btn btn-secondary btn-sm text-xs cursor-pointer"
                        >
                          <span>← Quay lại Sàng lọc</span>
                        </button>
                        <button
                          onClick={() => handleSelectTabManual('synthesis')}
                          className="btn btn-primary btn-sm flex items-center gap-1.5 cursor-pointer shadow-primary-sm"
                        >
                          <span>{language === 'vi' ? 'Khám phá Bước 4: Luận điểm & Chat RAG →' : 'Explore Step 4: Synthesis & RAG →'}</span>
                        </button>
                      </div>

                    </div>
                  )}

                  {/* ── STAGE 4: Grounded Synthesis, Gaps & RAG Chat ──────────── */}
                  {cockpitTab === 'synthesis' && (
                    <div className="space-y-6 animate-slide-up">
                      
                      {/* Synthesis Paragraph with Hover Citations */}
                      <div className="p-5 rounded-xl bg-surface-50/80 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 space-y-3">
                        <div className="flex items-center justify-between text-xs text-primary-600 dark:text-primary-400 font-mono font-bold uppercase tracking-wider">
                          <span>{language === 'vi' ? 'BẢN TỔNG HỢP LUẬN ĐIỂM CHUẨN HÓA DOI (100% GROUNDED SYNTHESIS)' : 'GROUNDED EVIDENCE SYNTHESIS'}</span>
                          <span className="badge badge-success text-[9px]">PRISMA INCLUDED</span>
                        </div>

                        <p className="font-display text-sm sm:text-base text-surface-900 dark:text-white leading-relaxed">
                          {activeTopic.summaryP1}
                          
                          {/* Citation 1 */}
                          <span className="relative inline-block group mx-1">
                            <button className="px-1.5 py-0.5 rounded bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-mono text-xs font-bold hover:bg-primary-600 hover:text-white transition-colors cursor-pointer ring-2 ring-primary-500/40">
                              {activeTopic.summaryCite1.id}
                            </button>
                            <span className={`absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3.5 rounded-xl bg-surface-900 text-white text-xs font-sans shadow-2xl transition-all z-30 border border-surface-700 ${
                              autoTooltipCite ? 'opacity-100 scale-100' : 'opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto'
                            }`}>
                              <span className="font-bold block text-xs leading-tight text-white">{activeTopic.summaryCite1.title}</span>
                              <span className="text-[11px] text-surface-400 block mt-1">{activeTopic.summaryCite1.author} · {activeTopic.summaryCite1.page}</span>
                              <span className="text-[10.5px] italic text-emerald-300 block mt-1.5">"{activeTopic.summaryCite1.quote}"</span>
                              <span className="badge badge-success text-[9px] mt-2 block">{activeTopic.summaryCite1.venue}</span>
                            </span>
                          </span>

                          {activeTopic.summaryP2}

                          {/* Citation 2 */}
                          <span className="relative inline-block group mx-1">
                            <button className="px-1.5 py-0.5 rounded bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-mono text-xs font-bold hover:bg-primary-600 hover:text-white transition-colors cursor-pointer">
                              {activeTopic.summaryCite2.id}
                            </button>
                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3.5 rounded-xl bg-surface-900 text-white text-xs font-sans shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-30 border border-surface-700">
                              <span className="font-bold block text-xs leading-tight text-white">{activeTopic.summaryCite2.title}</span>
                              <span className="text-[11px] text-surface-400 block mt-1">{activeTopic.summaryCite2.author} · {activeTopic.summaryCite2.page}</span>
                              <span className="text-[10.5px] italic text-emerald-300 block mt-1.5">"{activeTopic.summaryCite2.quote}"</span>
                              <span className="badge badge-success text-[9px] mt-2 block">{activeTopic.summaryCite2.venue}</span>
                            </span>
                          </span>

                          {activeTopic.summaryP3}

                          {/* Citation 3 */}
                          <span className="relative inline-block group mx-1">
                            <button className="px-1.5 py-0.5 rounded bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-mono text-xs font-bold hover:bg-primary-600 hover:text-white transition-colors cursor-pointer">
                              {activeTopic.summaryCite3.id}
                            </button>
                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3.5 rounded-xl bg-surface-900 text-white text-xs font-sans shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-30 border border-surface-700">
                              <span className="font-bold block text-xs leading-tight text-white">{activeTopic.summaryCite3.title}</span>
                              <span className="text-[11px] text-surface-400 block mt-1">{activeTopic.summaryCite3.author} · {activeTopic.summaryCite3.page}</span>
                              <span className="text-[10.5px] italic text-emerald-300 block mt-1.5">"{activeTopic.summaryCite3.quote}"</span>
                              <span className="badge badge-success text-[9px] mt-2 block">{activeTopic.summaryCite3.venue}</span>
                            </span>
                          </span>
                          
                          {activeTopic.summaryP4}
                        </p>
                      </div>

                      {/* Research Gaps Radar Cards */}
                      <div className="space-y-2.5">
                        <span className="text-xs font-bold text-surface-800 dark:text-surface-200 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-primary-600" />
                          <span>{language === 'vi' ? 'Khoảng trống Nghiên cứu Tự động Phát hiện (Research Gaps Radar):' : 'Discovered Research Opportunities (Gap Radar):'}</span>
                        </span>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {activeTopic.gaps.map((gap, i) => (
                            
                              <div className="p-3.5 rounded-xl bg-amber-50/40 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 space-y-1 scrolly-card">
                                <span className="font-bold text-xs text-amber-800 dark:text-amber-300 block">{gap.title}</span>
                                <p className="text-xs text-surface-600 dark:text-surface-400 leading-relaxed">{gap.desc}</p>
                              </div>
                            
                          ))}
                        </div>
                      </div>

                      {/* Interactive Grounded RAG Chat Simulator */}
                      <div className={`p-4 rounded-xl border space-y-3 transition-all duration-500 ${
                        ragSimActive
                          ? 'bg-primary-50/60 dark:bg-primary-950/30 border-primary-300 dark:border-primary-800 ring-2 ring-primary-500/30 shadow-md'
                          : 'bg-surface-50 dark:bg-surface-800/40 border-surface-200 dark:border-surface-700'
                      }`}>
                        <div className="flex items-center justify-between text-xs font-mono font-bold text-primary-700 dark:text-primary-300">
                          <span className="flex items-center gap-1.5">
                            <MessageSquare className="w-3.5 h-3.5 text-primary-600" />
                            <span>{language === 'vi' ? 'MÔ PHỎNG HỎI ĐÁP FACT-CHECKING RAG VỚI TOÀN VĂN PDF' : 'GROUNDED RAG PDF FACT-CHECKING SIMULATOR'}</span>
                          </span>
                          <span className="badge badge-primary text-[8.5px]">100% DOI VERIFIED</span>
                        </div>

                        {/* User Question */}
                        <div className="p-2.5 rounded-lg bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 text-xs font-medium text-surface-900 dark:text-white flex items-center gap-2 shadow-xs">
                          <span className="w-4 h-4 rounded-full bg-primary-600 text-white flex items-center justify-center text-[10px] font-bold shrink-0">Q</span>
                          <span>{activeTopic.ragSample.question}</span>
                        </div>

                        {/* AI Grounded Response with Page Quote */}
                        <div className="p-3 rounded-lg bg-surface-100/70 dark:bg-surface-900/80 border border-surface-200 dark:border-surface-800 space-y-2 text-xs">
                          <div className="flex items-center gap-1.5 text-primary-600 dark:text-primary-400 font-semibold">
                            <Bot className="w-3.5 h-3.5" />
                            <span>LitReview AI Assistant:</span>
                            <span className="badge badge-success text-[8.5px] ml-auto">{activeTopic.ragSample.pageAnchor}</span>
                          </div>
                          <p className="text-surface-800 dark:text-surface-200 leading-relaxed">
                            {activeTopic.ragSample.answer}
                          </p>
                          <div className="p-2 rounded bg-black/5 dark:bg-black/40 border border-primary-500/20 italic text-surface-600 dark:text-surface-300 text-[11.5px]">
                            {activeTopic.ragSample.quote}
                          </div>
                        </div>
                      </div>

                      {/* 1-Click Export Bar */}
                      <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs font-semibold text-surface-700 dark:text-surface-300">
                          <Download className="w-4 h-4 text-primary-600" />
                          <span>{language === 'vi' ? 'Xuất bản kết quả:' : 'Export Results:'}</span>
                          
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(activeTopic.bibtex);
                              setCopiedBib(true);
                              setTimeout(() => setCopiedBib(false), 2000);
                            }}
                            className="px-2.5 py-1 rounded bg-white dark:bg-surface-700 hover:bg-surface-100 dark:hover:bg-surface-600 border border-surface-200 dark:border-surface-600 text-xs font-mono flex items-center gap-1 transition-all cursor-pointer"
                          >
                            {copiedBib ? <CheckCheck className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3 text-primary-500" />}
                            <span>{copiedBib ? 'BibTeX Đã chép' : 'BibTeX (.bib)'}</span>
                          </button>

                          <button
                            onClick={() => onOpenAuth('demo')}
                            className="px-2.5 py-1 rounded bg-white dark:bg-surface-700 hover:bg-surface-100 dark:hover:bg-surface-600 border border-surface-200 dark:border-surface-600 text-xs font-mono flex items-center gap-1 transition-all cursor-pointer"
                          >
                            <span>CSV Table</span>
                          </button>

                          <button
                            onClick={() => onOpenAuth('demo')}
                            className="px-2.5 py-1 rounded bg-white dark:bg-surface-700 hover:bg-surface-100 dark:hover:bg-surface-600 border border-surface-200 dark:border-surface-600 text-xs font-mono flex items-center gap-1 transition-all cursor-pointer"
                          >
                            <span>Markdown (.md)</span>
                          </button>
                        </div>

                        <button
                          onClick={() => onOpenAuth('demo')}
                          className="btn btn-primary btn-sm shadow-primary-sm cursor-pointer ml-auto"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>{language === 'vi' ? 'Mở Toàn bộ Không gian Làm việc (Workspace)' : 'Open Full Workspace'}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                    </div>
                  )}

                </div>
              </div>
            
          </ScrollReveal>

          {/* 3 Metric Cards with Viewport-Triggered Counter & 3D Tilt */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            {[
              { num: d.demo.stat1Num, unit: d.demo.stat1Unit, label: d.demo.stat1Label, color: 'text-emerald-600 dark:text-emerald-400' },
              { num: d.demo.stat2Num, unit: d.demo.stat2Unit, label: d.demo.stat2Label, color: 'text-primary-600 dark:text-primary-400' },
              { num: d.demo.stat3Num, unit: d.demo.stat3Unit, label: d.demo.stat3Label, color: 'text-indigo-600 dark:text-indigo-400' },
            ].map((stat, i) => (
              <ScrollReveal key={i} variant="cascade" delay={i * 100}>
                
                  <div className="card p-5 space-y-1 scrolly-card">
                    <div className={`font-display text-3xl font-bold ${stat.color}`}>
                      <AnimatedCounter target={stat.num} suffix={stat.unit} />
                    </div>
                    <p className="text-xs text-surface-500 dark:text-surface-400">{stat.label}</p>
                  </div>
                
              </ScrollReveal>
            ))}
          </div>

        </div>
      </section>

      {/* ── 4. The 4 Specialized AI Agents ─────────────────────────────── */}
      <section id="agents" className="py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12 relative z-10 morph-section-bridge">
        <ScrollReveal variant="morph" className="text-center space-y-2">
          <span className="section-label block">{d.agents.badge}</span>
          <h2 className="font-display font-bold text-3xl text-surface-900 dark:text-white">
            <span className="text-shimmer">{d.agents.title}</span>
          </h2>
          <p className="text-xs sm:text-sm text-surface-500 max-w-2xl mx-auto">
            {d.agents.desc}
          </p>
        </ScrollReveal>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            { icon: Target, title: d.agents.a1Title, desc: d.agents.a1Desc, tag: 'MODULE 01', color: 'text-indigo-600 bg-indigo-50 dark:bg-indigo-950/60' },
            { icon: Database, title: d.agents.a2Title, desc: d.agents.a2Desc, tag: 'MODULE 02', color: 'text-sky-600 bg-sky-50 dark:bg-sky-950/60' },
            { icon: Table, title: d.agents.a3Title, desc: d.agents.a3Desc, tag: 'MODULE 03', color: 'text-violet-600 bg-violet-50 dark:bg-violet-950/60' },
            { icon: Bot, title: d.agents.a4Title, desc: d.agents.a4Desc, tag: 'MODULE 04', color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60' },
          ].map((agent, i) => {
            const Icon = agent.icon;
            return (
              <ScrollReveal key={i} variant="cascade" delay={i * 90}>
                
                  <div className="card p-6 flex flex-col justify-between hover:border-primary-400 hover:shadow-xl transition-all group backdrop-blur-md scrolly-card min-h-[260px]">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <div className={`w-10 h-10 rounded-xl ${agent.color} flex items-center justify-center group-hover:scale-110 group-hover:rotate-6 transition-transform shadow-xs`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <span className="badge badge-neutral text-[9px] font-mono">{agent.tag}</span>
                      </div>
                      <h3 className="font-display font-bold text-base text-surface-900 dark:text-white mb-2 leading-snug">
                        {agent.title}
                      </h3>
                      <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed">
                        {agent.desc}
                      </p>
                    </div>
                  </div>
                
              </ScrollReveal>
            );
          })}
        </div>
      </section>

      {/* ── 5. Methodology Comparison Matrix & Research Gaps Preview ──── */}
      <section id="matrix" className="py-20 bg-surface-100/60 dark:bg-surface-900/40 border-y border-surface-200 dark:border-surface-800 relative z-10 morph-section-bridge">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          
          <ScrollReveal variant="morph" className="max-w-3xl space-y-2">
            <span className="section-label block">{d.matrixSection.badge}</span>
            <h2 className="font-display font-bold text-3xl text-surface-900 dark:text-white">
              <span className="text-shimmer">{d.matrixSection.title}</span>
            </h2>
            <p className="text-xs sm:text-sm text-surface-500 leading-relaxed">
              {d.matrixSection.desc}
            </p>
          </ScrollReveal>

          {/* Interactive Synthesis Matrix Table with 3D Morph Ingress */}
          <ScrollReveal variant="zoom" delay={100}>
            
              <div className="card overflow-hidden shadow-xl border-surface-200 dark:border-surface-800 scrolly-card">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-surface-100 dark:bg-surface-800/80 border-b border-surface-200 dark:border-surface-700 text-surface-700 dark:text-surface-300 font-bold uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="p-3.5">{d.matrixSection.colAuthor}</th>
                        <th className="p-3.5">{d.matrixSection.colMethod}</th>
                        <th className="p-3.5">{d.matrixSection.colDataset}</th>
                        <th className="p-3.5">{d.matrixSection.colMetrics}</th>
                        <th className="p-3.5">{d.matrixSection.colGap}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                      {activeTopic.matrix.map((row, idx) => (
                        <tr key={idx} className="hover:bg-primary-50/20 dark:hover:bg-primary-950/20 transition-colors">
                          <td className="p-3.5 font-bold text-surface-900 dark:text-white whitespace-nowrap">{row.author}</td>
                          <td className="p-3.5 text-primary-600 dark:text-primary-400 font-medium">{row.method}</td>
                          <td className="p-3.5 text-surface-600 dark:text-surface-300">{row.dataset}</td>
                          <td className="p-3.5 font-mono text-emerald-600 dark:text-emerald-400 font-semibold">{row.metrics}</td>
                          <td className="p-3.5 text-amber-600 dark:text-amber-400 text-[11px] leading-relaxed">{row.gap}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            
          </ScrollReveal>

          {/* Discovered Gaps Radar Cards */}
          <div className="space-y-4">
            <ScrollReveal variant="morph" className="font-display font-bold text-base text-surface-900 dark:text-white flex items-center gap-2">
              <Target className="w-4 h-4 text-violet-500" />
              <span>{d.matrixSection.gapsTitle}</span>
            </ScrollReveal>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {activeTopic.gaps.map((gap, i) => (
                <ScrollReveal key={i} variant="cascade" delay={i * 90}>
                  
                    <div className="card p-5 border-amber-200 dark:border-amber-900/40 bg-amber-50/20 dark:bg-amber-950/10 space-y-2 scrolly-card">
                      <div className="flex items-center justify-between">
                        <span className="badge badge-warning text-[9px]">Research Opportunity #{i + 1}</span>
                        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-bold uppercase">Unsolved Gap</span>
                      </div>
                      <h4 className="font-bold text-xs text-surface-900 dark:text-white">{gap.title}</h4>
                      <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed">{gap.desc}</p>
                    </div>
                  
                </ScrollReveal>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* ── 6. PRISMA 2020 Protocol Flowchart ──────────────────────────── */}
      <section id="prisma" className="py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12 relative z-10 morph-section-bridge">
        <ScrollReveal variant="morph" className="text-center space-y-2">
          <span className="section-label block">{d.prismaSection.badge}</span>
          <h2 className="font-display font-bold text-3xl text-surface-900 dark:text-white">
            <span className="text-shimmer">{d.prismaSection.title}</span>
          </h2>
          <p className="text-xs sm:text-sm text-surface-500 max-w-2xl mx-auto">
            {d.prismaSection.desc}
          </p>
        </ScrollReveal>

        <div className="relative">
          {/* Animated Connecting Laser Beam Line */}
          <div className="hidden lg:block absolute top-1/2 left-8 right-8 h-1 laser-beam-line -translate-y-1/2 z-0 rounded-full opacity-60 pointer-events-none" />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
            {[
              { num: d.prismaSection.s1Num, title: d.prismaSection.s1Title, desc: d.prismaSection.s1Desc, tag: 'N = 100+ Records' },
              { num: d.prismaSection.s2Num, title: d.prismaSection.s2Title, desc: d.prismaSection.s2Desc, tag: 'Scopus Matched' },
              { num: d.prismaSection.s3Num, title: d.prismaSection.s3Title, desc: d.prismaSection.s3Desc, tag: 'Inclusion Scored' },
              { num: d.prismaSection.s4Num, title: d.prismaSection.s4Title, desc: d.prismaSection.s4Desc, tag: 'Synthesis Matrix' },
            ].map((st, i) => (
              <ScrollReveal key={i} variant="cascade" delay={i * 100}>
                
                  <div className="card p-5 space-y-3 relative hover:border-primary-500 hover:shadow-xl transition-all scrolly-card min-h-[190px]">
                    <div className="flex items-center justify-between">
                      <span className="w-8 h-8 rounded-xl bg-primary-600 text-white font-mono font-bold text-xs flex items-center justify-center shadow-xs">
                        {st.num}
                      </span>
                      <span className="badge badge-primary text-[9px] font-mono">{st.tag}</span>
                    </div>
                    <h4 className="font-display font-bold text-sm text-surface-900 dark:text-white">{st.title}</h4>
                    <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed">{st.desc}</p>
                  </div>
                
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── 7. 1-Click Interactive Demo Accounts ───────────────────────── */}
      <section id="demo-accounts" className="py-20 bg-surface-100/60 dark:bg-surface-900/40 border-y border-surface-200 dark:border-surface-800 relative z-10 morph-section-bridge">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
          
          <ScrollReveal variant="morph" className="text-center space-y-2">
            <span className="section-label block">{d.demoAccounts.badge}</span>
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white">
              <span className="text-shimmer">{d.demoAccounts.title}</span>
            </h2>
            <p className="text-xs sm:text-sm text-surface-500 max-w-2xl mx-auto">
              {d.demoAccounts.desc}
            </p>
          </ScrollReveal>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            
            {/* TS. Nguyen Hai */}
            <ScrollReveal variant="left" delay={100}>
              
                <div className="card p-6 flex flex-col justify-between space-y-4 hover:border-primary-500 hover:shadow-xl transition-all scrolly-card">
                  <div className="flex items-start gap-3.5">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600 to-indigo-700 text-white font-bold flex items-center justify-center text-base shadow-primary-sm shrink-0">
                      NH
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-sm text-surface-900 dark:text-white">{d.demoAccounts.u1Name}</h3>
                        <span className="badge badge-primary text-[10px]">{d.demoAccounts.u1Role}</span>
                      </div>
                      <p className="text-xs text-surface-500 mt-0.5">{d.demoAccounts.u1Inst}</p>
                      <p className="text-xs text-surface-700 dark:text-surface-300 mt-2 bg-surface-50 dark:bg-surface-800 p-2.5 rounded-lg border border-surface-200 dark:border-surface-700">
                        {d.demoAccounts.u1Project}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => onOpenAuth('demo')}
                    className="btn btn-primary btn-sm w-full shadow-primary-sm cursor-pointer"
                  >
                    <span>{d.demoAccounts.u1Btn}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              
            </ScrollReveal>

            {/* Minh Pham */}
            <ScrollReveal variant="right" delay={200}>
              
                <div className="card p-6 flex flex-col justify-between space-y-4 hover:border-primary-500 hover:shadow-xl transition-all scrolly-card">
                  <div className="flex items-start gap-3.5">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600 to-primary-700 text-white font-bold flex items-center justify-center text-base shadow-sm shrink-0">
                      MP
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-sm text-surface-900 dark:text-white">{d.demoAccounts.u2Name}</h3>
                        <span className="badge badge-success text-[10px]">{d.demoAccounts.u2Role}</span>
                      </div>
                      <p className="text-xs text-surface-500 mt-0.5">{d.demoAccounts.u2Inst}</p>
                      <p className="text-xs text-surface-700 dark:text-surface-300 mt-2 bg-surface-50 dark:bg-surface-800 p-2.5 rounded-lg border border-surface-200 dark:border-surface-700">
                        {d.demoAccounts.u2Project}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => onOpenAuth('demo')}
                    className="btn btn-secondary btn-sm w-full cursor-pointer"
                  >
                    <span>{d.demoAccounts.u2Btn}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              
            </ScrollReveal>

          </div>

        </div>
      </section>

      {/* ── 8. FAQ Accordion ───────────────────────────────────────────── */}
      <section id="faq" className="py-20 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8 relative z-10 morph-section-bridge">
        <ScrollReveal variant="morph" className="text-center space-y-2">
          <span className="section-label block">{d.faq.badge}</span>
          <h2 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white">
            <span className="text-shimmer">{d.faq.title}</span>
          </h2>
        </ScrollReveal>

        <div className="space-y-3">
          {[
            { q: d.faq.q1, a: d.faq.a1 },
            { q: d.faq.q2, a: d.faq.a2 },
            { q: d.faq.q3, a: d.faq.a3 },
            { q: d.faq.q4, a: d.faq.a4 },
          ].map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <ScrollReveal key={idx} variant="morph" delay={idx * 60} className="card overflow-hidden transition-all scrolly-card">
                <button
                  type="button"
                  onClick={() => setOpenFaq(isOpen ? -1 : idx)}
                  className="w-full p-4 text-left font-bold text-xs sm:text-sm text-surface-900 dark:text-white flex items-center justify-between gap-4 hover:text-primary-600 transition-colors cursor-pointer"
                >
                  <span>{faq.q}</span>
                  <span className={`font-mono text-base text-primary-600 transition-transform duration-200 ${isOpen ? 'rotate-45' : ''}`}>
                    +
                  </span>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 text-xs text-surface-500 dark:text-surface-400 leading-relaxed border-t border-surface-100 dark:border-surface-800 pt-3">
                    {faq.a}
                  </div>
                )}
              </ScrollReveal>
            );
          })}
        </div>
      </section>

      {/* ── 9. Product Development Team ─────────────────────────────────── */}
      <section id="team" className="py-20 bg-surface-100/60 dark:bg-surface-900/40 border-y border-surface-200 dark:border-surface-800 relative z-10 morph-section-bridge">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          
          <ScrollReveal variant="morph" className="text-center space-y-2">
            <span className="section-label block">{d.team.badge}</span>
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white">
              <span className="text-shimmer">{d.team.title}</span>
            </h2>
            <p className="text-xs sm:text-sm text-surface-500 max-w-2xl mx-auto">
              {d.team.desc}
            </p>
          </ScrollReveal>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {d.team.members.map((member, idx) => (
              <ScrollReveal key={idx} variant="cascade" delay={idx * 80}>
                <div className="card p-6 flex flex-col items-center text-center space-y-4 hover:border-primary-500/80 hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 group backdrop-blur-md scrolly-card relative overflow-hidden bg-surface-50/80 dark:bg-surface-900/60 border border-surface-200/80 dark:border-surface-800 rounded-2xl">
                  
                  {/* Subtle top accent bar */}
                  <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${member.color} opacity-90`} />

                  {/* Avatar / Portrait Photo Container */}
                  <div className="relative w-32 h-32 rounded-2xl overflow-hidden shadow-md ring-2 ring-surface-200 dark:ring-surface-700/80 group-hover:ring-primary-500/60 group-hover:shadow-primary-500/20 group-hover:shadow-lg transition-all duration-300 bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                    <img
                      src={member.img}
                      alt={member.name}
                      style={{ objectPosition: member.imgPosition || 'center 15%' }}
                      onError={(e) => {
                        if (e.target.src !== member.imgPublic) {
                          e.target.src = member.imgPublic;
                        } else {
                          e.target.style.display = 'none';
                          const fallback = e.target.parentElement.querySelector('.member-fallback');
                          if (fallback) fallback.style.display = 'flex';
                        }
                      }}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    {/* Fallback Initials */}
                    <div className={`member-fallback w-full h-full bg-gradient-to-br ${member.color} text-white font-bold text-2xl flex items-center justify-center shadow-inner`} style={{ display: 'none' }}>
                      {member.initials}
                    </div>
                  </div>

                  {/* Name and Student Info */}
                  <div className="space-y-1.5 w-full flex-1 flex flex-col justify-between">
                    <div>
                      <h3 className="font-display font-bold text-base text-surface-900 dark:text-white leading-snug group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                        {member.name}
                      </h3>
                      
                      <div className="flex items-center justify-center gap-1.5 pt-1.5">
                        <span className="inline-flex items-center gap-1 font-mono text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-primary-500/10 text-primary-600 dark:text-primary-400 border border-primary-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-pulse"></span>
                          ID: {member.studentId}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 text-xs border-t border-surface-200/60 dark:border-surface-800/80 w-full mt-2">
                      <span className="block text-primary-700 dark:text-primary-300 font-semibold">{member.role}</span>
                      <span className="text-[11px] text-surface-500 dark:text-surface-400">{member.course}</span>
                    </div>
                  </div>

                </div>
              </ScrollReveal>
            ))}
          </div>

        </div>
      </section>

      {/* ── 10. Special Acknowledgments & Gratitude ──────────────────────── */}
      <section id="acknowledgments" className="py-20 bg-gradient-to-b from-transparent via-primary-500/5 to-transparent relative z-10 morph-section-bridge">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          
          <ScrollReveal variant="morph" className="text-center space-y-2">
            <span className="section-label block">{d.acknowledgments.badge}</span>
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white">
              <span className="text-shimmer">{d.acknowledgments.title}</span>
            </h2>
          </ScrollReveal>

          <ScrollReveal variant="zoom" delay={100}>
            <div className="card p-8 sm:p-10 border-primary-200/80 dark:border-primary-900/60 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl shadow-2xl relative overflow-hidden space-y-6 scrolly-card">
              
              {/* Decorative background glow */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

              <div className="flex items-center gap-3 text-amber-500">
                <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/60 flex items-center justify-center border border-amber-200 dark:border-amber-800/80 shadow-xs">
                  <Sparkles className="w-5 h-5 animate-pulse" />
                </div>
                <div>
                  <span className="font-display font-bold text-sm text-surface-900 dark:text-white block">
                    {language === 'vi' ? 'Chương trình AI Thực Chiến — Khóa 3' : 'AI Engineering Program — Cohort 3'}
                  </span>
                  <span className="text-xs text-surface-500">
                    {language === 'vi' ? 'Dự án Capstone Tốt nghiệp Khóa Học' : 'Graduation Capstone Project'}
                  </span>
                </div>
              </div>

              <div className="space-y-4 text-surface-700 dark:text-surface-300 text-sm sm:text-[15px] leading-relaxed relative z-10 font-normal">
                <p className="indent-6 sm:indent-8">
                  {d.acknowledgments.p1}
                </p>
                <p className="indent-6 sm:indent-8">
                  {d.acknowledgments.p2}
                </p>
                <p className="indent-6 sm:indent-8 font-medium text-primary-700 dark:text-primary-300">
                  {d.acknowledgments.p3}
                </p>
              </div>

              {/* Signature block */}
              <div className="pt-4 border-t border-surface-200/80 dark:border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                <span className="font-bold text-surface-900 dark:text-white flex items-center gap-2">
                  <Award className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  <span>{d.acknowledgments.signature}</span>
                </span>
                <span className="badge badge-primary font-mono text-[10px] px-3 py-1 font-bold">
                  AI20K Cohort 3
                </span>
              </div>

            </div>
          </ScrollReveal>

        </div>
      </section>

      {/* ── 9. Final CTA ───────────────────────────────────────────────── */}
      <section className="py-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6 relative z-10 morph-section-bridge">
        <ScrollReveal variant="zoom" className="space-y-4">
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-surface-900 dark:text-white max-w-2xl mx-auto leading-tight">
            <span className="text-shimmer">{d.final.title}</span>
          </h2>
          <p className="text-xs sm:text-sm text-surface-500 max-w-xl mx-auto">
            {d.final.desc}
          </p>
          <div className="pt-3">
            <button
              onClick={() => onOpenAuth('demo')}
              className="btn btn-primary btn-lg shadow-primary-md hover:scale-105 transition-transform cursor-pointer"
            >
              <span>{d.final.btn}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </ScrollReveal>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────── */}
      <footer className="py-8 border-t border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 relative z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-surface-400">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-primary-600" />
            <span className="font-bold text-surface-700 dark:text-surface-300">LitReview AI</span>
            <span>— {d.final.footerTagline}</span>
          </div>
          <p>© {new Date().getFullYear()} VinUni AI Team 165. {d.final.footerSub}</p>
        </div>
      </footer>

    </div>
  );
}
