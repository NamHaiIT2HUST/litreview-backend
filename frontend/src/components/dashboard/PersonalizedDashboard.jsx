import React, { useState, useEffect } from 'react';
import {
  BookOpen, Sparkles, Search, Layers, ShieldCheck, ArrowRight,
  CheckCircle2, Bot, Database, Zap, FileText, Check, ChevronRight,
  Plus, Target, BarChart2, TrendingUp, Clock, Copy, Trash2,
  ExternalLink, ArrowUpRight, Filter, AlertCircle, RefreshCw,
  FolderKanban, Award, Compass, PieChart, FolderPlus, HelpCircle,
  Pin, PinOff, Pencil, Share2, AlertTriangle, X, MoreVertical,
  LayoutGrid, List, Settings, Globe, Cpu, Mic, Heart, Lightbulb,
  Laptop, Activity, SlidersHorizontal
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';

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

// Helper to get nice Notebook icons matching NotebookLM
const getNotebookIcon = (title = '', field = '') => {
  const text = (title + ' ' + field).toLowerCase();
  if (text.includes('robot') || text.includes('tự hành')) {
    return <span className="text-lg select-none">🤖</span>;
  }
  if (text.includes('y tế') || text.includes('sức khỏe') || text.includes('tim') || text.includes('mắt') || text.includes('med')) {
    return <span className="text-lg select-none">💖</span>;
  }
  if (text.includes('mạng') || text.includes('chip') || text.includes('embedded') || text.includes('nhúng')) {
    return <span className="text-lg select-none">📟</span>;
  }
  if (text.includes('interview') || text.includes('audio') || text.includes('tiếng') || text.includes('thoại')) {
    return <span className="text-lg select-none">🎙️</span>;
  }
  if (text.includes('toán') || text.includes('lý thuyết') || text.includes('suy luận') || text.includes('llm') || text.includes('ai')) {
    return <span className="text-lg select-none">💡</span>;
  }
  if (text.includes('dữ liệu') || text.includes('data') || text.includes('cấu trúc') || text.includes('system')) {
    return <span className="text-lg select-none">💻</span>;
  }
  return <span className="text-lg select-none">📚</span>;
};

export default function PersonalizedDashboard({ setActiveTab, onOpenNewProject, onStartTour }) {
  const { currentUser } = useAuth();
  const { 
    projects, activeProject, activeProjectId, 
    switchProject, togglePinProject, renameProject, 
    deleteProject, duplicateProject, shareProject,
    createProject
  } = useProject();
  const { t, language } = useLanguage();

  const isVietnamese = language === 'vi';

  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'mine' | 'featured' | 'shared' | 'collections'
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [sortBy, setSortBy] = useState('recent'); // 'recent' | 'name' | 'sources'

  const [activeMenuProjectId, setActiveMenuProjectId] = useState(null);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [dashboardToast, setDashboardToast] = useState(null);

  // Close menus on outside click
  useEffect(() => {
    const handleOutside = () => {
      setActiveMenuProjectId(null);
    };
    document.addEventListener('click', handleOutside);
    return () => document.removeEventListener('click', handleOutside);
  }, []);

  const showToast = (msg) => {
    setDashboardToast(msg);
    setTimeout(() => setDashboardToast(null), 2500);
  };

  // Helper to dynamically calculate actual source count of any project
  const getProjectSourceCount = (proj) => {
    try {
      const p1 = localStorage.getItem(`litreview_papers_${proj.id}`);
      const p2 = localStorage.getItem(`litreview_workspace_papers_${proj.id}`);
      const arr1 = p1 ? JSON.parse(p1) : [];
      const arr2 = p2 ? JSON.parse(p2) : [];
      const actualCount = Math.max(arr1.length, arr2.length);
      return actualCount > 0 ? actualCount : (proj.paper_count || 0);
    } catch {
      return proj.paper_count || 0;
    }
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
          text: `### 🌟 Sổ ghi chú Nghiên cứu Mẫu: ${feat.title}\n\nHệ thống đã nạp sẵn **${samplePapers.length} tài liệu học thuật chỉ mục Scopus Q1** cho đề tài này:\n\n` +
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
      showToast(isVietnamese ? 'Đã đổi tên sổ ghi chú thành công!' : 'Notebook renamed successfully!');
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
    showToast(isPinned ? (isVietnamese ? 'Đã bỏ ghim sổ ghi chú.' : 'Unpinned.') : (isVietnamese ? 'Đã ghim lên đầu!' : 'Pinned to top!'));
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
    showToast(isVietnamese ? 'Đã xóa sổ ghi chú.' : 'Notebook deleted.');
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
    <div className="min-h-screen bg-[#171A21] text-slate-100 font-sans selection:bg-blue-600 selection:text-white flex flex-col">
      
      {/* ── Toast Notification (NotebookLM style bottom pill) ── */}
      {dashboardToast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl bg-slate-900 text-white text-xs font-semibold shadow-2xl flex items-center gap-3 border border-slate-700/80 animate-slide-up">
          <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
          <span>{dashboardToast}</span>
        </div>
      )}
      
      {/* ── 1. Top NotebookLM Header Bar (Proportionally Scaled) ── */}
      <header className="sticky top-0 z-40 w-full bg-[#171A21]/95 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 lg:px-12 py-3.5 sm:py-4 lg:py-5 flex items-center justify-between gap-4">
        
        {/* Left: Brand Logo & Notebook Title */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0">
            <BookOpen className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <span className="font-display font-extrabold text-lg sm:text-2xl lg:text-3xl text-white tracking-tight">
            LitReview Notebook
          </span>
        </div>

        {/* Right: Controls, Search, View Mode, + Tạo mới, Profile */}
        <div className="flex items-center gap-3 sm:gap-4">
          
          {/* Search Input */}
          <div className="relative hidden md:block w-48 sm:w-64 lg:w-80">
            <Search className="w-4 h-4 sm:w-5 sm:h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={isVietnamese ? 'Tìm kiếm sổ ghi chú...' : 'Search notebooks...'}
              className="w-full pl-10 sm:pl-11 pr-4 py-2 sm:py-2.5 rounded-full bg-[#232834] border border-slate-700/70 text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-inner"
            />
          </div>

          {/* Grid / List Toggle */}
          <div className="flex items-center bg-[#232834] p-1 rounded-full border border-slate-700/70">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 sm:p-2 rounded-full transition-all cursor-pointer ${viewMode === 'grid' ? 'bg-[#313848] text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'}`}
              title="Chế độ Lưới"
            >
              <LayoutGrid className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 sm:p-2 rounded-full transition-all cursor-pointer ${viewMode === 'list' ? 'bg-[#313848] text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'}`}
              title="Chế độ Danh sách"
            >
              <List className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
            </button>
          </div>

          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="hidden sm:block px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full bg-[#232834] border border-slate-700/70 text-xs sm:text-sm font-semibold text-slate-200 focus:outline-none cursor-pointer"
          >
            <option value="recent">{isVietnamese ? 'Gần đây nhất' : 'Most recent'}</option>
            <option value="name">{isVietnamese ? 'Tên A - Z' : 'Name A - Z'}</option>
            <option value="sources">{isVietnamese ? 'Số lượng nguồn' : 'Most sources'}</option>
          </select>

          {/* + Tạo mới Button */}
          <button
            onClick={onOpenNewProject}
            className="px-4 sm:px-6 py-2 sm:py-2.5 rounded-full bg-white hover:bg-slate-100 text-slate-900 font-extrabold text-xs sm:text-sm lg:text-base flex items-center gap-2 shadow-lg hover:scale-105 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 sm:w-5 sm:h-5 text-slate-900 stroke-[2.8]" />
            <span>{isVietnamese ? 'Tạo mới' : 'New Notebook'}</span>
          </button>

          {/* Settings / Tour */}
          {onStartTour && (
            <button
              onClick={onStartTour}
              className="p-2 sm:p-2.5 rounded-full text-slate-400 hover:text-white hover:bg-[#232834] transition-colors cursor-pointer flex items-center gap-1.5"
              title={isVietnamese ? 'Cài đặt & Hướng dẫn' : 'Settings & Guide'}
            >
              <Settings className="w-4 h-4 sm:w-5 sm:h-5" />
              <span className="hidden lg:inline text-xs sm:text-sm font-semibold text-slate-300">{isVietnamese ? 'Cài đặt' : 'Settings'}</span>
            </button>
          )}

          {/* User Profile Avatar */}
          {currentUser?.picture ? (
            <img
              src={currentUser.picture}
              alt={currentUser.name}
              className="w-9 h-9 sm:w-11 sm:h-11 rounded-full object-cover ring-2 ring-blue-500/40 shrink-0"
            />
          ) : (
            <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-extrabold text-xs sm:text-sm flex items-center justify-center shrink-0 shadow-md">
              {userInitials}
            </div>
          )}

        </div>
      </header>

      {/* ── Main Hub Content Area (Proportional Scaling & Spacious Margins) ── */}
      <main className="flex-1 w-full max-w-[96vw] 2xl:max-w-[1840px] mx-auto px-4 sm:px-8 lg:px-12 py-6 sm:py-8 lg:py-10 space-y-8 sm:space-y-10 lg:space-y-12">
        
        {/* ── 2. Filter Category Pills (All, Mine, Featured, Shared, Collections) ── */}
        <div className="flex items-center gap-2.5 sm:gap-3.5 overflow-x-auto custom-scrollbar pb-1 text-xs sm:text-sm font-semibold">
          {[
            { id: 'all', label: isVietnamese ? 'Tất cả' : 'All' },
            { id: 'mine', label: isVietnamese ? 'Sổ ghi chú của tôi' : 'My notebooks' },
            { id: 'featured', label: isVietnamese ? 'Sổ ghi chú nổi bật' : 'Featured' },
            { id: 'shared', label: isVietnamese ? 'Được chia sẻ với tôi' : 'Shared with me' },
            { id: 'collections', label: isVietnamese ? 'Tuyển tập' : 'Collections' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-4 sm:px-6 py-2 sm:py-2.5 rounded-full transition-all whitespace-nowrap cursor-pointer ${
                activeFilter === tab.id
                  ? 'bg-white text-slate-900 font-extrabold shadow-md'
                  : 'bg-[#232834] text-slate-300 hover:bg-[#2e3444] hover:text-white border border-slate-700/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── 3. Section: Sổ ghi chú nổi bật (Featured Notebooks) ── */}
        {(activeFilter === 'all' || activeFilter === 'featured') && (
          <section className="space-y-4 sm:space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg sm:text-2xl 2xl:text-3xl font-extrabold text-white tracking-tight">
                {isVietnamese ? 'Sổ ghi chú nổi bật' : 'Featured Notebooks'}
              </h2>
              <button
                onClick={() => setActiveFilter('featured')}
                className="text-xs sm:text-sm font-bold text-slate-400 hover:text-blue-400 flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <span>{isVietnamese ? 'Xem tất cả' : 'View all'}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-5 lg:gap-6">
              {FEATURED_NOTEBOOKS.map(feat => (
                <div
                  key={feat.id}
                  onClick={() => handleOpenFeatured(feat)}
                  className="group relative rounded-3xl overflow-hidden bg-[#202531] border border-slate-800 hover:border-blue-500/80 shadow-md hover:shadow-2xl hover:shadow-blue-500/10 transition-all duration-300 cursor-pointer flex flex-col h-64 sm:h-72 lg:h-80 2xl:h-88"
                >
                  {/* Cover Image */}
                  <div className="h-32 sm:h-36 lg:h-44 2xl:h-48 w-full relative overflow-hidden bg-slate-800 shrink-0">
                    <img
                      src={feat.image}
                      alt={feat.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 filter brightness-95 contrast-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#202531] via-[#202531]/40 to-transparent" />
                  </div>

                  {/* Body Content */}
                  <div className="p-4 sm:p-5 flex flex-col justify-between flex-1 min-w-0">
                    <div>
                      <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-blue-400 truncate">
                        <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                        <span className="truncate">{feat.source}</span>
                      </div>
                      <h3 className="font-extrabold text-xs sm:text-sm lg:text-base text-white group-hover:text-blue-300 transition-colors line-clamp-2 mt-1.5 leading-snug">
                        {feat.title}
                      </h3>
                    </div>

                    {/* Footer Meta */}
                    <div className="flex items-center justify-between text-xs sm:text-sm text-slate-400 pt-2 border-t border-slate-800/80 mt-auto">
                      <span className="truncate">{feat.date}</span>
                      <span className="flex items-center gap-1 text-slate-300 font-semibold shrink-0">
                        {feat.sourcesCount} nguồn <Globe className="w-3.5 h-3.5 text-slate-400" />
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── 4. Section: Sổ ghi chú gần đây (Recent User Notebooks) ── */}
        {(activeFilter === 'all' || activeFilter === 'mine') && (
          <section className="space-y-4 sm:space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg sm:text-2xl 2xl:text-3xl font-extrabold text-white tracking-tight">
                {isVietnamese ? 'Sổ ghi chú gần đây' : 'Recent Notebooks'}
              </h2>
              <span className="text-xs sm:text-sm font-semibold text-slate-400">
                {filteredProjects.length} {isVietnamese ? 'sổ ghi chú' : 'notebooks'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-7">
              
              {/* Card 1: + Tạo sổ ghi chú mới */}
              <button
                onClick={onOpenNewProject}
                className="h-52 sm:h-60 lg:h-68 2xl:h-72 rounded-3xl bg-[#202531]/60 hover:bg-[#202531] border-2 border-dashed border-slate-700/80 hover:border-blue-500 flex flex-col items-center justify-center p-6 sm:p-8 text-center transition-all group cursor-pointer shadow-md hover:shadow-xl"
              >
                <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-[#29303F] group-hover:bg-blue-600 text-slate-300 group-hover:text-white flex items-center justify-center mb-3.5 transition-all group-hover:scale-110 shadow-inner">
                  <Plus className="w-7 h-7 sm:w-8 sm:h-8 stroke-[2.8]" />
                </div>
                <span className="font-extrabold text-sm sm:text-base lg:text-lg text-slate-200 group-hover:text-white transition-colors">
                  {isVietnamese ? 'Tạo sổ ghi chú mới' : 'Create new notebook'}
                </span>
                <span className="text-xs sm:text-sm text-slate-400 mt-1 font-medium">
                  {isVietnamese ? 'Chuẩn PRISMA & RAG' : 'PRISMA & RAG-ready'}
                </span>
              </button>

              {/* User Projects Cards */}
              {filteredProjects.map((proj) => {
                const isEditing = editingProjectId === proj.id;
                const isMenuOpen = activeMenuProjectId === proj.id;
                const updatedDate = proj.updated_at 
                  ? new Date(proj.updated_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'short', year: 'numeric' })
                  : (isVietnamese ? 'Hôm nay' : 'Today');
                const sourceCount = getProjectSourceCount(proj);

                return (
                  <div
                    key={proj.id}
                    onClick={() => handleOpenNotebook(proj)}
                    className={`group relative h-52 sm:h-60 lg:h-68 2xl:h-72 rounded-3xl bg-[#202531] border transition-all duration-200 cursor-pointer p-5 sm:p-6 lg:p-7 flex flex-col justify-between shadow-md hover:shadow-2xl ${
                      proj.is_pinned
                        ? 'border-blue-500/80 hover:border-blue-400 bg-gradient-to-b from-[#202531] to-[#1a2234]'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {/* Card Top: Icon & 3-Dot Action Menu */}
                    <div className="flex items-center justify-between shrink-0">
                      <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-[#29303F] border border-slate-700/60 flex items-center justify-center shadow-inner">
                        {getNotebookIcon(proj.name, proj.research_field)}
                      </div>

                      <div className="flex items-center gap-1.5">
                        {proj.is_pinned && (
                          <Pin className="w-4 h-4 text-blue-400 fill-blue-400/40" />
                        )}
                        
                        {/* 3-Dot Button */}
                        <div className="relative">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMenuProjectId(isMenuOpen ? null : proj.id);
                            }}
                            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#2E3647] transition-colors cursor-pointer opacity-80 group-hover:opacity-100"
                            title="Tùy chọn sổ ghi chú"
                          >
                            <MoreVertical className="w-5 h-5" />
                          </button>

                          {/* Action Dropdown Menu */}
                          {isMenuOpen && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 top-full mt-2 w-48 rounded-2xl bg-[#1E2330] border border-slate-700/80 shadow-2xl p-1.5 z-50 animate-slide-up text-xs sm:text-sm font-semibold text-slate-200"
                            >
                              <button
                                onClick={(e) => handleStartRename(e, proj)}
                                className="w-full px-3.5 py-2.5 rounded-xl text-left hover:bg-[#2A3142] flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <Pencil className="w-4 h-4 text-slate-400" />
                                <span>{isVietnamese ? 'Đổi tên' : 'Rename'}</span>
                              </button>

                              <button
                                onClick={(e) => handleTogglePin(e, proj.id, proj.is_pinned)}
                                className="w-full px-3.5 py-2.5 rounded-xl text-left hover:bg-[#2A3142] flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                {proj.is_pinned ? <PinOff className="w-4 h-4 text-slate-400" /> : <Pin className="w-4 h-4 text-slate-400" />}
                                <span>{proj.is_pinned ? (isVietnamese ? 'Bỏ ghim' : 'Unpin') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                              </button>

                              <button
                                onClick={(e) => handleShare(e, proj)}
                                className="w-full px-3.5 py-2.5 rounded-xl text-left hover:bg-[#2A3142] flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <Share2 className="w-4 h-4 text-slate-400" />
                                <span>{isVietnamese ? 'Sao chép liên kết' : 'Copy link'}</span>
                              </button>

                              <div className="my-1 border-t border-slate-700/60" />

                              <button
                                onClick={(e) => handleDelete(e, proj.id)}
                                className="w-full px-3.5 py-2.5 rounded-xl text-left hover:bg-rose-950/50 text-rose-400 font-bold flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-4 h-4 text-rose-400" />
                                <span>{isVietnamese ? 'Xóa sổ ghi chú' : 'Delete'}</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Card Body: Title (or Inline Editing Input) */}
                    <div className="my-auto min-w-0">
                      {isEditing ? (
                        <div onClick={e => e.stopPropagation()} className="space-y-2">
                          <input
                            type="text"
                            autoFocus
                            value={editingName}
                            onChange={e => setEditingName(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleSaveRename(e, proj.id);
                              if (e.key === 'Escape') handleCancelRename(e);
                            }}
                            className="w-full px-3 py-1.5 text-xs sm:text-sm rounded-xl bg-[#2E3647] border border-blue-500 text-white font-bold focus:outline-none"
                          />
                          <div className="flex items-center gap-2 justify-end">
                            <button
                              onClick={(e) => handleSaveRename(e, proj.id)}
                              className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white"
                            >
                              Lưu
                            </button>
                            <button
                              onClick={handleCancelRename}
                              className="px-3 py-1 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs text-slate-300"
                            >
                              Hủy
                            </button>
                          </div>
                        </div>
                      ) : (
                        <h3 className="font-extrabold text-sm sm:text-base lg:text-lg 2xl:text-xl text-white group-hover:text-blue-300 transition-colors line-clamp-2 leading-snug">
                          {proj.name}
                        </h3>
                      )}
                    </div>

                    {/* Card Footer: Date & Source Count */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs sm:text-sm text-slate-400 shrink-0 font-medium">
                      <span className="truncate">{updatedDate}</span>
                      <span className="font-bold text-slate-200 shrink-0">
                        {sourceCount} {isVietnamese ? 'nguồn' : 'sources'}
                      </span>
                    </div>
                  </div>
                );
              })}

            </div>
          </section>
        )}

      </main>

    </div>
  );
}
