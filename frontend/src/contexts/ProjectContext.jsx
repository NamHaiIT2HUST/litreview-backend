import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { API_BASE, safeFetch } from '../utils/apiConfig';

const ProjectContext = createContext();

const INITIAL_DEMO_PROJECTS = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    name: 'Ứng dụng Deep Learning trong Phân loại và Chẩn đoán Tín hiệu Điện tim (ECG)',
    research_question: 'Các mô hình 1D-CNN và Transformer có độ chính xác và khả năng tổng quát hóa ra sao trong phát hiện rối loạn nhịp tim từ dữ liệu ECG thời gian thực?',
    research_field: 'Y tế & Chẩn đoán Y sinh',
    year_from: 2020,
    year_to: 2026,
    criteria_include: [
      'Bài báo xuất bản bằng tiếng Anh trong giai đoạn 2020 - 2026',
      'Sử dụng mô hình học sâu (Deep Learning, CNN, Transformer, LSTM)',
      'Tập trung vào phân loại và chẩn đoán tín hiệu ECG (Electrocardiogram)',
      'Có kiểm thử định lượng với các chỉ số Accuracy, F1-Score, Sensitivity'
    ],
    criteria_exclude: [
      'Các bài báo tổng quan lý thuyết thuần túy không có thực nghiệm',
      'Dữ liệu nghiên cứu không rõ nguồn gốc hoặc cỡ mẫu dưới 50 bệnh nhân',
      'Các nghiên cứu không công bố mã nguồn hoặc quy trình tiền xử lý'
    ],
    status: 'in_progress',
    paper_count: 14,
    screened_count: 8,
    gaps_count: 4,
    created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    name: 'Khảo sát Tổng quan về Chuỗi Tư duy (Chain-of-Thought) trong Mô hình Ngôn ngữ Lớn',
    research_question: 'Cơ chế prompting Chain-of-Thought và Tree-of-Thoughts cải thiện khả năng suy luận logic và toán học của LLMs như thế nào?',
    research_field: 'Toán học & Tối ưu hóa',
    year_from: 2022,
    year_to: 2026,
    criteria_include: [
      'Nghiên cứu về CoT prompting, ToT, Self-Consistency trên LLM',
      'Đánh giá trên các benchmark GSM8K, MATH, HumanEval, BBH',
      'Xuất bản tại các hội nghị đầu ngành (NeurIPS, ICML, ICLR, ACL)'
    ],
    criteria_exclude: [
      'Bài báo chỉ áp dụng LLM cho tác vụ dịch thuật hoặc chat thông thường',
      'Không có phân tích định lượng hiệu năng suy luận'
    ],
    status: 'screening',
    paper_count: 9,
    screened_count: 4,
    gaps_count: 2,
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
  }
];

export function ProjectProvider({ children }) {
  const { currentUser, token } = useAuth();
  const userId = currentUser?.id || 'guest';
  const isDemoUser = Boolean(currentUser?.id && (currentUser.id === 'user_researcher_01' || currentUser.id === 'user_student_02' || currentUser.id.startsWith('user_')));

  const [projects, setProjects] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_projects_${userId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.filter(p => String(p.id) !== '00000000-0000-0000-0000-000000000001' && p.name !== 'Default Project');
        }
      }
    } catch {}
    return isDemoUser ? INITIAL_DEMO_PROJECTS : [];
  });

  const [activeProjectId, setActiveProjectId] = useState(() => {
    try {
      const savedActiveId = localStorage.getItem(`litreview_active_project_id_${userId}`);
      if (savedActiveId && savedActiveId !== '00000000-0000-0000-0000-000000000001') return savedActiveId;
      const saved = localStorage.getItem(`litreview_projects_${userId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        const valid = Array.isArray(parsed) ? parsed.filter(p => String(p.id) !== '00000000-0000-0000-0000-000000000001' && p.name !== 'Default Project') : [];
        if (valid.length > 0 && valid[0]?.id) return valid[0].id;
      }
    } catch {}
    return isDemoUser ? INITIAL_DEMO_PROJECTS[0].id : null;
  });

  // Switch project state when switching user
  useEffect(() => {
    try {
      const saved = localStorage.getItem(`litreview_projects_${userId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          const filtered = parsed.filter(p => String(p.id) !== '00000000-0000-0000-0000-000000000001' && p.name !== 'Default Project');
          setProjects(filtered);
          const savedActiveId = localStorage.getItem(`litreview_active_project_id_${userId}`);
          setActiveProjectId(savedActiveId && filtered.some(p => p.id === savedActiveId) ? savedActiveId : (filtered[0]?.id || null));
          return;
        }
      }
    } catch {}
    if (isDemoUser) {
      setProjects(INITIAL_DEMO_PROJECTS);
      setActiveProjectId(INITIAL_DEMO_PROJECTS[0].id);
    } else {
      setProjects([]);
      setActiveProjectId(null);
    }
  }, [userId, isDemoUser]);

  // Fetch backend projects only if in production/backend connected
  useEffect(() => {
    const fetchBackendProjects = async () => {
      try {
        const res = await safeFetch(`${API_BASE}/projects`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(userId ? { 'X-User-Id': userId } : {}),
          },
        });
        if (res.ok) {
          const backendProjects = await res.json();
          if (Array.isArray(backendProjects)) {
            const validBackend = backendProjects.filter(bp => String(bp.id) !== '00000000-0000-0000-0000-000000000001' && bp.name !== 'Default Project');
            setProjects(prev => {
              const map = new Map();
              prev.forEach(p => {
                if (String(p.id) !== '00000000-0000-0000-0000-000000000001' && p.name !== 'Default Project') {
                  map.set(p.id, p);
                }
              });
              validBackend.forEach(bp => {
                if (!bp.user_id || bp.user_id === userId || currentUser?.role === 'admin') {
                  map.set(bp.id, {
                    ...map.get(bp.id),
                    ...bp,
                    id: String(bp.id),
                  });
                }
              });
              return Array.from(map.values());
            });
          }
        }
      } catch (err) {
        // Fallback to localStorage
      }
    };
    if (userId && !isDemoUser) {
      fetchBackendProjects();
    }
  }, [userId, isDemoUser, token]);

  // Persist projects to localStorage per user
  useEffect(() => {
    localStorage.setItem(`litreview_projects_${userId}`, JSON.stringify(projects));
  }, [projects, userId]);

  // Persist active project id
  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_active_project_id_${userId}`, activeProjectId);
    } else {
      localStorage.removeItem(`litreview_active_project_id_${userId}`);
    }
  }, [activeProjectId, userId]);

  const activeProject = projects.find(p => p.id === activeProjectId) || projects[0] || null;

  const createProject = async (projectData = {}) => {
    const newId = `proj_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    const newProject = {
      id: newId,
      name: projectData.name !== undefined ? projectData.name : '',
      research_question: projectData.research_question || '',
      research_field: projectData.research_field || '',
      year_from: projectData.year_from || 2020,
      year_to: projectData.year_to || new Date().getFullYear(),
      criteria_include: projectData.criteria_include || [],
      criteria_exclude: projectData.criteria_exclude || [],
      status: 'in_progress',
      paper_count: 0,
      screened_count: 0,
      gaps_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Try backend sync
    try {
      const res = await safeFetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(userId ? { 'X-User-Id': userId } : {}),
        },
        body: JSON.stringify({
          name: newProject.name,
          research_question: newProject.research_question,
          research_field: newProject.research_field,
          year_from: newProject.year_from,
          year_to: newProject.year_to,
          criteria_include: newProject.criteria_include,
          criteria_exclude: newProject.criteria_exclude,
        })
      });
      if (res.ok) {
        const created = await res.json();
        if (created.id) newProject.id = String(created.id);
      }
    } catch (e) {
      console.warn("Backend project creation failed, using local ID:", e);
    }

    // Initialize 100% clean, fresh storage keys for this new project
    const defaultWelcome = [
      {
        sender: 'ai',
        isWelcome: true,
        text: "",
      }
    ];
    try {
      localStorage.setItem(`litreview_workspace_chat_${newProject.id}`, JSON.stringify(defaultWelcome));
      localStorage.setItem(`litreview_papers_${newProject.id}`, JSON.stringify([]));
      localStorage.setItem(`litreview_selected_ids_${newProject.id}`, JSON.stringify([]));
      localStorage.setItem(`litreview_selected_papers_${newProject.id}`, JSON.stringify([]));
      localStorage.setItem(`litreview_workspace_papers_${newProject.id}`, JSON.stringify([]));
      localStorage.setItem(`litreview_workspace_subtab_${newProject.id}`, 'chat');
    } catch {}

    setProjects(prev => [newProject, ...prev]);
    setActiveProjectId(newProject.id);
    return newProject;
  };

  const switchProject = (projectId) => {
    if (projects.some(p => p.id === projectId)) {
      setActiveProjectId(projectId);
    }
  };

  const updateProject = async (projectId, data) => {
    const updatedList = projects.map(p => {
      if (p.id === projectId) {
        return {
          ...p,
          ...data,
          updated_at: new Date().toISOString(),
        };
      }
      return p;
    });
    setProjects(updatedList);

    // Sync to backend if possible
    try {
      await safeFetch(`${API_BASE}/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } catch {}
  };

  const togglePinProject = (projectId) => {
    setProjects(prev =>
      prev.map(p => {
        if (p.id === projectId) {
          return { ...p, is_pinned: !p.is_pinned };
        }
        return p;
      })
    );
  };

  const renameProject = async (projectId, newName) => {
    if (!newName || !newName.trim()) return;
    const trimmed = newName.trim();
    setProjects(prev =>
      prev.map(p => {
        if (p.id === projectId) {
          return { ...p, name: trimmed, updated_at: new Date().toISOString() };
        }
        return p;
      })
    );

    // Sync to backend if possible
    try {
      await safeFetch(`${API_BASE}/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
    } catch {}
  };

  const deleteProject = async (projectId) => {
    const remaining = projects.filter(p => p.id !== projectId);
    setProjects(remaining);

    if (activeProjectId === projectId) {
      setActiveProjectId(remaining.length > 0 ? remaining[0].id : null);
    }

    // Sync to backend if possible
    try {
      await safeFetch(`${API_BASE}/projects/${projectId}`, {
        method: 'DELETE',
      });
    } catch (e) {
      console.warn("Backend project deletion warning:", e);
    }
  };

  const duplicateProject = (projectId) => {
    const source = projects.find(p => p.id === projectId);
    if (!source) return;
    const duplicated = {
      ...source,
      id: `proj_${Date.now()}_dup`,
      name: `${source.name} (Bản sao)`,
      is_pinned: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setProjects(prev => [duplicated, ...prev]);
    setActiveProjectId(duplicated.id);
  };

  const shareProject = async (projectId) => {
    const target = projects.find(p => p.id === projectId) || activeProject;
    if (!target) return { success: false };
    const shareUrl = `${window.location.origin}/#overview?project=${target.id}`;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(shareUrl);
      }
      return { success: true, url: shareUrl, projectName: target.name };
    } catch (e) {
      return { success: true, url: shareUrl, projectName: target.name };
    }
  };

  // Sort projects: Pinned first, then by updated_at / created_at desc
  const sortedProjects = [...projects].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0);
  });

  return (
    <ProjectContext.Provider
      value={{
        projects: sortedProjects,
        rawProjects: projects,
        activeProject,
        activeProjectId,
        createProject,
        switchProject,
        updateProject,
        renameProject,
        togglePinProject,
        deleteProject,
        duplicateProject,
        shareProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}
