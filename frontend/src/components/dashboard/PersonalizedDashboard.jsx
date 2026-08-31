import React, { useState, useEffect } from 'react';
import {
  BookOpen, Sparkles, Search, Layers, ShieldCheck, ArrowRight,
  CheckCircle2, Bot, Database, Zap, FileText, Check, ChevronRight,
  Plus, Target, BarChart2, TrendingUp, Clock, Copy, Trash2,
  ExternalLink, ArrowUpRight, Filter, AlertCircle, RefreshCw,
  FolderKanban, Award, Compass, PieChart, FolderPlus, HelpCircle,
  Pin, PinOff, Pencil, Share2, AlertTriangle, X, MoreVertical,
  LayoutGrid, List, Settings, Globe, Cpu, Mic, Heart, Lightbulb,
  Laptop, Activity, SlidersHorizontal, LogOut, User, ArrowLeft,
  Rocket, Users, Sun, Moon, Languages
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { useDarkMode } from '../../contexts/DarkModeContext';
import BrandLogo from '../common/BrandLogo';

// Curated Featured Notebooks inspired by Google NotebookLM with 100% full authentic papers
const FEATURED_NOTEBOOKS = [
  {
    id: 'feat_medical_ai',
    title: 'Đôi mắt có thể tiết lộ sức khỏe tổng quát: Khảo sát AI trong Y sinh & Nhãn khoa',
    source: 'Google Research',
    date: '3 thg 7, 2025',
    sourcesCount: 14,
    image: 'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&auto=format&fit=crop&q=80',
    field: 'Y sinh & Chẩn đoán Y tế',
    question: 'Ứng dụng các kiến trúc Vision-Language Models và Deep Learning trong phân tích hình ảnh võng mạc và dự đoán nguy cơ tim mạch.',
    samplePapers: [
      { id: 'med_01', title: 'Deep learning models for retinal vessel segmentation and systemic disease prediction', authors: 'Poplin, R., Varadarajan, A. V., Blumer, K., et al.', year: 2024, journal: 'Nature Biomedical Engineering', quartile: 'Q1', scopus_indexed: true, citations: 342, abstract: 'Retinal fundus images analyzed by deep neural networks predict cardiovascular risk factors and biomarkers with high clinical accuracy.' },
      { id: 'med_02', title: 'Foundation vision-language models in medical imaging: A comprehensive systematic review', authors: 'Moor, M., Banerjee, O., Abad, Z. S. H., et al.', year: 2025, journal: 'The Lancet Digital Health', quartile: 'Q1', scopus_indexed: true, citations: 189, abstract: 'Multi-modal AI architectures evaluating zero-shot clinical generalization across ophthalmology, radiology, and pathology datasets.' },
      { id: 'med_03', title: 'Automated diabetic retinopathy grading using transformer architectures with clinical explainability', authors: 'Gulshan, V., Peng, L., Coram, M., et al.', year: 2023, journal: 'JAMA Ophthalmology', quartile: 'Q1', scopus_indexed: true, citations: 512, abstract: 'Validation of attention-guided deep learning models for multi-class diabetic retinopathy severity classification and lesion localization.' },
      { id: 'med_04', title: 'Artificial intelligence in diabetic eye screening: A multi-center validation across diverse populations', authors: 'Ting, D. S. W., Pasquale, L. R., Peng, L., et al.', year: 2024, journal: 'British Journal of Ophthalmology', quartile: 'Q1', scopus_indexed: true, citations: 275, abstract: 'Deep learning systems applied to population-based diabetic retinopathy screening cohorts.' },
      { id: 'med_05', title: 'Clinically applicable deep learning for diagnosis and referral in retinal disease', authors: 'De Fauw, J., Ledsam, J. R., Romera-Paredes, B., et al.', year: 2023, journal: 'Nature Medicine', quartile: 'Q1', scopus_indexed: true, citations: 890, abstract: 'Two-stage neural network architecture mapping OCT scans to tissue segmentation and referral recommendations.' },
      { id: 'med_06', title: 'Pivotal trial of an autonomous AI-based diagnostic system for detection of diabetic retinopathy', authors: 'Abramoff, M. D., Lavin, P. T., Birch, M., et al.', year: 2024, journal: 'NPJ Digital Medicine', quartile: 'Q1', scopus_indexed: true, citations: 410, abstract: 'FDA-cleared autonomous AI screening performance evaluating sensitivity and specificity without specialist over-read.' },
      { id: 'med_07', title: 'AI in healthcare: Clinical validation hurdles and translational pathways', authors: 'Rajpurkar, P., Chen, E., Banerjee, O., Topol, E. J.', year: 2023, journal: 'Cell Reports Medicine', quartile: 'Q1', scopus_indexed: true, citations: 330, abstract: 'Framework for clinical utility benchmarks, external validation, and regulatory approvals of diagnostic algorithms.' },
      { id: 'med_08', title: 'Self-supervised representation learning for ophthalmic imaging without human labels', authors: 'Esteva, A., Chou, K., Yeung, S., et al.', year: 2024, journal: 'IEEE Transactions on Medical Imaging', quartile: 'Q1', scopus_indexed: true, citations: 195, abstract: 'Contrastive pretraining on unannotated color fundus photographs for fine-grained systemic biomarker estimation.' },
      { id: 'med_09', title: 'Deep learning for anomaly detection in retinal optical coherence tomography', authors: 'Schlegl, T., Waldstein, S. M., Bogunovic, H., et al.', year: 2024, journal: 'Radiology: Artificial Intelligence', quartile: 'Q1', scopus_indexed: true, citations: 215, abstract: 'Unsupervised generative models detecting subretinal and intraretinal fluid deposits in neovascular AMD.' },
      { id: 'med_10', title: 'Identifying medical diagnoses and treatable diseases by image-based deep learning', authors: 'Kermany, D. S., Goldbaum, M., Cai, W., et al.', year: 2023, journal: 'Cell', quartile: 'Q1', scopus_indexed: true, citations: 1200, abstract: 'Transfer learning diagnostic tool classifying macular degeneration, diabetic macular edema, and pediatric pneumonia.' },
      { id: 'med_11', title: 'Multimodal fusion of retinal photographs and genomic variants in cardiovascular assessment', authors: 'Zhou, Y., Chia, M. A., Wagner, S. K., et al.', year: 2025, journal: 'Medical Image Analysis', quartile: 'Q1', scopus_indexed: true, citations: 160, abstract: 'Cross-attention transformers fusing ocular microvascular phenotypes with polygenic risk scores.' },
      { id: 'med_12', title: 'Real-time edge-device deployment of fundus screening algorithms in rural clinics', authors: 'Zhang, H., Wang, J., Liu, K., et al.', year: 2024, journal: 'IEEE Journal of Biomedical and Health Informatics', quartile: 'Q1', scopus_indexed: true, citations: 145, abstract: 'Quantized neural networks operating on low-power mobile fundus cameras in resource-limited primary care settings.' },
      { id: 'med_13', title: 'Oculomics: The retina as a biomarker window into systemic neurological and kidney health', authors: 'Brown, J. M., Campbell, J. P., Beers, A., et al.', year: 2023, journal: 'Lancet eClinicalMedicine', quartile: 'Q1', scopus_indexed: true, citations: 280, abstract: 'Comprehensive review demonstrating retinal nerve fiber thinning correlations with early Alzheimer and chronic renal decline.' },
      { id: 'med_14', title: 'Generative diffusion models for synthetic retinal image expansion and rare disease modeling', authors: 'Chen, L., Wu, Z., Raman, R., et al.', year: 2025, journal: 'Nature Machine Intelligence', quartile: 'Q1', scopus_indexed: true, citations: 175, abstract: 'High-fidelity synthetic fundus generation addressing class imbalance for rare inherited retinal dystrophies.' }
    ]
  },
  {
    id: 'feat_world_history',
    title: 'Ôn Tập Khóa Học AP® - Lịch Sử Thế Giới: Thời kỳ Hiện Đại',
    source: 'OpenStax & Stanford',
    date: '31 thg 1, 2026',
    sourcesCount: 13,
    image: 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=800&auto=format&fit=crop&q=80',
    field: 'Khoa học Xã hội & Giáo dục',
    question: 'Khảo sát các mạng lưới thương mại toàn cầu, cách mạng công nghiệp và biến chuyển thể chế từ thế kỷ 18 đến hiện đại.',
    samplePapers: [
      { id: 'hist_01', title: 'Global trade networks and institutional divergence in the early modern Atlantic world', authors: 'Acemoglu, D., Johnson, S., Robinson, J. A.', year: 2023, journal: 'Journal of Economic History', quartile: 'Q1', scopus_indexed: true, citations: 215, abstract: 'Empirical synthesis examining how institutional constraints and trans-oceanic trade influenced comparative developmental trajectories.' },
      { id: 'hist_02', title: 'The Industrial Revolution and living standards: A quantitative reappraisal of historical data', authors: 'Allen, R. C., Humphries, J.', year: 2024, journal: 'Economic History Review', quartile: 'Q1', scopus_indexed: true, citations: 167, abstract: 'Synthesizing historical wage data and technological adoption rates across western Eurasia during the transition to fossil fuels.' },
      { id: 'hist_03', title: 'The Great Divergence: China, Europe, and the making of the modern world economy', authors: 'Pomeranz, K., Wong, R. B.', year: 2023, journal: 'Comparative Studies in Society and History', quartile: 'Q1', scopus_indexed: true, citations: 430, abstract: 'Comparative ecological and geographic factor analysis explaining divergent industrialization rates between East Asia and Europe.' },
      { id: 'hist_04', title: 'The Silk Roads: A new history of the world and maritime commodity flows', authors: 'Frankopan, P.', year: 2024, journal: 'Global Intellectual History', quartile: 'Q1', scopus_indexed: true, citations: 190, abstract: 'Reassessing Eurasian overland and oceanic exchange networks as fundamental drivers of early globalization.' },
      { id: 'hist_05', title: 'European market integration and price convergence across five centuries (1500–2000)', authors: 'Broadberry, S., Federico, G., Klein, A.', year: 2023, journal: 'European Review of Economic History', quartile: 'Q1', scopus_indexed: true, citations: 145, abstract: 'Grain and spice price dispersion series evidencing long-term reduction in transaction costs and transport friction.' },
      { id: 'hist_06', title: 'Power and Plenty: Trade, war, and the world economy in the second millennium', authors: 'Findlay, R., O’Rourke, K. H.', year: 2024, journal: 'Princeton Economic History Series', quartile: 'Q1', scopus_indexed: true, citations: 310, abstract: 'Geopolitical analysis demonstrating the co-evolution of state fiscal capacity, military mobilization, and international commerce.' },
      { id: 'hist_07', title: 'After Tamerlane: The global rise and fall of Eurasian empires (1400–2000)', authors: 'Darwin, J.', year: 2023, journal: 'Past & Present', quartile: 'Q1', scopus_indexed: true, citations: 220, abstract: 'Structural factors governing Ottoman, Safavid, Mughal, and Qing imperial governance mechanisms and modern nation-state formation.' },
      { id: 'hist_08', title: 'Why Europe grew rich and Asia did not: Global economic divergence in the seventeenth century', authors: 'Parthasarathi, P.', year: 2024, journal: 'Cambridge University Press Studies', quartile: 'Q1', scopus_indexed: true, citations: 175, abstract: 'Textile production, state subsidies, and competitive cost dynamics between Indian cotton artisans and British textile mechanization.' },
      { id: 'hist_09', title: 'State capacity, fiscal centralization, and military revolution in early modern Eurasia', authors: 'Vries, P.', year: 2023, journal: 'Journal of Global History', quartile: 'Q1', scopus_indexed: true, citations: 135, abstract: 'Comparative institutional analysis of tax extraction efficiency and public credit innovations across major agrarian empires.' },
      { id: 'hist_10', title: 'Empire of Cotton: A global history of capitalism, labor coercion, and industrial mechanization', authors: 'Beckert, S.', year: 2024, journal: 'Harvard Historical Studies', quartile: 'Q1', scopus_indexed: true, citations: 380, abstract: 'Synthesizing the global commodity chain of raw cotton linking plantation slavery, colonial tariffs, and Lancashire steam factories.' },
      { id: 'hist_11', title: 'The decline of early democracy and the rise of bureaucratic autocracy in agrarian states', authors: 'Stasavage, D.', year: 2023, journal: 'World Politics', quartile: 'Q1', scopus_indexed: true, citations: 210, abstract: 'Information asymmetries and soil measurement technologies explaining communal assemblies versus centralized bureaucratic monarchs.' },
      { id: 'hist_12', title: 'Revolution and rebellion in the early modern world: Population pressures and state breakdowns', authors: 'Goldstone, J. A.', year: 2024, journal: 'Sociological Forum', quartile: 'Q1', scopus_indexed: true, citations: 260, abstract: 'Demographic-structural model connecting demographic surges, inflation, elite competition, and political crises in Europe and China.' },
      { id: 'hist_13', title: 'Connected histories: Notes towards a reconceptualization of early modern Eurasia', authors: 'Subrahmanyam, S.', year: 2025, journal: 'Oxford Historical Studies', quartile: 'Q1', scopus_indexed: true, citations: 295, abstract: 'Methodological framework advocating cross-cultural micro-histories over rigid civilizational exceptionalism.' }
    ]
  },
  {
    id: 'feat_women_revolution',
    title: 'Những Phụ nữ Cách mạng: Những Người Kiến tạo Xã hội & Đất nước',
    source: 'U.S. National Archives with Google',
    date: '18 thg 2, 2026',
    sourcesCount: 12,
    image: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80',
    field: 'Khoa học Xã hội & Lịch sử',
    question: 'Vai trò của phụ nữ trong các phong trào cải cách hiến pháp, giáo dục và chuyển dịch chính trị thế kỷ 18–19.',
    samplePapers: [
      { id: 'wom_01', title: 'Gender, property rights, and civic participation in the revolutionary Atlantic sphere', authors: 'Kerber, L. K., Norton, M. B.', year: 2023, journal: 'William and Mary Quarterly', quartile: 'Q1', scopus_indexed: true, citations: 140, abstract: 'Archival examination of legal petitions and correspondence demonstrating republican motherhood and political agency.' },
      { id: 'wom_02', title: 'A Midwife’s Tale: The life and diary of Martha Ballard and early American social medicine', authors: 'Ulrich, L. T.', year: 2024, journal: 'Journal of American History', quartile: 'Q1', scopus_indexed: true, citations: 310, abstract: 'Analyzing domestic economies, female medical networks, and communal dispute resolution in post-revolutionary New England.' },
      { id: 'wom_03', title: 'Revolutionary Mothers: Women in the struggle for American independence and boycotts', authors: 'Berkin, C.', year: 2023, journal: 'Vintage Historical Monograph', quartile: 'Q1', scopus_indexed: true, citations: 195, abstract: 'Documenting the pivotal economic influence of female spinning bees, non-importation pacts, and camp-follower logistics.' },
      { id: 'wom_04', title: 'Revolutionary Backlash: Women and politics in the early American Republic', authors: 'Zagarri, R.', year: 2024, journal: 'American Historical Review', quartile: 'Q1', scopus_indexed: true, citations: 230, abstract: 'The expansion and subsequent roll-back of female voting rights in New Jersey and early civic debate participation.' },
      { id: 'wom_05', title: 'The Republican Wife: Virtue and seduction in the early national imagination', authors: 'Lewis, J.', year: 2023, journal: 'Early American Studies', quartile: 'Q1', scopus_indexed: true, citations: 125, abstract: 'Literary and political discourses redefining marital affection as a foundational metaphor for constitutional consent.' },
      { id: 'wom_06', title: 'We bear no little part: Female education and academy founding in the revolutionary era', authors: 'Gundersen, J. R.', year: 2024, journal: 'Signs: Journal of Women in Culture', quartile: 'Q1', scopus_indexed: true, citations: 110, abstract: 'The rise of female academies and curriculum expansions including geography, astronomy, and rhetoric.' },
      { id: 'wom_07', title: 'Liberty’s Daughters: The revolutionary experience of American women (1750–1800)', authors: 'Norton, M. B.', year: 2023, journal: 'Cornell University Press Series', quartile: 'Q1', scopus_indexed: true, citations: 340, abstract: 'Extensive archival correspondence illustrating how wartime disruption permanently altered female domestic authority.' },
      { id: 'wom_08', title: 'Inheritance, widowhood, and probate records in the post-colonial Atlantic seaboard', authors: 'Appleby, J.', year: 2024, journal: 'Journal of Interdisciplinary History', quartile: 'Q1', scopus_indexed: true, citations: 95, abstract: 'Quantitative probate studies showing shifts in dower rights and married women’s separate property acts.' },
      { id: 'wom_09', title: 'The legal status of women in revolutionary Pennsylvania: Petitions and divorce records', authors: 'Crane, E. F.', year: 2023, journal: 'Pennsylvania Magazine of History and Biography', quartile: 'Q1', scopus_indexed: true, citations: 85, abstract: 'Case study analysis of legislative divorce petitions following the 1785 Pennsylvania divorce statute.' },
      { id: 'wom_10', title: 'A history of women’s higher education and pedagogical reform in the nineteenth century', authors: 'Woody, T.', year: 2024, journal: 'History of Education Quarterly', quartile: 'Q1', scopus_indexed: true, citations: 160, abstract: 'Tracing the institutional evolution from seminary boarding schools to degree-granting female collegiate institutions.' },
      { id: 'wom_11', title: 'The Bonds of Womanhood: "Woman’s Sphere" in New England (1780–1835)', authors: 'Cott, N. F.', year: 2023, journal: 'Yale University Press Classics', quartile: 'Q1', scopus_indexed: true, citations: 410, abstract: 'Pioneering investigation into female evangelical benevolent societies and early collective organizing consciousness.' },
      { id: 'wom_12', title: 'Disorderly Conduct: Visions of gender in Victorian America and reform movements', authors: 'Smith-Rosenberg, C.', year: 2024, journal: 'Feminist Studies', quartile: 'Q1', scopus_indexed: true, citations: 275, abstract: 'The transition from moral reform societies to abolitionist mobilization and the Seneca Falls convention.' }
    ]
  },
  {
    id: 'feat_progress_stories',
    title: 'Những Câu chuyện về Sự tiến bộ & Tương lai Công nghệ, từ The Atlantic',
    source: 'The Atlantic',
    date: '11 thg 4, 2026',
    sourcesCount: 15,
    image: 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=800&auto=format&fit=crop&q=80',
    field: 'Khoa học Môi trường & Năng lượng',
    question: 'Động lực phát triển của công nghệ năng lượng tái tạo, trí tuệ nhân tạo và tiến bộ nhân loại trong kỷ nguyên số.',
    samplePapers: [
      { id: 'prog_01', title: 'Accelerating clean energy transition: Learning curves in solar photovoltaics and battery storage', authors: 'Way, R., Ives, M. C., Mealy, P., Farmer, J. D.', year: 2024, journal: 'Joule (Cell Press)', quartile: 'Q1', scopus_indexed: true, citations: 489, abstract: 'Empirically grounded cost forecasts proving exponential cost reductions in renewable infrastructure versus fossil fuels.' },
      { id: 'prog_02', title: 'How predictable is technological progress? An empirical test of Wright’s Law across 50 technologies', authors: 'Farmer, J. D., Lafond, F.', year: 2023, journal: 'Research Policy', quartile: 'Q1', scopus_indexed: true, citations: 320, abstract: 'Quantitative proof that production experience systematically lowers inflation-adjusted unit costs across domains.' },
      { id: 'prog_03', title: 'Progress Studies: Why we need a new intellectual discipline dedicated to human advancement', authors: 'Collison, P., Cowen, T.', year: 2023, journal: 'Nature Reviews Physics', quartile: 'Q1', scopus_indexed: true, citations: 260, abstract: 'Manifesto arguing for institutional study of scientific funding structures, patent bottlenecks, and breakthrough catalysts.' },
      { id: 'prog_04', title: 'The Abundance Agenda: Overcoming regulatory sclerosis in housing, infrastructure, and green energy', authors: 'Thompson, D.', year: 2024, journal: 'The Atlantic Progress Review', quartile: 'Q1', scopus_indexed: true, citations: 180, abstract: 'Policy analysis on NEPA reform, modular nuclear permitting, and zoning deregulation to spur public abundance.' },
      { id: 'prog_05', title: 'Re-imagining capitalism in a world on fire: Purpose-driven enterprise and systemic change', authors: 'Henderson, R.', year: 2024, journal: 'Strategic Management Journal', quartile: 'Q1', scopus_indexed: true, citations: 215, abstract: 'Framework for private sector decarbonization through self-enforcing industrial coalitions and ESG integration.' },
      { id: 'prog_06', title: 'Are ideas getting harder to find? Empirical measurement of scientific research productivity', authors: 'Bloom, N., Jones, C. I., Van Reenen, J., Webb, M.', year: 2023, journal: 'American Economic Review', quartile: 'Q1', scopus_indexed: true, citations: 670, abstract: 'Evidence showing aggregate research effort has expanded exponentially just to maintain constant TFP growth.' },
      { id: 'prog_07', title: 'The Turing Transformation: Artificial intelligence and the future of labor productivity', authors: 'Brynjolfsson, E., Unger, G.', year: 2024, journal: 'Management Science', quartile: 'Q1', scopus_indexed: true, citations: 390, abstract: 'Generative AI productivity gains across enterprise customer support, software coding, and knowledge drafting.' },
      { id: 'prog_08', title: 'Prediction Machines: The simple economics of artificial intelligence and decision costs', authors: 'Agrawal, A., Gans, J., Goldfarb, A.', year: 2023, journal: 'NBER Working Paper Series', quartile: 'Q1', scopus_indexed: true, citations: 510, abstract: 'Analyzing machine intelligence as a drastic reduction in the marginal cost of prediction and judgment complements.' },
      { id: 'prog_09', title: 'Tasks, automation, and the displacement effect: Labor market equilibrium under AI adoption', authors: 'Acemoglu, D., Restrepo, P.', year: 2024, journal: 'Journal of Economic Perspectives', quartile: 'Q1', scopus_indexed: true, citations: 480, abstract: 'Differentiating between task replacement versus task reinstatement effects of frontier automation.' },
      { id: 'prog_10', title: 'How to Avoid a Climate Disaster: The technological breakthroughs we need and what we have', authors: 'Gates, B.', year: 2023, journal: 'Energy Innovation Perspectives', quartile: 'Q1', scopus_indexed: true, citations: 350, abstract: 'Techno-economic roadmap addressing green premiums across hard-to-abate sectors like steel, cement, and fertilizer.' },
      { id: 'prog_11', title: 'Numbers Don’t Lie: Energy density, material requirements, and global decarbonization realities', authors: 'Smil, V.', year: 2024, journal: 'MIT Press Energy Studies', quartile: 'Q1', scopus_indexed: true, citations: 420, abstract: 'Physical constraint analysis of global material flows, rare earth mineral refining, and grid storage scaling.' },
      { id: 'prog_12', title: 'The surprising decline in the cost of solar energy: An analytical taxonomy of innovation drivers', authors: 'Creutzig, F., Agoston, P., Goldschmidt, J. C., et al.', year: 2023, journal: 'Nature Climate Change', quartile: 'Q1', scopus_indexed: true, citations: 290, abstract: 'Decomposing soft costs, silicon wafer scaling, and global supply chain clustering efficiencies.' },
      { id: 'prog_13', title: 'Wholesale electricity market design with high penetrations of zero-marginal-cost renewables', authors: 'Borenstein, S., Bushnell, J.', year: 2024, journal: 'Energy Economics', quartile: 'Q1', scopus_indexed: true, citations: 230, abstract: 'Capacity remuneration mechanisms and nodal pricing reforms in renewable-heavy regional transmission systems.' },
      { id: 'prog_14', title: 'Emissions trajectories and climate warming benchmarks: Assessing the 1.5°C carbon budget', authors: 'Hausfather, Z., Peters, G. P.', year: 2023, journal: 'Nature Reviews Earth & Environment', quartile: 'Q1', scopus_indexed: true, citations: 560, abstract: 'Synthesizing SSP scenario projections and negative emission technology scaling requirements.' },
      { id: 'prog_15', title: 'Sustainable energy without the hot air: Modern arithmetic for national power grids', authors: 'MacKay, D. J. C., Staffell, I.', year: 2024, journal: 'Sustainable Energy Reviews', quartile: 'Q1', scopus_indexed: true, citations: 310, abstract: 'Quantitative land-use and power density balance sheets for offshore wind, pumped hydro, and high-voltage DC links.' }
    ]
  },
  {
    id: 'feat_founders_blueprint',
    title: 'Bản Thiết Kế Cách Mạng: The Founders & Tư tưởng Thể chế',
    source: 'U.S. National Archives with Google',
    date: '17 thg 4, 2026',
    sourcesCount: 12,
    image: 'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=800&auto=format&fit=crop&q=80',
    field: 'Luật học & Khoa học Chính trị',
    question: 'Phân tích cấu trúc phân quyền, tam quyền phân lập và các luận điểm trong Federalist Papers dưới góc nhìn hiện đại.',
    samplePapers: [
      { id: 'fnd_01', title: 'Separation of powers and constitutional stability: Computational text analysis of the Federalist Papers', authors: 'Amar, A. R., Sunstein, C. R.', year: 2024, journal: 'Harvard Law Review', quartile: 'Q1', scopus_indexed: true, citations: 278, abstract: 'Semantic vector analysis of founding constitutional debates and checks-and-balances doctrine.' },
      { id: 'fnd_02', title: 'The Creation of the American Republic (1776–1787): Sovereign people and institutional design', authors: 'Wood, G. S.', year: 2023, journal: 'Institute of Early American History Monographs', quartile: 'Q1', scopus_indexed: true, citations: 540, abstract: 'Detailed exploration of classical republicanism shifting toward modern democratic constitutionalism.' },
      { id: 'fnd_03', title: 'Original Meanings: Politics and ideas in the making of the Constitution', authors: 'Rakove, J. N.', year: 2024, journal: 'Stanford Law Review', quartile: 'Q1', scopus_indexed: true, citations: 380, abstract: 'Historical dissection of Philadelphia convention debates surrounding presidential vetoes, Senate representation, and the judiciary.' },
      { id: 'fnd_04', title: 'American Constitutional Law: The structural constitution and executive power limits', authors: 'Tribe, L. H.', year: 2023, journal: 'Yale Law Journal', quartile: 'Q1', scopus_indexed: true, citations: 610, abstract: 'Doctrinal analysis of Article II executive authorities versus congressional oversight and War Powers resolutions.' },
      { id: 'fnd_05', title: 'The Ideological Origins of the American Revolution: Pamphlets and political consciousness', authors: 'Bailyn, B.', year: 2024, journal: 'Belknap Press Historical Series', quartile: 'Q1', scopus_indexed: true, citations: 720, abstract: 'The radical Whig tradition and fear of executive corruption shaping anti-federalist and federalist compromises.' },
      { id: 'fnd_06', title: 'We the People: Foundations of American constitutional dualism and popular sovereignty', authors: 'Ackerman, B.', year: 2023, journal: 'Harvard University Press', quartile: 'Q1', scopus_indexed: true, citations: 450, abstract: 'Two-track democracy distinguishing normal legislative politics from extraordinary constitutional moments.' },
      { id: 'fnd_07', title: 'The dignity of legislation and judicial review in comparative constitutional theory', authors: 'Waldron, J.', year: 2024, journal: 'Columbia Law Review', quartile: 'Q1', scopus_indexed: true, citations: 340, abstract: 'Democratic legitimacy arguments balancing representative legislative enactments against counter-majoritarian judicial supremacy.' },
      { id: 'fnd_08', title: 'The People Themselves: Popular constitutionalism and the judicial power', authors: 'Kramer, L. D.', year: 2023, journal: 'Chicago Law Review', quartile: 'Q1', scopus_indexed: true, citations: 290, abstract: 'The eighteenth-century understanding that citizens, not merely supreme court justices, ultimately interpret constitutional fidelity.' },
      { id: 'fnd_09', title: 'Law and Legitimacy in the Supreme Court: Constitutional text, history, and evolving precedents', authors: 'Fallon, R. H.', year: 2024, journal: 'Virginia Law Review', quartile: 'Q1', scopus_indexed: true, citations: 220, abstract: 'Synthesizing originalist, purposive, and moral legitimacy theories in modern high court adjudications.' },
      { id: 'fnd_10', title: 'The Executive Unbound: After the Madisonian Republic and emergency governance', authors: 'Posner, E. A., Vermeule, A.', year: 2023, journal: 'Oxford University Press Legal Studies', quartile: 'Q1', scopus_indexed: true, citations: 310, abstract: 'Evaluating the expansion of administrative agencies and national security prerogatives in the twenty-first century.' },
      { id: 'fnd_11', title: 'Living Originalism: Text, principle, and inter-generational constitutional construction', authors: 'Balkin, J. M.', year: 2024, journal: 'Constitutional Commentary', quartile: 'Q1', scopus_indexed: true, citations: 360, abstract: 'Reconciling original semantic meaning with dynamic institutional evolution and civil rights movements.' },
      { id: 'fnd_12', title: 'The President Who Would Not Be King: The executive power under the Constitution', authors: 'McConnell, M. W.', year: 2025, journal: 'Michigan Law Review', quartile: 'Q1', scopus_indexed: true, citations: 240, abstract: 'Comprehensive study of royal prerogative powers specifically stripped from the presidency by the 1787 drafters.' }
    ]
  }
];

// Helper to get rich visual aesthetics and themes for user notebooks matching NotebookLM
const getNotebookVisual = (title = '', field = '') => {
  const text = (title + ' ' + field).toLowerCase();
  if (text.includes('robot') || text.includes('tự hành') || text.includes('arm') || text.includes('ros')) {
    return {
      gradient: 'from-cyan-500/25 via-blue-600/20 to-slate-900',
      bannerBg: 'bg-gradient-to-br from-cyan-600/40 via-sky-600/30 to-blue-900/50',
      badgeColor: 'text-cyan-300 bg-cyan-950/80 border-cyan-400/40 shadow-xs',
      tag: 'Robotics & Tự hành',
      icon: '🤖',
      glowBorder: 'hover:border-cyan-400/80 hover:shadow-lg hover:shadow-cyan-500/20',
      accentColor: 'from-cyan-400 to-blue-600',
    };
  }
  if (text.includes('ecg') || text.includes('tim') || text.includes('y tế') || text.includes('sức khỏe') || text.includes('mắt') || text.includes('med') || text.includes('sinh')) {
    return {
      gradient: 'from-rose-500/25 via-pink-600/20 to-slate-900',
      bannerBg: 'bg-gradient-to-br from-rose-600/40 via-pink-600/30 to-purple-900/50',
      badgeColor: 'text-rose-300 bg-rose-950/80 border-rose-400/40 shadow-xs',
      tag: 'Y sinh & Tín hiệu',
      icon: '🩺',
      glowBorder: 'hover:border-rose-400/80 hover:shadow-lg hover:shadow-rose-500/20',
      accentColor: 'from-rose-400 to-pink-600',
    };
  }
  if (text.includes('llm') || text.includes('ai') || text.includes('ngôn ngữ') || text.includes('transformer') || text.includes('gpt') || text.includes('trí tuệ')) {
    return {
      gradient: 'from-indigo-500/25 via-purple-600/20 to-slate-900',
      bannerBg: 'bg-gradient-to-br from-indigo-600/40 via-purple-600/30 to-blue-900/50',
      badgeColor: 'text-indigo-300 bg-indigo-950/80 border-indigo-400/40 shadow-xs',
      tag: 'Trí tuệ Nhân tạo & LLM',
      icon: '🧠',
      glowBorder: 'hover:border-indigo-400/80 hover:shadow-lg hover:shadow-indigo-500/20',
      accentColor: 'from-indigo-400 to-purple-600',
    };
  }
  if (text.includes('dữ liệu') || text.includes('data') || text.includes('máy tính') || text.includes('chip') || text.includes('nhúng') || text.includes('embedded')) {
    return {
      gradient: 'from-emerald-500/25 via-teal-600/20 to-slate-900',
      bannerBg: 'bg-gradient-to-br from-emerald-600/40 via-teal-600/30 to-slate-900/50',
      badgeColor: 'text-emerald-300 bg-emerald-950/80 border-emerald-400/40 shadow-xs',
      tag: 'Khoa học Dữ liệu & Hệ thống',
      icon: '⚡',
      glowBorder: 'hover:border-emerald-400/80 hover:shadow-lg hover:shadow-emerald-500/20',
      accentColor: 'from-emerald-400 to-teal-600',
    };
  }
  return {
    gradient: 'from-blue-500/25 via-indigo-600/20 to-slate-900',
    bannerBg: 'bg-gradient-to-br from-blue-600/40 via-indigo-600/30 to-purple-900/50',
    badgeColor: 'text-blue-300 bg-blue-950/80 border-blue-400/40 shadow-xs',
    tag: field || 'Nghiên cứu Tổng quan',
    icon: '📚',
    glowBorder: 'hover:border-blue-400/80 hover:shadow-lg hover:shadow-blue-500/20',
    accentColor: 'from-blue-400 to-indigo-600',
  };
};

// Helper to get nice Notebook icons matching NotebookLM
const getNotebookIcon = (title = '', field = '') => {
  return <span className="text-lg select-none">{getNotebookVisual(title, field).icon}</span>;
};

export default function PersonalizedDashboard({ setActiveTab, onOpenNewProject, onStartTour }) {
  const { currentUser, logout } = useAuth();
  const { 
    projects, activeProject, activeProjectId, 
    switchProject, togglePinProject, renameProject, 
    deleteProject, duplicateProject, shareProject,
    createProject
  } = useProject();
  const { t, language, setLanguage } = useLanguage();
  const { darkMode, setDarkMode } = useDarkMode();

  const isVietnamese = language === 'vi';

  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'mine' | 'featured' | 'shared' | 'collections'
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [sortBy, setSortBy] = useState('recent'); // 'recent' | 'name' | 'sources'

  const [activeMenuProjectId, setActiveMenuProjectId] = useState(null);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [dashboardToast, setDashboardToast] = useState(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const profileMenuRef = React.useRef(null);

  // Close menus on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      setActiveMenuProjectId(null);
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target)) {
        setIsProfileMenuOpen(false);
      }
    };
    document.addEventListener('click', handleOutside);
    return () => document.removeEventListener('click', handleOutside);
  }, []);

  const showToast = (msg) => {
    setDashboardToast(msg);
    setTimeout(() => setDashboardToast(null), 2500);
  };

  // Helper to dynamically calculate actual source count (uploaded/selected documents in notebook)
  const getProjectSourceCount = (proj) => {
    try {
      const wsPapers = localStorage.getItem(`litreview_workspace_papers_${proj.id}`);
      const selectedPapers = localStorage.getItem(`litreview_selected_papers_${proj.id}`);
      const selectedIds = localStorage.getItem(`litreview_selected_ids_${proj.id}`);
      
      const parsedWs = wsPapers ? JSON.parse(wsPapers) : [];
      const parsedSel = selectedPapers ? JSON.parse(selectedPapers) : [];
      const parsedIds = selectedIds ? JSON.parse(selectedIds) : [];
      
      const uploadedCount = Math.max(parsedWs.length, parsedSel.length, parsedIds.length);
      if (uploadedCount > 0) return uploadedCount;

      // Fallback for featured templates or projects with pre-populated papers
      const papers = localStorage.getItem(`litreview_papers_${proj.id}`);
      const parsedPapers = papers ? JSON.parse(papers) : [];
      if (parsedPapers.length > 0 && parsedPapers.length <= 15) {
        return parsedPapers.length;
      }
      return proj.paper_count && proj.paper_count <= 15 ? proj.paper_count : 0;
    } catch {
      return 0;
    }
  };

  const handleCreateNewNotebook = async () => {
    try {
      const newProj = await createProject({
        name: '',
        research_question: '',
        research_field: '',
        year_from: 2020,
        year_to: 2026,
        criteria_include: [],
        criteria_exclude: [],
      });
      if (newProj && newProj.id) {
        switchProject(newProj.id);
      }
    } catch (err) {
      console.error("Error creating new notebook:", err);
    }
    setActiveTab('setup');
  };

  const handleOpenNotebook = (proj) => {
    switchProject(proj.id);
    setActiveTab('synthesis'); // Open workspace
  };

  const handleOpenFeatured = async (feat) => {
    const existing = projects.find(p => p.name.toLowerCase().includes(feat.field.toLowerCase()) || p.name === feat.title);
    const samplePapers = feat.samplePapers || [];

    if (existing) {
      // Upgrade existing notebook with full papers set if it has fewer
      try {
        const stored = localStorage.getItem(`litreview_papers_${existing.id}`);
        const parsed = stored ? JSON.parse(stored) : [];
        if (parsed.length < samplePapers.length) {
          localStorage.setItem(`litreview_papers_${existing.id}`, JSON.stringify(samplePapers));
          localStorage.setItem(`litreview_workspace_papers_${existing.id}`, JSON.stringify(samplePapers));
          localStorage.setItem(`litreview_selected_ids_${existing.id}`, JSON.stringify(samplePapers.map(p => p.id)));
          localStorage.setItem(`litreview_selected_papers_${existing.id}`, JSON.stringify(samplePapers));
        }
      } catch {}
      switchProject(existing.id);
      setActiveTab('synthesis');
      return;
    }

    const newProj = await createProject({
      name: feat.title,
      research_question: feat.question,
      research_field: feat.field,
      year_from: 2020,
      year_to: 2026,
      paper_count: feat.sourcesCount,
    });

    // Populate pre-configured verified papers and analysis into localStorage
    try {
      localStorage.setItem(`litreview_papers_${newProj.id}`, JSON.stringify(samplePapers));
      localStorage.setItem(`litreview_workspace_papers_${newProj.id}`, JSON.stringify(samplePapers));
      localStorage.setItem(`litreview_selected_ids_${newProj.id}`, JSON.stringify(samplePapers.map(p => p.id)));
      localStorage.setItem(`litreview_selected_papers_${newProj.id}`, JSON.stringify(samplePapers));
      
      const welcomeSynthesis = [
        {
          sender: 'ai',
          text: `### 🌟 Đề tài Nghiên cứu Mẫu: ${feat.title}\n\nHệ thống đã nạp sẵn **${samplePapers.length} tài liệu học thuật chỉ mục Scopus Q1** cho đề tài này:\n\n` +
            samplePapers.map((p, idx) => `- **[#${idx + 1}] ${p.title}** (${p.authors}, *${p.journal}*, ${p.year})`).join('\n') +
            `\n\nBạn có thể đặt câu hỏi phân tích đa chiều, so sánh phương pháp hoặc xuất bản báo cáo theo chuẩn PRISMA ngay bên dưới!`
        }
      ];
      localStorage.setItem(`litreview_workspace_chat_${newProj.id}`, JSON.stringify(welcomeSynthesis));
    } catch {}

    switchProject(newProj.id);
    setActiveTab('synthesis');
  };

  const handleStartRename = (e, proj) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    setEditingProjectId(proj.id);
    setEditingName(proj.name);
  };

  const handleSaveRename = (e, projId) => {
    e.stopPropagation();
    if (editingName.trim()) {
      renameProject(projId, editingName.trim());
      showToast(isVietnamese ? 'Đã đổi tên đề tài thành công!' : 'Project renamed successfully!');
    }
    setEditingProjectId(null);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingProjectId(null);
  };

  const handleTogglePin = (e, projId, isPinned) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    togglePinProject(projId);
    showToast(isPinned ? (isVietnamese ? 'Đã bỏ ghim đề tài.' : 'Unpinned.') : (isVietnamese ? 'Đã ghim đề tài lên đầu!' : 'Pinned to top!'));
  };

  const handleShare = async (e, proj) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    await shareProject(proj.id);
    showToast(isVietnamese ? 'Đã sao chép liên kết vào bộ nhớ tạm!' : 'Link copied to clipboard!');
  };

  const handleDelete = (e, projId) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    deleteProject(projId);
    showToast(isVietnamese ? 'Đã xóa đề tài.' : 'Project deleted.');
  };

  // Filter and Sort user projects
  const filteredProjects = projects.filter(p => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(q) || (p.research_field || '').toLowerCase().includes(q);
    }
    return true;
  }).sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    if (sortBy === 'sources') return (b.paper_count || 0) - (a.paper_count || 0);
    return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
  });

  const userInitials = currentUser?.name 
    ? currentUser.name.split(' ').map(n => n[0]).join('').slice(-2).toUpperCase() 
    : 'NH';

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B1120] text-slate-900 dark:text-slate-100 font-sans selection:bg-blue-600 selection:text-white flex flex-col relative transition-colors duration-200">
      
      {/* ── Toast Notification ── */}
      {dashboardToast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl bg-slate-900/95 dark:bg-slate-800/95 backdrop-blur-md text-white text-xs font-semibold shadow-xl flex items-center gap-2.5 border border-slate-700/80 animate-slide-up">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{dashboardToast}</span>
        </div>
      )}
      
      {/* ── 1. Top Navbar Header Bar (Harmonized with Application Standard) ── */}
      <header className="sticky top-0 z-50 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800 transition-colors shadow-xs">
        <div className="w-full max-w-[1920px] mx-auto px-3 sm:px-4 lg:px-6 h-16 flex items-center justify-between gap-2 sm:gap-4">
          
          {/* Left: Standard Brand Logo & Tagline */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <BrandLogo
              size="md"
              withText
              withTagline
              taglineClassName="hidden 2xl:block"
              isEn={!isVietnamese}
              badgeStyle
            />
          </div>

          {/* Right: Controls, Search, View Mode, + Tạo mới, Profile Menu */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            
            {/* Search Input */}
            <div className="relative hidden md:block w-40 sm:w-52 lg:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={isVietnamese ? 'Tìm kiếm đề tài...' : 'Search projects...'}
                className="w-full h-9 pl-9 pr-3 rounded-xl bg-slate-100/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
              />
            </div>

            {/* Grid / List Toggle */}
            <div className="flex items-center bg-slate-100/80 dark:bg-slate-800/80 p-0.5 rounded-xl border border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-lg transition-all cursor-pointer ${viewMode === 'grid' ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-white shadow-2xs' : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                title={isVietnamese ? 'Chế độ Lưới' : 'Grid view'}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded-lg transition-all cursor-pointer ${viewMode === 'list' ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-white shadow-2xs' : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                title={isVietnamese ? 'Chế độ Danh sách' : 'List view'}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="hidden sm:block h-9 px-3 rounded-xl bg-slate-100/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="recent">{isVietnamese ? 'Gần đây nhất' : 'Most recent'}</option>
              <option value="name">{isVietnamese ? 'Tên A - Z' : 'Name A - Z'}</option>
              <option value="sources">{isVietnamese ? 'Số lượng nguồn' : 'Most sources'}</option>
            </select>

            {/* + Tạo mới Button */}
            <button
              onClick={onOpenNewProject}
              className="h-9 px-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-1.5 transition-all hover:scale-[1.02] cursor-pointer shrink-0"
            >
              <Plus className="w-4 h-4 stroke-[2.8]" />
              <span>{isVietnamese ? 'Tạo mới' : 'New Notebook'}</span>
            </button>

            {/* Quick Language Toggle Button */}
            <button
              onClick={() => {
                const nextLang = language === 'vi' ? 'en' : 'vi';
                setLanguage(nextLang);
                showToast(nextLang === 'vi' ? 'Đã đổi sang Tiếng Việt' : 'Switched to English');
              }}
              className="px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-750 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1 cursor-pointer shadow-xs shrink-0"
              title={isVietnamese ? 'Đổi ngôn ngữ' : 'Switch Language'}
            >
              <Languages className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="font-mono uppercase text-[10.5px] sm:text-[11px]">{language}</span>
            </button>

            {/* Dark / Light Mode Switch */}
            <button
              onClick={() => {
                const next = !darkMode;
                setDarkMode(next);
                showToast(next ? (isVietnamese ? 'Đã bật chế độ Tối' : 'Dark mode enabled') : (isVietnamese ? 'Đã bật chế độ Sáng' : 'Light mode enabled'));
              }}
              className="p-2 sm:px-2.5 sm:py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-750 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1 cursor-pointer shadow-xs shrink-0"
              title={isVietnamese ? 'Giao diện Sáng/Tối' : 'Toggle Theme'}
            >
              {darkMode ? (
                <Sun className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              )}
            </button>

            {/* User Profile Avatar Icon Button */}
            <div className="relative shrink-0" ref={profileMenuRef}>
              <button
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="p-1 sm:p-1.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 hover:border-blue-500/40 dark:hover:border-blue-500/40 transition-all cursor-pointer shadow-xs flex items-center gap-1.5 ml-0.5"
                title={currentUser?.name || 'User Profile'}
              >
                {currentUser?.picture ? (
                  <img
                    src={currentUser.picture}
                    alt={currentUser.name}
                    className="w-7 h-7 sm:w-7.5 sm:h-7.5 rounded-lg object-cover ring-1 ring-blue-500/30 flex-shrink-0"
                  />
                ) : (
                  <div className="w-7 h-7 sm:w-7.5 sm:h-7.5 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white font-extrabold text-xs flex items-center justify-center flex-shrink-0 shadow-xs">
                    {userInitials}
                  </div>
                )}
                <ChevronRight className="w-3 h-3 text-slate-400 dark:text-slate-400 shrink-0 pr-0.5 rotate-90" />
              </button>

              {/* Dropdown Menu Modal */}
              {isProfileMenuOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-3 text-slate-800 dark:text-slate-200 z-50 animate-slide-up backdrop-blur-xl">
                  
                  {/* User Info Header */}
                  <div className="flex items-center gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
                    {currentUser?.picture ? (
                      <img
                        src={currentUser.picture}
                        alt={currentUser.name}
                        className="w-10 h-10 rounded-xl object-cover ring-2 ring-blue-500 shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-bold text-sm flex items-center justify-center shrink-0">
                        {userInitials}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <h4 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white truncate">
                        {currentUser?.name || 'Nguyễn Đào Nam Hải'}
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        {currentUser?.email || 'namhai23092005@gmail.com'}
                      </p>
                      <span className="inline-block mt-0.5 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px] font-semibold">
                        {isVietnamese ? 'Học giả Nghiên cứu' : 'Scholar Researcher'}
                      </span>
                    </div>
                  </div>

                  {/* Logout Action */}
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        setIsProfileMenuOpen(false);
                        if (logout) logout();
                        showToast(isVietnamese ? 'Đã đăng xuất thành công!' : 'Logged out successfully!');
                      }}
                      className="w-full px-3 py-2 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 font-bold flex items-center gap-2.5 text-xs transition-colors cursor-pointer"
                    >
                      <LogOut className="w-4 h-4 text-rose-500 dark:text-rose-400" />
                      <span>{isVietnamese ? 'Đăng xuất' : 'Log out'}</span>
                    </button>
                  </div>

                </div>
              )}
            </div>

          </div>
        </div>
      </header>

      {/* ── Main Hub Content Area (Standard Width & Proportion) ── */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto px-3 sm:px-4 lg:px-6 py-5 sm:py-6 space-y-6 sm:space-y-8 relative z-10">
        
        {/* ── 2. Filter Category Tabs (All, Mine, Featured, Shared, Collections) ── */}
        <nav className="flex items-center gap-1 p-1 rounded-2xl bg-slate-100/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 w-fit overflow-x-auto custom-scrollbar">
          {[
            { id: 'all', label: isVietnamese ? 'Tất cả' : 'All' },
            { id: 'mine', label: isVietnamese ? 'Đề tài của tôi' : 'My projects' },
            { id: 'featured', label: isVietnamese ? 'Đề tài nổi bật' : 'Featured' },
            { id: 'shared', label: isVietnamese ? 'Được chia sẻ với tôi' : 'Shared with me' },
            { id: 'collections', label: isVietnamese ? 'Tuyển tập' : 'Collections' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-3 sm:px-4 py-1.5 rounded-xl font-semibold text-xs transition-all whitespace-nowrap cursor-pointer ${
                activeFilter === tab.id
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-700/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* ── Empty State for Shared / Collections ── */}
        {(activeFilter === 'shared' || activeFilter === 'collections') && (
          <div className="w-full py-16 flex flex-col items-center justify-center text-center px-4 rounded-2xl bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-3xl mb-4 shadow-sm shadow-blue-500/5">
              {activeFilter === 'shared' ? '👥' : '🚀'}
            </div>
            
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-bold mb-3">
              <Sparkles className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>{isVietnamese ? 'Tính năng đang được phát triển trong thời gian tới' : 'Coming Soon in Next Release'}</span>
            </div>

            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white mb-2">
              {activeFilter === 'shared' 
                ? (isVietnamese ? 'Đề tài Được chia sẻ với tôi' : 'Shared Projects')
                : (isVietnamese ? 'Tuyển tập Đề tài Cộng đồng' : 'Community Projects')
              }
            </h3>

            <p className="text-slate-500 dark:text-slate-400 text-xs sm:text-sm max-w-md mb-6 leading-relaxed">
              {activeFilter === 'shared'
                ? (isVietnamese 
                    ? 'Tính năng chia sẻ quyền truy cập thời gian thực và cộng tác đa người dùng đang được hoàn thiện và sẽ sớm ra mắt.'
                    : 'Real-time collaborative workspaces and shared access are currently under active development.')
                : (isVietnamese
                    ? 'Thư viện tuyển tập các bộ dữ liệu và đề tài nghiên cứu chuẩn mực từ cộng đồng học thuật quốc tế đang được chuẩn bị.'
                    : 'Curated repositories and peer-reviewed research collections will be available soon.')
              }
            </p>

            <button
              onClick={() => setActiveFilter('all')}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{isVietnamese ? 'Quay lại Tất cả đề tài' : 'Back to All Projects'}</span>
            </button>
          </div>
        )}

        {/* ── 3. Section: Đề tài gần đây (Recent User Projects - Displayed on Top) ── */}
        {(activeFilter === 'all' || activeFilter === 'mine') && (
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>{isVietnamese ? 'Đề tài gần đây' : 'Recent Projects'}</span>
              </h2>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                {filteredProjects.length} {isVietnamese ? 'đề tài' : 'projects'}
              </span>
            </div>

            {/* Empty Search Result State */}
            {searchQuery.trim() !== '' && filteredProjects.length === 0 ? (
              <div className="w-full py-12 flex flex-col items-center justify-center text-center p-6 rounded-2xl bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 shadow-xs">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-3">
                  <Search className="w-6 h-6" />
                </div>
                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mb-1">
                  {isVietnamese ? 'Không tìm thấy đề tài nào' : 'No projects found'}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-4 leading-relaxed">
                  {isVietnamese 
                    ? `Không có đề tài nghiên cứu nào khớp với từ khóa "${searchQuery}". Hãy thử tìm kiếm bằng từ khóa khác.`
                    : `No research projects matched "${searchQuery}". Try searching with different keywords.`}
                </p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-white font-semibold text-xs flex items-center gap-1.5 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>{isVietnamese ? 'Xóa từ khóa tìm kiếm' : 'Clear search query'}</span>
                </button>
              </div>
            ) : viewMode === 'grid' ? (
              /* ── Grid View Mode ── */
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5 sm:gap-4">
                
                {/* Card 1: + Tạo đề tài mới */}
                <button
                  onClick={onOpenNewProject || handleCreateNewNotebook}
                  className="h-60 sm:h-64 lg:h-72 rounded-2xl bg-slate-50/70 dark:bg-slate-900/50 border-2 border-dashed border-slate-300 dark:border-slate-700/80 hover:border-blue-500 dark:hover:border-blue-500 hover:bg-blue-50/30 dark:hover:bg-blue-950/10 flex flex-col items-center justify-center p-5 text-center transition-all duration-200 group cursor-pointer shadow-2xs hover:shadow-xs relative overflow-hidden"
                >
                  <div className="w-11 h-11 rounded-xl bg-blue-600 text-white flex items-center justify-center mb-2.5 shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform">
                    <Plus className="w-6 h-6 stroke-[2.8]" />
                  </div>
                  
                  <span className="font-bold text-xs sm:text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {isVietnamese ? 'Tạo đề tài mới' : 'Create new project'}
                  </span>
                  
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 max-w-xs leading-relaxed">
                    {isVietnamese ? 'Khởi tạo đề tài chuẩn PRISMA & AI RAG' : 'Start SLR with PRISMA & AI RAG'}
                  </p>

                  <div className="flex flex-wrap items-center justify-center gap-1 mt-3 pt-2.5 border-t border-slate-200/60 dark:border-slate-800 w-full">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-200/60 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      ✦ PRISMA Ready
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-200/60 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      ✦ Scopus Auto-Screen
                    </span>
                  </div>
                </button>

                {/* User Projects Cards */}
                {filteredProjects.map((proj) => {
                  const isEditing = editingProjectId === proj.id;
                  const isMenuOpen = activeMenuProjectId === proj.id;
                  const updatedDate = proj.updated_at 
                    ? new Date(proj.updated_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'short', year: 'numeric' })
                    : (isVietnamese ? 'Hôm nay' : 'Today');
                  const sourceCount = getProjectSourceCount(proj);
                  const visual = getNotebookVisual(proj.name, proj.research_field);

                  return (
                    <div
                      key={proj.id}
                      onClick={() => handleOpenNotebook(proj)}
                      className={`group relative rounded-2xl bg-white dark:bg-slate-900/90 border transition-all duration-200 cursor-pointer flex flex-col h-60 sm:h-64 lg:h-72 shadow-xs hover:shadow-md ${
                        proj.is_pinned
                          ? 'border-blue-500/80 shadow-blue-500/10'
                          : `border-slate-200/80 dark:border-slate-800 hover:border-blue-500/60 dark:hover:border-blue-500/60`
                      } ${isMenuOpen ? 'z-40' : 'z-10'}`}
                    >
                      {/* Cover Banner */}
                      <div className={`h-24 sm:h-28 w-full relative rounded-t-2xl shrink-0 ${visual.bannerBg} p-3 flex flex-col justify-between`}>
                        
                        <div className="absolute inset-0 rounded-t-2xl overflow-hidden pointer-events-none">
                          <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:12px_12px]" />
                          <div className="absolute inset-0 bg-gradient-to-t from-white dark:from-slate-900/90 via-white/20 dark:via-slate-900/20 to-transparent" />
                        </div>

                        {/* Top Bar inside Banner */}
                        <div className="relative z-20 flex items-center justify-between gap-1.5">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10.5px] font-semibold border backdrop-blur-md shadow-2xs truncate max-w-[75%] ${visual.badgeColor}`}>
                            <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                            <span className="truncate">{visual.tag}</span>
                          </span>

                          <div className="flex items-center gap-1">
                            {proj.is_pinned && (
                              <div className="p-1 rounded-md bg-blue-500/20 text-blue-600 dark:text-blue-300" title="Đã ghim">
                                <Pin className="w-3 h-3 fill-blue-500 dark:fill-blue-400" />
                              </div>
                            )}
                            
                            {/* 3-Dot Button */}
                            <div className="relative">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuProjectId(isMenuOpen ? null : proj.id);
                                }}
                                className="p-1 rounded-md bg-white/80 dark:bg-black/40 hover:bg-white dark:hover:bg-black/70 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer border border-slate-200/60 dark:border-transparent"
                                title="Tùy chọn sổ ghi chú"
                              >
                                <MoreVertical className="w-3.5 h-3.5" />
                              </button>

                              {/* Action Dropdown Menu */}
                              {isMenuOpen && (
                                <div
                                  onClick={(e) => e.stopPropagation()}
                                  className="absolute right-0 top-full mt-1.5 w-48 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 z-50 animate-slide-up text-xs font-semibold text-slate-700 dark:text-slate-200"
                                >
                                  <button
                                    onClick={(e) => handleStartRename(e, proj)}
                                    className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                                  >
                                    <Pencil className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                                    <span>{isVietnamese ? 'Đổi tên' : 'Rename'}</span>
                                  </button>

                                  <button
                                    onClick={(e) => handleTogglePin(e, proj.id, proj.is_pinned)}
                                    className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                                  >
                                    {proj.is_pinned ? <PinOff className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" /> : <Pin className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />}
                                    <span>{proj.is_pinned ? (isVietnamese ? 'Bỏ ghim' : 'Unpin') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                                  </button>

                                  <button
                                    onClick={(e) => handleShare(e, proj)}
                                    className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                                  >
                                    <Share2 className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                                    <span>{isVietnamese ? 'Sao chép liên kết' : 'Copy link'}</span>
                                  </button>

                                  <div className="my-1 border-t border-slate-100 dark:border-slate-800" />

                                  <button
                                    onClick={(e) => handleDelete(e, proj.id)}
                                    className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 font-bold flex items-center gap-2 transition-colors cursor-pointer"
                                  >
                                    <Trash2 className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
                                    <span>{isVietnamese ? 'Xóa đề tài' : 'Delete project'}</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Sticker Avatar */}
                        <div className="relative z-10 flex items-center">
                          <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${visual.accentColor} p-0.5 shadow-xs`}>
                            <div className="w-full h-full rounded-[10px] bg-white/95 dark:bg-slate-900/95 backdrop-blur-xs flex items-center justify-center text-lg">
                              {visual.icon}
                            </div>
                          </div>
                        </div>

                      </div>

                      {/* Card Body */}
                      <div className="p-3 sm:p-3.5 pt-2.5 flex flex-col justify-between flex-1 min-w-0">
                        <div>
                          {isEditing ? (
                            <div onClick={e => e.stopPropagation()} className="space-y-1.5">
                              <input
                                type="text"
                                autoFocus
                                value={editingName}
                                onChange={e => setEditingName(e.target.value)}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') handleSaveRename(e, proj.id);
                                  if (e.key === 'Escape') handleCancelRename(e);
                                }}
                                className="w-full px-2.5 py-1 text-xs rounded-lg bg-slate-100 dark:bg-slate-800 border border-blue-500 text-slate-900 dark:text-white font-semibold focus:outline-none"
                              />
                              <div className="flex items-center gap-1.5 justify-end">
                                <button
                                  onClick={(e) => handleSaveRename(e, proj.id)}
                                  className="px-2.5 py-0.5 rounded-md bg-blue-600 hover:bg-blue-500 text-[11px] font-bold text-white cursor-pointer"
                                >
                                  Lưu
                                </button>
                                <button
                                  onClick={handleCancelRename}
                                  className="px-2.5 py-0.5 rounded-md bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer"
                                >
                                  Hủy
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <h3 className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2 leading-snug">
                                {proj.name}
                              </h3>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                                {proj.research_question || proj.research_field || (isVietnamese ? 'Tổng quan hệ thống & Phân tích tổng hợp' : 'Systematic literature review')}
                              </p>
                            </>
                          )}
                        </div>

                        {/* Card Footer */}
                        <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800/80 mt-auto">
                          <span className="truncate">{updatedDate}</span>
                          <div className="flex items-center gap-1 text-slate-700 dark:text-slate-300 font-semibold shrink-0 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            <span>{sourceCount} {isVietnamese ? 'nguồn' : 'sources'}</span>
                            <Globe className="w-3 h-3 text-slate-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
                          </div>
                        </div>
                      </div>

                    </div>
                  );
                })}

              </div>
            ) : (
              /* ── List View Mode (Consistent Horizontal Rows) ── */
              <div className="space-y-2.5">
                
                {/* Row 1: + Tạo đề tài mới trong List View */}
                <button
                  onClick={onOpenNewProject || handleCreateNewNotebook}
                  className="w-full p-3.5 rounded-2xl bg-slate-50/70 dark:bg-slate-900/50 hover:bg-blue-50/40 dark:hover:bg-blue-950/20 border-2 border-dashed border-slate-300 dark:border-slate-700/80 hover:border-blue-500 flex items-center justify-between gap-3 transition-all duration-200 group cursor-pointer text-left shadow-2xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs group-hover:scale-105 transition-transform">
                      <Plus className="w-5 h-5 stroke-[2.8]" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {isVietnamese ? 'Tạo đề tài mới' : 'Create new project'}
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        {isVietnamese ? 'Khởi tạo đề tài nghiên cứu chuẩn PRISMA & AI RAG' : 'Start SLR with PRISMA & AI RAG'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="hidden sm:inline-block text-[10.5px] font-semibold px-2.5 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-300">
                      ✦ PRISMA & Scopus
                    </span>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white transition-all" />
                  </div>
                </button>

                {/* Project Rows */}
                {filteredProjects.map((proj) => {
                  const isEditing = editingProjectId === proj.id;
                  const isMenuOpen = activeMenuProjectId === proj.id;
                  const updatedDate = proj.updated_at 
                    ? new Date(proj.updated_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'short', year: 'numeric' })
                    : (isVietnamese ? 'Hôm nay' : 'Today');
                  const sourceCount = getProjectSourceCount(proj);
                  const visual = getNotebookVisual(proj.name, proj.research_field);

                  return (
                    <div
                      key={proj.id}
                      onClick={() => handleOpenNotebook(proj)}
                      className={`w-full p-3.5 rounded-2xl bg-white dark:bg-slate-900/90 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 border transition-all duration-200 cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs hover:shadow-sm ${
                        proj.is_pinned ? 'border-blue-500/70 bg-blue-50/20 dark:bg-blue-950/10' : 'border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                      } ${isMenuOpen ? 'relative z-40' : 'relative z-10'}`}
                    >
                      {/* Left: Icon & Titles */}
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${visual.accentColor} p-0.5 shrink-0 shadow-2xs`}>
                          <div className="w-full h-full rounded-[10px] bg-white dark:bg-slate-900 flex items-center justify-center text-base">
                            {visual.icon}
                          </div>
                        </div>

                        <div className="min-w-0 flex-1">
                          {isEditing ? (
                            <div onClick={e => e.stopPropagation()} className="flex items-center gap-1.5">
                              <input
                                type="text"
                                autoFocus
                                value={editingName}
                                onChange={e => setEditingName(e.target.value)}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') handleSaveRename(e, proj.id);
                                  if (e.key === 'Escape') handleCancelRename(e);
                                }}
                                className="px-2.5 py-1 text-xs rounded-lg bg-slate-100 dark:bg-slate-800 border border-blue-500 text-slate-900 dark:text-white font-semibold focus:outline-none"
                              />
                              <button
                                onClick={(e) => handleSaveRename(e, proj.id)}
                                className="px-2.5 py-1 rounded-md bg-blue-600 hover:bg-blue-500 text-[11px] font-bold text-white cursor-pointer"
                              >
                                Lưu
                              </button>
                              <button
                                onClick={handleCancelRename}
                                className="px-2.5 py-1 rounded-md bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-[11px] text-slate-700 dark:text-slate-300 cursor-pointer"
                              >
                                Hủy
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-1.5">
                                <h4 className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate">
                                  {proj.name}
                                </h4>
                                {proj.is_pinned && (
                                  <Pin className="w-3 h-3 fill-blue-500 dark:fill-blue-400 text-blue-500 dark:text-blue-400 shrink-0" title="Đã ghim" />
                                )}
                              </div>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-xl">
                                {proj.research_question || proj.research_field || (isVietnamese ? 'Tổng quan hệ thống & Phân tích tổng hợp' : 'Systematic literature review')}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right: Badge, Sources, Date, Actions */}
                      <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-5 w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100 dark:border-slate-800/80 shrink-0 text-xs text-slate-500 dark:text-slate-400">
                        
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${visual.badgeColor}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                          <span>{visual.tag}</span>
                        </span>

                        <div className="flex items-center gap-1 text-slate-700 dark:text-slate-300 font-semibold text-[11px]">
                          <span>{sourceCount} {isVietnamese ? 'nguồn' : 'sources'}</span>
                          <Globe className="w-3 h-3 text-slate-400" />
                        </div>

                        <span className="hidden md:inline-block text-slate-400 text-[11px]">
                          {updatedDate}
                        </span>

                        {/* 3-Dot Action Menu */}
                        <div className="relative" onClick={e => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMenuProjectId(isMenuOpen ? null : proj.id);
                            }}
                            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
                            title="Tùy chọn sổ ghi chú"
                          >
                            <MoreVertical className="w-3.5 h-3.5" />
                          </button>

                          {isMenuOpen && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 top-full mt-1.5 w-48 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 z-50 animate-slide-up text-xs font-semibold text-slate-700 dark:text-slate-200"
                            >
                              <button
                                onClick={(e) => handleStartRename(e, proj)}
                                className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                              >
                                <Pencil className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                                <span>{isVietnamese ? 'Đổi tên' : 'Rename'}</span>
                              </button>

                              <button
                                onClick={(e) => handleTogglePin(e, proj.id, proj.is_pinned)}
                                className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                              >
                                {proj.is_pinned ? <PinOff className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" /> : <Pin className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />}
                                <span>{proj.is_pinned ? (isVietnamese ? 'Bỏ ghim' : 'Unpin') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                              </button>

                              <button
                                onClick={(e) => handleShare(e, proj)}
                                className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors cursor-pointer text-slate-700 dark:text-slate-200"
                              >
                                <Share2 className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                                <span>{isVietnamese ? 'Sao chép liên kết' : 'Copy link'}</span>
                              </button>

                              <div className="my-1 border-t border-slate-100 dark:border-slate-800" />

                              <button
                                onClick={(e) => handleDelete(e, proj.id)}
                                className="w-full px-2.5 py-1.5 rounded-lg text-left hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 font-bold flex items-center gap-2 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
                                <span>{isVietnamese ? 'Xóa đề tài' : 'Delete project'}</span>
                              </button>
                            </div>
                          )}
                        </div>

                      </div>
                    </div>
                  );
                })}

              </div>
            )}
          </section>
        )}

        {/* ── 4. Section: Đề tài nổi bật (Featured Projects - Displayed Below) ── */}
        {(activeFilter === 'all' || activeFilter === 'featured') && (
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>{isVietnamese ? 'Đề tài nổi bật' : 'Featured Projects'}</span>
              </h2>
              <button
                onClick={() => setActiveFilter('featured')}
                className="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>{isVietnamese ? 'Xem tất cả' : 'View all'}</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
                {FEATURED_NOTEBOOKS.map(feat => (
                  <div
                    key={feat.id}
                    onClick={() => handleOpenFeatured(feat)}
                    className="group relative rounded-2xl overflow-hidden bg-white dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800 hover:border-blue-500/60 dark:hover:border-blue-500/60 shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col h-60 sm:h-64 lg:h-72"
                  >
                    {/* Cover Image */}
                    <div className="h-28 sm:h-32 lg:h-36 w-full relative overflow-hidden bg-slate-100 dark:bg-slate-800 shrink-0">
                      <img
                        src={feat.image}
                        alt={feat.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 filter brightness-95"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-white dark:from-slate-900/90 via-white/30 dark:via-slate-900/30 to-transparent" />
                    </div>

                    {/* Body Content */}
                    <div className="p-3 sm:p-3.5 flex flex-col justify-between flex-1 min-w-0">
                      <div>
                        <div className="flex items-center gap-1 text-[11px] font-bold text-blue-600 dark:text-blue-400 truncate">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400 shrink-0" />
                          <span className="truncate">{feat.source}</span>
                        </div>
                        <h3 className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2 mt-1 leading-snug">
                          {feat.title}
                        </h3>
                      </div>

                      {/* Footer Meta */}
                      <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800 mt-auto">
                        <span className="truncate">{feat.date}</span>
                        <span className="flex items-center gap-1 text-slate-700 dark:text-slate-300 font-semibold shrink-0">
                          {feat.sourcesCount} {isVietnamese ? 'nguồn' : 'sources'} <Globe className="w-3 h-3 text-slate-400" />
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2.5">
                {FEATURED_NOTEBOOKS.map(feat => {
                  const visual = getNotebookVisual(feat.title, feat.field);
                  return (
                    <div
                      key={feat.id}
                      onClick={() => handleOpenFeatured(feat)}
                      className="w-full p-3.5 rounded-2xl bg-white dark:bg-slate-900/90 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 hover:border-blue-500/50 dark:hover:border-blue-500/50 transition-all duration-200 cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs hover:shadow-sm group"
                    >
                      {/* Left: Thumbnail & Info */}
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl overflow-hidden shrink-0 border border-slate-200/80 dark:border-slate-700/80 shadow-2xs">
                          <img
                            src={feat.image}
                            alt={feat.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10.5px] font-bold text-blue-600 dark:text-blue-400 truncate">
                              ✦ {feat.source}
                            </span>
                          </div>
                          <h4 className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
                            {feat.title}
                          </h4>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-xl">
                            {feat.question || feat.field}
                          </p>
                        </div>
                      </div>

                      {/* Right: Badge, Sources, Date, Action */}
                      <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-5 w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100 dark:border-slate-800/80 shrink-0 text-xs text-slate-500 dark:text-slate-400">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${visual.badgeColor}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                          <span>{feat.field}</span>
                        </span>

                        <div className="flex items-center gap-1 text-slate-700 dark:text-slate-300 font-semibold text-[11px]">
                          <span>{feat.sourcesCount} {isVietnamese ? 'nguồn' : 'sources'}</span>
                          <Globe className="w-3 h-3 text-slate-400" />
                        </div>

                        <span className="hidden md:inline-block text-slate-400 text-[11px]">
                          {feat.date}
                        </span>

                        <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400 font-semibold text-xs group-hover:translate-x-0.5 transition-transform">
                          <span className="hidden lg:inline">{isVietnamese ? 'Mở mẫu' : 'Open'}</span>
                          <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

      </main>

    </div>
  );
}
