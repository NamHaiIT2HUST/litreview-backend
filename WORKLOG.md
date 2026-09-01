25f5e01 Add professional HTML pitch deck with 10 slides
898258c fix(security,tests): restore fail-closed SECRET_KEY validation, stop leaking evidence text into writer prompt, fix duplicate-claim miscount, mock external deps in agent graph test
e1c0d81 chore(lint): fix ruff violations blocking backend CI (import order, unused vars, one-liners); scope targeted ignores for intentional naming conventions
44c5c72 fix(projects): fix FK-order bug that silently failed project deletion, surface delete errors in UI
6618c97 Merge pull request #48 from AI20K-Build-Phase-Cohort-3/nvh-ui
e0fd901 fix(ui): resolve overflow-x regression, & capitalization bug, undefined no-scrollbar/w-7.5 classes, unguarded modal close
b571d80 fix(ui): fix overflow and improper text wrapping in SearchTab sidebar topic scope box
eacaf89 fix(i18n): capitalize words following & symbol across all Vietnamese UI strings
9a9652a fix(brand): standardize brand tagline and remaining subheadings to sentence case
a1df525 fix(i18n): standardize all vietnamese ui text across project to sentence case
f1da22c fix(header): ensure sticky header position fixed on scroll across all screens
73633f0 fix(navbar): compact avatar profile icon and optimize responsive header
9af01d0 fix(navbar): enhance responsive layout and prevent horizontal overflow
c374322 merge: sync remote nvhung-fix-test
40b5e3b merge: sync latest changes from main into nvhung-fix-test
ebbf9c4 fix(admin): use sentence case for labels, fix broken dark-mode card background
3cef828 feat(admin): record real LLM token usage per synthesis run, polish dashboard UI
a3fba6b style(admin): polish dashboard visuals - role-colored avatars, hover states, fix header wrapping
4e6bfce fix(admin): always force admin role into the Admin tab, including from a fresh-login Overview landing
cfc7668 fix(onboarding): skip the researcher onboarding tour for admin accounts
9dfe8dc fix(auth): allow non-email usernames to log in (was HTML5-blocked by type=email)
6a6850c feat(admin): show per-user token usage and query counts in admin dashboard
ffeda9a chore: remove unreferenced duplicate team-photo assets
183f16e fix(ui): truncate long project name in navbar, clear stale citation on project switch, restore SerpApi key input
2a24f3e debug: log which claim spans the citation model judges unsupported
f0d8ece fix(ui): fix PDF highlight race condition, add auto-scroll; improve citation recall prompt
673261c fix(ui): restore setup step progress on reload, sentence-case labels, fix navbar profile truncation
155f0f7 feat(ui): merge PR #46 UI/UX overhaul, fix 5 confirmed bugs before merge
30f51ee Merge branch 'fix/test' into nvhung-fix-test
dd08d91 feat: update ui ux
adaa3a0 fix: fix author/title RAG grounding and section evidence-count display
f4a652c fix(rag): reliably ground author/title questions in DB metadata, fix page ordering bug
e034def Merge pull request #45 from AI20K-Build-Phase-Cohort-3/fix/test
8feaf95 done check bug
22f1513 fix(fast_v2): bind citations per-paragraph and show real Tier1/2 quality metrics
59000d7 feat(module1): wire Tier 1/2 pre-filter into the real fast_v2 citation pipeline
88ced5c feat(module1): add Tier 1 exact-match and the quality-metrics endpoint
c84cb49 feat(module1): wire the NLI Tier-2 pre-filter into cross_paper_analysis
ce4a380 feat(module1): train and select NLI evidence-quantification model
1dbb9c0 fix(eval): make ragas_eval_service actually compute real RAGAS scores
7cd5fc3 feat(fast_v2): port synthesis-accuracy improvements from feat/synthesis-fast-v2-ui
cc34d0c Merge remote-tracking branch 'mirror/main'
465b1ba fix(fast_v2): swap embedding model to MiniLM to fix timeout on small EC2 instances
f2b9a3f Merge pull request #3 from NamHaiIT2HUST/fix/test
e53cf62 Merge pull request #44 from AI20K-Build-Phase-Cohort-3/fix/test
599f0c0 fix: close cross-project data leak in synthesis endpoints, restore writer anti-fabrication guards, fix outline UI crashes
90aeb1f docs: update Module 1 evidence-quantification plan
cbda547 fix: correct scope-optimizer calibration, cross-project AI Screening leak, and mislabeled AI-generated citations
948150d chore: remove accidentally-committed terminal-output capture
f591a59 feat(synthesis): merge outline-first Fast v2 pipeline, fix credential cross-wiring and fabricated grounding status
05f0022 feat(synthesis): merge outline-first Fast v2 pipeline, fix credential cross-wiring and fabricated grounding status
d7dcccd fix: correct project-scoped AI Screening, silent-fabrication fallbacks, and remaining Gemini-quota tasks
b294d63 feat(llm): route tab Cấu hình/Tìm kiếm sang OpenAI gpt-4o-mini, tab Phân tích sang deepseek riêng biệt
17b132c fix: fetch full synthesis session detail on load so a finished report actually renders
147e989 fix: attach original PDF file after fast text-only upload so verification panel can preview it
948fa74 fix: scope workspace chat fallback to current project, fix upload NameError, fix layout overflow
96bef8d fix: remove redundant duplicate close (X) label on screening modal
41300c4 fix: genealogy add-paper button now toggles (was add-only, no way to remove)
220b6e2 fix: route screening and paper-summary through shared LLM router, fix NameError crash
be15fea fix: register gemini-3.6-flash model, fresh login lands on Overview tab
344bc9d fix: log every LLM retry failure, not just auth/quota/permanent
dd00703 fix: unify PICO agent through shared LLM router, pin GEMINI_MODEL to gemini-2.0-flash
b5b2791 fix: real Google auth, instant project creation, per-agent Gemini keys, project ownership checks
f856611 fix(dashboard): eliminate 30s timeout on notebook opening, enable instant 0.1s launch
3d0f511 fix(auth): add resilient direct Google & offline fallbacks so login never gets stuck
23cf25a fix(llm): set default gemini model to gemini-flash-latest
21ddd67 fix(agents): add robust academic heuristic fallback for scope optimizer and criteria generator
9dd5ad4 chore(config): keep default local port as 8000
154f845 fix(backend): fix research_field not-null constraint, add synthesis_sessions error_message column, update default gemini model
a24c3ca feat(eval): add runnable benchmark script for academic cross-encoder reranker
6de2f3b docs: add fine-tuning hyperparameters, architecture specs and benchmark results for academic reranker
d977e70 fix(api): route requests to www origin to eliminate 308 POST drop
5a3787a fix(auth): route all login and register requests through safeFetch
7dafe68 fix(auth): import safeFetch in AuthContext
c9cf003 fix(auth): update Google OAuth Client ID to match Google Cloud Console
a945d51 fix(landing): enforce fixed top-0 navbar on landing page
e7cfba7 fix(auth): restore full Google OAuth client id and safeFetch
3aeab0a fix(landing): fix sticky navigation header on scroll and remove Google client id error banner
3e2e72c perf(search): optimize quality_check speed and eliminate blocking sync calls in search loop
bfdefd9 fix(config): provide safe fallback for SECRET_KEY to ensure server starts smoothly
1990cee feat(core): merge system contracts audit and enhance strict Scopus verification filtering
17007d3 fix(landing): sync scrollytelling navigator with all 9 sections including team and acknowledgments
af3c97b feat(upload): add client-side pdf extraction and direct-upload-json to bypass edge payload limits
974a815 docs: add setup and orientation guide for this branch
1f1974a fix(app): persist active tab in sessionStorage across page reloads
ddc7078 fix(workspace): add missing X icon import in WorkspaceTab.jsx
3285c9d feat(llm): route every provider choice through one capability-gated router
96cbc2a fix(overview): hide internal default project placeholder to match NotebookLM user dashboard experience
edc63df fix(workspace): add dismiss and clear UI for upload queue in WorkspaceTab
147f5a9 fix(workspace): fix direct pdf upload and document persistence with safeFetch and auto-project creation
b4ab775 fix(ui): simplify floating dock to only show clear all and CSV export buttons
3ba77a9 feat(ui): upgrade floating bottom action dock for seamless End-to-End selection and workspace transfer
255fc75 feat(auth): restore demo profiles as real seeded accounts
94bc5b2 fix(ui): redesign auth modal divider and fix background overlap
b047de1 perf(search): optimize timeouts and reranker to achieve sub-second search response
713f069 feat(vector-index): treat the embedding model as index schema
36525f5 fix(search): import safeFetch in SearchTab.jsx
83fbde7 build(env): pin dependencies and make configuration reproducible
3f9bc57 fix(security,cost): enforce API authentication and stop silent fallbacks
d9bff4b docs(architecture): add system contracts audit and standardization plan
e0e38be fix(vector_store): safely handle dummy or malformed Gemini keys in embedding fallback
a07f35a fix(embeddings): graceful fallback for embedding provider when OpenAI key is absent
9d7bfc5 feat(deploy): switch Vercel proxy to active AWS EC2 instance 13.212.121.28
be8ef4f fix(search): use safeFetch and resolve project UUID in search API endpoints to fix backend connection error
cac86ac merge: integrate all features from feature/ngaedit-integration into main with AWS EC2 proxy and Google Client ID
a39c1c2 feat(auth): configure Google OAuth Client ID for c3-app-165.io.vn and local dev
c55770d feat(auth): configure Google OAuth Client ID for c3-app-165.io.vn and local dev
752dc8f fix(services): restore standard OpenAI/xkiro dispatch for RAG chat and synthesis services
69f80cd feat(dashboard): beautify recent notebooks with dynamic themed covers and fix action menu
1439488 feat(deploy): connect frontend directly to AWS EC2 backend via Vercel proxy rewrite and sync latest swarm improvements
f83bc1f feat(dashboard): beautify recent notebooks with dynamic themed covers and fix action menu
9d8a821 feat(deploy): connect frontend directly to AWS EC2 backend via Vercel proxy rewrite and sync latest swarm improvements
bed66da feat(deploy): connect frontend directly to AWS EC2 backend via Vercel /api/v1 proxy rewrite
147da67 Merge origin/main into feature/ngaedit-integration
97beacd fix(api): support custom string project ids seamlessly and sanitize gemini api keys
029158e feat(pico): wire multi-provider LLM cascade directly into Gap Finder and Swarm Deps for real AI PICO extraction
929987d feat(agents): support multi-provider LLM cascade (Gemini, Groq, OpenAI) across SLR swarm agents
806f342 fix(db): preserve Supabase domain for SNI routing and remove Docker HEALTHCHECK for clean Railway routing
9138fd2 clean(api): remove duplicate update_project endpoint
6c877ce fix(server): bind to dynamic PORT from environment on cloud deployment
6f441a6 fix(docker): support dynamic PORT in healthcheck and add Procfile for Railway
a8deb40 fix(db): add cascade delete on project/paper models and enable WAL mode on sqlite
78e6db2 ngaedit 1
84a574b fix(frontend): update apiConfig.js default and fallback directly to Railway live backend
fa74297 fix(landing): group logo and nav links together to shift menu left and free right space
345393b fix(landing): optimize navbar spacing and reserve right gutter for floating sidebar on laptops
20598d7 revert(landing): restore exact original PublicLandingPage layout matching localhost
d0d0320 fix(landing): balance nav links count for laptop screens to prevent button overflow
975672b fix(landing): remove overlapping side dots and compact navbar for laptop screens
29a95c6 deploy: trigger latest production build on vercel
0efe010 fix(vercel): add SPA rewrite rules to vercel.json
8f26dca fix(landing): align header max-w-7xl with hero section and fix side indicators
171f66d fix(landing): polish navbar responsive spacing and prevent button clipping
e6114b4 fix(frontend): add explicit favicon and shortcut icon tags
0cf785c fix(database): use safe ALTER TABLE IF NOT EXISTS to prevent DuplicateColumnError on startup
6b68396 fix(docker): resolve CPU-only torch installation with extra-index-url
1e136d0 fix(docker): install cpu-only torch first to save 2.5GB and prevent 512MB OOM on Render
6d186a4 fix(docker): install CPU-only PyTorch
c0d1516 fix(deploy): bind dynamic PORT and make warmup non-blocking for Render 512MB RAM
4fab341 Merge branch 'develop' of https://github.com/AI20K-Build-Phase-Cohort-3/P-165 into develop
3069205 fix: add validate_configuration() + timeout for synthesis endpoint - Add missing validate_configuration() method to SynthesisLLMService - Add 10s timeout to ensure_paper_ingested in synthesis route to prevent hanging - Add 60s AbortController timeout in SynthesisPanel frontend
3b1d5ea docs: add fast v2 deployment environment example
87eb1e8 Merge remote-tracking branch 'origin/develop' into claude/synthesis-accuracy-speed-b92595
316cccb feat: wire semantic verification into fast v2
0e1f970 fix(swarm): ensure RealLLMAdapter is activated dynamically with live LLM configured
ec8d2d8 fix(setup): strictly scope PICO and keywords storage per project ID
5f03185 feat(notebook): instantiate clean blank project state when creating new notebook
a8a4eae feat(dashboard): navigate directly to setup tab when clicking create new notebook card
3f9c303 Merge pull request #42 from AI20K-Build-Phase-Cohort-3/feature/ui-review
82d8e14 docs(landing): eliminate redundancy between paragraph 1 and 2 in acknowledgments
3bd827d fix(landing): align member portrait face framing with custom objectPosition
69a6955 feat(landing): connect member portraits from assets and polish team card UI
c670e55 build(docker): pre-download and bake HuggingFace models into production stage
2038da5 docs(landing): enrich acknowledgments with heartfelt gratitude to instructors, mentors and lab coaches
de9cae3 fix(synthesis): enhance provider compatibility, error handling and 100% test coverage
0d9d8c6 Merge pull request #41 from AI20K-Build-Phase-Cohort-3/feature/ui-review
8e8a18e feat(landing): move Team section to bottom and add heartfelt Acknowledgments section
70f73c5 feat(landing): add Product Development Team section with member profiles and image fallback
18322cd fix(ingestion): auto-sync existing PDFChunks from DB into active vector store collection
e6de715 fix(synthesis): add UniversalJsonRunner and json_mode fallback for GoRouter/proxy compatibility
2f2992b Merge remote-tracking branch 'origin/develop' into claude/synthesis-accuracy-speed-b92595
de93a17 feat: add grounded literature synthesis for fast v2
4a6b017 fix(llm): add User-Agent default headers for GoRouter/OpenAI-compatible proxy support
2c40f28 fix(search): prevent full question sentence echoing in keywords, add clean PICO term extraction
2fdd996 style(workspace): optimize 3-column screen proportions (compact left sources, spacious center chat, balanced right studio)
c831847 feat(ui): default overview tab on login, permanent horizontal layout, clean synthesis topic input, data engine overview script, and studio resize presets
ce7c426 Merge pull request #40 from AI20K-Build-Phase-Cohort-3/feature/ui-review
0f452dc feat(i18n): add prominent language switcher to sidebar and top dashboard bar
a38e6fd fix(layout): remove parent max-w-7xl constraint in App.jsx to achieve true 100% full-width overview hub
cf5f178 style(dashboard): remove tour button and make overview hub 100% full-width fluid responsive
9e38e06 feat(dashboard): add vibrant background glow, profile menu with logout, and coming-soon empty state for shared/collections
2fa3e6e feat(workspace): implement NotebookLM 3-column architecture (Sources | Chat | Right Studio) and add papers_data fallback for AI Q&A
e6c504d fix(dashboard): count uploaded documents and workspace papers strictly as notebook sources
0d19430 chore(merge): resolve conflicts and sync develop branch into feature/ui-review
5143699 fix(dashboard): synchronize exact source count with full sample papers list for all featured research templates
ac267ce nga edit
e69ad48 feat(dashboard): adapt fluid responsive typography, larger cards and proportional layout for large desktop screens
e5e1bdb feat(dashboard): add preloaded verified papers to featured templates, calculate dynamic real source count, remove PRO tag, and polish NotebookLM UI
14d109c fix(overview): ensure sidebar is completely hidden when viewing full-screen NotebookLM overview gallery
eea9240 feat(dashboard): transform overview tab into full-width Google NotebookLM gallery with featured templates and recent notebooks grid
7c48a1c fix(workspace): add dedicated clear chat button and ensure initial clean storage on new project creation
9416509 fix(responsive): optimize viewport scaling, clamp sidebars, and eliminate layout overflows across all screen sizes
82ddfdc fix(layout): preserve main workspace and active subtab state seamlessly when toggling sidebar/navbar mode
37d7b9b fix(workspace): add key mount guard and prevent cross-project chat state race conditions
b97e4f2 fix(chat): strictly isolate chat messages and workspace state per project
b8ea579 feat(navbar): show user avatar picture, full name, and email in horizontal navbar
455665f feat(setup): enable custom research topics across all academic disciplines with starter ideas
5c3c891 style(dashboard): refine tab Tong quan with academic icons, remove AI stickers, and update .env
07b8154 Merge pull request #39 from AI20K-Build-Phase-Cohort-3/feature/ui-review
42436c6 style(landing): enlarge navbar text, simplify menu labels, and improve screen proportions
584f714 style(landing): optimize hero title spacing, line-height and column layout
886f24b fix(auth): fix login and registration flows with async handling and robust local fallback
f1acf95 feat(branding): replace purple bolt with academic research book logo and update title
59939b0 fix(ui): show full user email under user name in sidebar
c5b017e feat(ui): add horizontal navbar layout, optimize light mode colors and contrast
a994fbe style(ui): redesign AuthModal, refine landing branding and remove 2020/AI clutter
38206da style(ui): modernize light mode design system and dashboard metrics
5dae3d9 fix(workspace): resolve chat & synthesis connectivity, update AI avatar, clean redundant files
159327d fix(workspace): ensure introductory/abstract chunks are prioritized for broad queries and add auto-scroll to bottom in ChatPanel
f23df33 fix(workspace): isolate workspace sources and direct uploads per project to prevent cross-project paper leakage
f378271 fix(workspace): define togglePaperSelection and handleRemoveSource in WorkspaceTab
44ea72a fix(workspace): add missing import for RAGEvalHarnessModal preventing UI crash on WorkspaceTab
3bc7a4d feat(search): add deep dive cell inspector for research gap matrix with matching papers overview and 2 actionable research proposal directions
8eb9678 feat(search): enlarge and style 'Select all' and 'Clear all' keyword action buttons
5546e00 feat(search): add visual saturation spectrum & method density bar charts to Research Gaps modal and remove redundant close button
08dcb37 fix(search): fix abstract expand/collapse toggle per paper, standardize bilingual modal headers, and ensure reliable research gaps loading
9ea3e46 fix(search): import missing Plus icon component in SearchTab
88ebea7 feat(search): display selected search keywords pool under suggested keywords and support individual tag removal
9df15a1 feat(search): clean up search input and display dedicated PRISMA screening criteria section below keywords
e4e9521 feat(search): unify suggested keywords with search console, make SerpApi key visible, fix gap analysis and F5 persistence
81361da feat(ui): add back navigation buttons to step 2/3 and make save analysis button prominent
53ecc8b fix(persistence): resolve React async state closure bug in handleSave to guarantee F5 keeps Step 2/3 active
83de3de feat(ui): implement custom animated SVG illustrations for stepper and foolproof F5 state persistence
a9c828d feat(ui): add vibrant academic stickers to stepper, save analysis button, and robust F5 persistence
791c104 feat(ui): overhaul ResearchSetupTab with elegant academic design, smooth guidance and bilingual sync
9bbd45f fix(agent): elevate PICO & search keywords to high quality academic English phrases
331b957 fix(setup): resolve step1-setup backend argument mismatch and redesign Phase 3 PICO UI/UX with smooth guidance
8a6c7c0 fix(workspace): bind all tabs to activeProjectId and enforce zero-data leak for fresh user accounts
ab1b1a3 feat(db): enforce complete multi-tenant user isolation for projects and workspace data
784f429 fix(core): polish JWT secret length and fix duplicate User model in metadata
a45b9ba merge: sync remote develop and integrate authentication with robust communication
8411be8 fix(core): ensure robust backend-frontend communication, database SQLite auto-fallback, and complete auth endpoints
9dfe4de Merge pull request #38 from AI20K-Build-Phase-Cohort-3/feature/auth
3911ef7 merge: merge branch 'develop' into feature/auth and resolve all conflicts
3fb0e8a merge: merge branch 'origin/nvhungUIUX' into develop and resolve conflicts
2ac5e1b Merge pull request #37 from AI20K-Build-Phase-Cohort-3/claude/synthesis-accuracy-speed-b92595
51daaf5 fix: avoid blocking fast v2 event loop
78de4db merge: sync origin/develop into fast v2 mvp
b3df09a fix: simplify structured provenance manifest for fast v2
c1d8f04 fix: preserve structured claim validation diagnostics
b3ebec0 fix: increase structured manifest output budget
31f502a fix: preserve hosted generation diagnostics
595b0e4 feat: add structured provenance validation for fast v2
58e6b18 feat: add comparison-aware evidence retrieval for fast v2
7d9bcc1 fix: wire validated fast v2 runtime and facet planning
e8eb572 feat: add hosted api generator for fast v2
de48b48 feat: add remote generator service for fast v2
39f70f3 feat: add persistent semantic evidence index for fast v2
2827942 fix: restore fast v2 parity with validated evidence pipeline
45d47d1 feat(fast_v2): wire the real cross-encoder reranker behind the frozen protocol
01a4e55 feat(ui-ux): complete academic redesign, google oauth, project management, onboarding tour and dark/light mode optimization
9ac6133 docs(fast_v2): record freeze outcome, test results, and what was not ported
8385639 feat(fast_v2): wire the pipeline and add phase-timing observability
93b78ce merge: tich hop phan tich du lieu EDA vao develop
b0b11d7 update phan tich du lieu 4
efdbb87 feat(fast_v2): add deterministic P-165 citation/provenance finalizer
d8c98dc feat(fast_v2): add claim-grounding interface with unvalidated passthrough
6627e04 feat(fast_v2): add OpenScholar generator adapter and frozen prompt
fc11545 feat(fast_v2): add GroundedEvidenceBank with deterministic merge/dedupe
6ba6cf2 feat(fast_v2): add dimension query planner, selection policy, reranker contract
7e8ce1d feat(fast_v2): port validated Evidence Hygiene classifier
90cc3b1 feat(fast_v2): add Evidence-First EvidenceUnit domain type
ca04592 feat(fast_v2): add architecture freeze ADR and SYNTHESIS_MODE feature flag
640c9db update phan tich so lieu 3
79254c2 update phan tich du lieu 2
c605774 update phan tich du lieu lan 1
2f99384 adaptive rag
5fbc555 fix: stop silently falling back to non-semantic hash embeddings
65f4bba done sanbox
2b64dd5 done ragas, guardrails
248e469 Merge remote-tracking branch 'origin/develop' into develop
29daa81 hallucination
f7b6c80 feat(auth): add authentication, role-based access control, and admin dashboard
5ab2eba Merge pull request #36 from AI20K-Build-Phase-Cohort-3/finetune_model/benchmark_3domains
fb529c0 feat: complete Phase 2 multi-agent integration and finetune pipeline
186aa36 done v1.1
58c0e2a ptichdulieu error
c8a715c ok chatbot, liter
da7fd97 chatbot+liter v1
9d03798 feat(reranker): benchmark and integrate fine-tuned academic 3-domain reranker (98.55% AP)
d89aedc docs: add embedding-provider migration guide for teammates
a4a00f1 Merge fix/rag-answer-grounding-stability into develop
e679459 Merge feat/synthesis-coverage-loop into develop
9eb440d Merge fix/benchmark-eval-and-ingestion into develop
122feeb Merge fix/openai-embedding-provider into develop
b80a44a fix: stabilize grounded RAG answer generation (temperature + refusal rule)
82b4a2e feat: loop coverage expansion instead of a single fixed attempt
d2e5e97 fix: repair broken PDF ingestion path, rebuild benchmark eval set
06505b4 fix: wire up OpenAI embedding provider in vector store
69fc962 feat(search): add automated full-text and paywall-aware paper summary (TL;DR) modal
3959fe9 Merge pull request #35 from AI20K-Build-Phase-Cohort-3/feature/multi-agent-setup-search
de170da docs: add comprehensive fine-tuning pipeline guide covering user flow, input/processing/output, architecture, and step-by-step training scripts
e38db03 chore: clean up temporary test files and ignore test artifacts
b5588f3 feat: add Citation Genealogy agent with 2-way snowballing, PDF/Screening actions, scrollable sidebar, deep gap analysis modal, and VinDynamics-styled overview tab
986e04b feat: implement 100% full-motion cinematic live video backgrounds on Hero and Banner stages with interactive neural particle canvas overlay
3ae4678 feat: add dynamic Ken-Burns camera breathing, laser scanline beams, mouse-reactive neural network, and floating telemetry animations to Overview tab
207f72c feat: align Overview tab with university literature review problem statement, integrate custom 3D academic research imagery, remove unverified numbers and robot videos
58dabef feat: embed VinDynamics cinematic robot video backgrounds and banners in Overview tab, remove unwanted badge
bf5a20d feat: add interactive neural canvas background with 60fps particle mesh and glowing aura like VinDynamics
900ee94 feat: redesign Overview tab with interactive animations & workflow, refactor Setup tab with Plus Jakarta Sans and Royal Blue/White palette
dc3d6c8 style: apply VinDynamics deep-tech design language (Space Grotesk typography, #28AB67 green brand accent, industrial card modules)
661143b feat: polish Setup Tab UI with professional aesthetics and smooth auto-scroll to results
497b2ce feat: implement Human-in-the-Loop (HITL) Multi-Agent Governance on Setup tab with 3 Approval Gates
0b69b6e fix: ground evidence quotes against raw source text
7f4f4b9 feat: refine Setup tab progressive multi-agent flow per user UX design
2b32bfe feat: implement Scope Optimizer and Criteria Auto-Generator Multi-Agent Swarm on Setup tab
476ecec feat: stabilize gemini model cascade, refine search keywords display and gap analysis
7d67051 feat(slr-swarm): multi-agent supervisor graph theo Phase 2 Master Plan
892d6e3 feat: set default LLM provider to OpenAI gpt-4o-mini matching yesterday working setup
54f4c2c fix: smart AIzaSy key filtering and RAG chat metadata fallback
a610a14 fix: auto-parse GEMINI_API_KEYS plural variable and dynamic RAGService LLM resolution
5b7bd5c revert: restore Gemini LLM provider config and remove GoRouter
45ea384 feat: add GoRouter integration support in config for high-speed LLM execution
de06289 fix: integrate safeFetch helper with auto-fallback to production Render backend
7f0fb27 fix: delete ClaimEvidenceLink before EvidenceRecord to prevent ForeignKeyViolationError 500
e7088ed fix: resolve string paper_id in delete_paper and force BackgroundTasks execution on single container deployment
f7e8451 fix: resolve CORS credential error and add root vercel.json build config
43ca634 fix: add root health endpoints for Render and prevent loading failed session state on mount
00ac383 fix: allow string paper_ids in SynthesisSessionCreateRequest to prevent Pydantic 422 errors
f0b61dc fix: auto-ingest papers missing active_ingestion_id during synthesis and improve error formatting
677270c fix: dynamically resolve API_BASE fallback for Vercel production deployment
0b96bad fix: resolve synthesis fetch error, abstract enrichment via DOI, AI screening fallback, and RAG chat speed
2207bfa fix synthesis evidence and workspace flows
f7be659 Merge pull request #34 from AI20K-Build-Phase-Cohort-3/develop
7ec0862 fix(ingestion): Inject source and paper_title metadata to ChromaDB chunks to fix unknown citations and broken PDF links during auto-recovery
cc2fa18 Fix: Fallback to Crossref when Semantic Scholar and OpenAlex hit 429 limits
e42b0cf feat: add custom User-Agent headers to external academic API calls
4e83e3f fix: declare global settings variable in routes.py
4fe5855 fix: resolve NameError settings is not defined in search_papers endpoint
0c447fd fix: add pool_pre_ping=True and pool_recycle=300 to database async engine to fix stale connection 500 error
df996f0 fix: wrap search_papers in try-except block to output detailed JSON error message
d621e15 fix: normalize authors list for SQLAlchemy Paper model to prevent 500 error
2fd607a fix: remove asyncio.gather over shared DB session to eliminate SQLAlchemy concurrent operation error
862a6b4 feat: add missing POST /projects endpoint to enable project creation
93fb7f4 feat: add Semantic Scholar 3-tier search fallback and remove strict 401 requirement for zero-failure search
046f6dc build: bump version to 1.0.5 to force fresh Render Docker container deployment
0b056f6 fix: add OpenAlex mailto polite pool parameter and handle 429 rate limit exceptions gracefully
cdf9336 fix: replace undefined scopus_papers variable with target_papers in search_papers response
fe0aae7 fix: remove orphaned except block in routes.py
776f19e feat: implement sequential batch ranking search to collect exactly top 20 Scopus indexed papers
33ca9da fix: remove client-side filter in SearchTab.jsx to render all 20 returned papers
acaeb1c fix: fallback to undetermined papers when indexed count < target to prevent empty search results
80b5f5a perf: optimize search speed by only enriching the final 20 selected Scopus papers instead of all 60 ingested papers
234a98a fix: clean paper title from HTML tags and prefix badges before online abstract lookup
6ecfa25 fix: implement auto-detection and fallback for LLM provider in synthesis initialization
94da73c fix: implement automatic vector store recovery from PostgreSQL on Chroma DB cache miss
4318a96 fix: map enriched abstract and DOI back to Pydantic search response object
af77bb0 fix: add Semantic Scholar fallback to Scopus quality check abstract enrichment
ca72854 fix: implement automatic PDF re-download fallback from online URL when local ephemeral storage is wiped
d9fe172 fix: force quality_check run for cached indexed papers if they have a snippet abstract to trigger enrichment
6e6e40b fix: automatic fallback to FastAPI BackgroundTasks for synthesis when Redis/Celery is unavailable
c37ed8a fix: auto-enrich snippet abstracts to full abstracts using OpenAlex API in quality_check
ae237d4 fix: re-run quality check on cached undetermined papers to update their status
2ba7169 fix: implement smart heuristic fallback for Scopus validation to prevent empty search results on empty cloud databases
07a860d fix: run Scopus sources seeding in background task to avoid blocking startup port binding
e0b8910 fix: auto-seed minimal Scopus source list on app startup to resolve empty Supabase error
0d3be78 fix: resolve excel file path dynamically in import_scopus.py
2528061 fix: disable asyncpg statement cache for Supabase connection pooler compatibility
d6db9a2 docs: add detailed hostname logging on DNS failure
3f4f989 fix: enforce IPv4 resolution in database.py to prevent Render free-tier IPv6 connection failure to Supabase DB
547b732 docs: add MVP deliverables (README, Architecture, Eval Evidences)
d8bbdef docs: add comprehensive deployment guide for local/Supabase/Render/Vercel
3de8f1b fix: resolve Postgres schema incompatibilities - add auto migration for file_path/authors/tldr columns and prevent duplicate SearchQueryPaper keys
7351eba fix: resolve search history mismatch and single paper display bug by introducing SearchQueryPaper many-to-many model
36d03c5 fix: implement Google Scholar pagination search in SerpApi to guarantee collecting up to target Scopus-indexed count
8ab36f2 feat: configure dynamic API_BASE with VITE_API_BASE environment variable for Vercel deployment
e391769 feat: complete Export tab backend integration, auto-sync history and pre-populate latest synthesis draft
12a6133 feat: persist chatMessages state in localStorage and add Clear Chat history button to Workspace header
4674dd8 feat: persist active synthesis session on refresh, add create new session and delete session actions
1a2dceb fix: satisfy legacy NOT NULL constraints on search_query_id and year for direct uploads
f45c396 fix: document deletion cascading, propagate delete to selectedPapers, and sync naive UTC date strings to browser local time
a05c698 fix: auto-migrate papers.file_path column and resolve serpapi_api_key attribute error
83bd798 fix: support openai in suggest_keywords and handle model mismatch
b454727 chore: update .env.example with AI usage logging variables
f05f2f9 chore: clean up unnecessary test scripts and template markdown files
4aa4c98 v1.6 them lich su phien lam viec
b7829bf v1.5 merge systhesis
c2aa832 feat: merge synthesis feature from feature/workspace-ui-layout
ec0d761 v1.4
c3a666e v1.3
4a62ca2 v1.2
be52545 v1.1
acc8e2e Merge remote-tracking branch 'origin/develop' into ngaup
7848548 done 2 module đầu
87bc7c0 Fix React white screen crash by safely rendering context_used object fields in ChatPanel
d810102 Fix PyMuPDF dependency fallback to pypdf, resolve SQLite constraints, enable reload_dirs=['src'], and verify NotebookLM chat API
8ecec4c Fix Workspace persistence bug, isolate workspace sources to direct uploads, and enforce NotebookLM RAG chat
8a75a12 Fix Workspace layout from feature/workspace-ui-layout, update model to gemini-3.5-flash-lite, and fix screening type conversions
e55304b Merge branch 'feature/workspace-ui-layout' into develop, preserving advanced RAG and integrating workspace tabs
b175677 Merge branch 'nga' into develop, resolving routes import conflict
3e86ee2 feat: refine workspace scoped layout
7d3f7e0 Untrack reference folders
506b504 vv1.4
c852256 v1.4
c3623a4 Merge branch 'nga' into develop, resolving conflicts
e6ee972 Merge pull request #31 from AI20K-Build-Phase-Cohort-3/feat/search-ui-fixes-and-phase2-docs
6f658a1 Merge pull request #30 from AI20K-Build-Phase-Cohort-3/feature/synthesis-evidence-cache
8041ef7 v1.3
3374222 feat: add evidence-first synthesis pipeline
2378059 v1.2
45e1bce v1.1
f07b62e .
dacb72d chua duoc gi ca huhu
7ab6690 docs: plan synthesis pipeline optimization
2e39115 docs: design synthesis pipeline optimization
3a7f997 docs: Add Phase 2 Implementation Plan and System Architecture Context, and UI fixes
113bd13 feat: add evidence-first literature review synthesis
0dfe6e9 Refactor ExportTab: Replace mock data with real global context data
73c561c Merge branch 'feat/hung-export-update' into merge/nga-test-integration
5610a30 Refactor UI: Change Workspace transition to Excel Download and translate Excel headers
3f1ee76 Add clear selected papers button to SearchTab UI
f760b77 Fix selectedPapers state loss when papers update across multiple searches
06852cf Refactor SearchTab to navigate to Workspace instead of Library
58a6eb6 Fix remaining App.jsx merge conflict and update package-lock
d131ffe Merge branch 'feature/nga-test-setup' into merge/nga-test-integration: Keeping Research Setup and Search & Verify from fix/function, integrating Synthesis and Workspace from feature/nga-test-setup
b94c6ee fix(search): strict scopus-only filtering across API & UI, fix query deletion 500 error on UUID comparison
8ffc2ea fix(search): fix history delete F5 bug, add unmatched points section in AI screening, remove redundant scopus bar
78f6994 feat(setup): rename Save button to 'Lưu cấu hình', add success banner, persist AI suggested keywords in localStorage
f2547b2 fix(modules): put Research Setup card on top, delete query fix, rich AI screening prompt, persist search query and setup data
d3b372e feat(ui): sync history count, add delete history button, add AI screening button & overlay modal, add research setup card to left sidebar
5f32358 fix(db-and-search): migrate sqlite paper columns, convert project_id UUID, add automatic OpenAlex fallback for failed SerpApi keys
2439fd3 fix(scopus): add CrossRef API enrichment and ISSN normalization for 100% accurate Scopus matching
b1056b3 fix(search): extract real journal name from scholar summary and fallback to openalex/s2 to fix scopus matching
90b5c86 update tieppp
f014ec5 feat(search): import 48k scopus records, improve scopus matching, add screening button under search bar
4f55e3c fix(setup): use gemini-3.5-flash, robust json parsing, fix dark mode invisible text
0e3765e feat(export): complete Module M6 Export with BibTeX, CSV, Markdown, and JSON support
0daec5b Nga update load pdf
527913c Merge pull request #28 from AI20K-Build-Phase-Cohort-3/develop
203506d Merge main into develop and resolve conflicts
3a780f3 Merge pull request #27 from AI20K-Build-Phase-Cohort-3/stagging
52f5371 Merge pull request #26 from AI20K-Build-Phase-Cohort-3/feat/phase-2-search-screening
4964ccd Merge stagging and resolve search filters
eea2d8a Merge pull request #25 from AI20K-Build-Phase-Cohort-3/feature/synthesis-upgrade
e2db855 fix(synthesis): implement bounded batch dispatch & state transition (pending -> queued -> processing) for vector cleanup
ed504d1 Merge pull request #24 from AI20K-Build-Phase-Cohort-3/feature/synthesis-upgrade
cc96d62 fix(synthesis): log full traceback on cleanup failure & dispatch async celery tasks
210fd70 Merge pull request #23 from AI20K-Build-Phase-Cohort-3/feature/synthesis-upgrade
951e73b fix(synthesis): resolve race condition outbox, fail-closed claim verification, and grounding normalization
36c7d4b Merge pull request #22 from AI20K-Build-Phase-Cohort-3/feature/synthesis-upgrade
c655394 feat: implement Evidence-Driven Synthesis & Ingestion Provenance
d36bcf8 Add utility scripts
c055b03 Refactor search verify flow and update task split
2e1f03a fix(module4): fix UUID db insertion and add Quartile UX
2cdb917 feat: implement Module 4 Quality Verification frontend
fcac2fe fix(backend): align db schema and fix Pydantic validation errors
f499f68 fix(screening): allow shorter abstracts and fix Keep button UI filtering
823638e Merge pull request #21 from AI20K-Build-Phase-Cohort-3/feat/refactor-architecture
e77a95e fix: load dotenv in database.py to connect to postgres instead of sqlite
2f40359 fix: resolve backend import error and frontend dark mode issue
7ca9557 feat: implement Module 1 API and refactor Frontend routing
da4d889 chore: setup PostgreSQL models and Alembic for Phase 1
06037d2 Merge pull request #20 from AI20K-Build-Phase-Cohort-3/develop
2e0acbd Merge pull request #18 from AI20K-Build-Phase-Cohort-3/feat/rag-frontend
fd7e69f fix(backend): fix LangChain max_tokens parameter to prevent response truncation
9d4c09b feat(frontend): integrate RAG upload and chat APIs with loading states
f36c980 Merge pull request #17 from AI20K-Build-Phase-Cohort-3/develop
53756ec Merge pull request #16 from AI20K-Build-Phase-Cohort-3/feat/rag-chat
1df63bc chore(backend): remove temporary test scripts
84d78ca fix(backend): change LLM to gemini-flash-latest due to 404 error
ba008b9 Merge pull request #15 from AI20K-Build-Phase-Cohort-3/develop
9d2d7b7 fix(backend): disable LangSmith tracing to prevent 403 error in RAG chat
1cfb0d0 Merge pull request #14 from AI20K-Build-Phase-Cohort-3/feat/vector-db
dffbdb1 feat(backend): implement LangChain RAG chat API with Gemini 1.5 Flash
c2d6ecc Merge pull request #13 from AI20K-Build-Phase-Cohort-3/feature/nga
4de3cac feat: persist search state to session storage to handle F5 reload
3e4c91d fix(backend): update Gemini embedding model name to models/gemini-embedding-2
3742129 fix(backend): use embedding-001 model for Gemini
b9db221 feat(backend): integrate ChromaDB and Gemini Embeddings for vector search
9b14184 Merge pull request #12 from AI20K-Build-Phase-Cohort-3/develop
ca7f433 Merge pull request #11 from AI20K-Build-Phase-Cohort-3/feat/pdf-ingestion
d76c77b Merge pull request #10 from AI20K-Build-Phase-Cohort-3/develop
6399135 refactor(ui): remove subjective LitScore and replace with verified real data & Scopus filter
33ca19f lưu trữ và tiền xử lý file pdf
93c6340 feat(scopus): implement Scopus journal verification matching & UI status badges
fb9ac94 Merge pull request #4 from AI20K-Build-Phase-Cohort-3/feature/nga-test-setup
a4d3ed0 Merge pull request #9 from AI20K-Build-Phase-Cohort-3/feature/nga-test-setup
a1dd358 Merge branch 'develop' into feature/nga-test-setup
357c757 Nga up
838904e Merge pull request #8 from AI20K-Build-Phase-Cohort-3/feat/hung-litreview
b3ea349 Merge branch 'develop' into feat/hung-litreview
9b1e8d1 Merge pull request #6 from AI20K-Build-Phase-Cohort-3/feat/backend-api
0e92550 fix: resolve ruff lint errors
3dd9dec Merge pull request #5 from AI20K-Build-Phase-Cohort-3/develop
5efcde0 feat: Add document filter, multi-dimension sort, openalex full abstract enrichment and responsive UI view modes
de5b31b fix: resolve ruff linting errors for CI
b91e819 Nga update F5 search
59ff1f4 Merge remote-tracking branch 'origin/develop' into feature/nga-test-setup
2112b8a Merge pull request #3 from AI20K-Build-Phase-Cohort-3/feat/backend-api
ea3c565 docs: add RUN_GUIDE.md and clean up mock data
e3a32e6 feat(backend): add SerpApi and Semantic Scholar integration with BYOK and LitScore
a818ab8 Merge pull request #2 from AI20K-Build-Phase-Cohort-3/feat/ui-ux
936aa71 done FE UI/UX with mock data
2b3fef2 feat(ui): redesign LitReview Agent UI with uncluttered header, enlarged typography, VinMotion theme, and NotebookLM multi-step upload workflow
53c52e0 style(ui): overhaul UI with MotaAdmin ThemeForest dashboard template and AIoT Lab user-friendly layout
9a0b91e fix(ui): add Tailwind CSS CDN and Google Fonts to index.html for instant styling
adbed69 fix(ui): resolve xlsx import issue and refactor frontend into modular components architecture
7e0d4b0 feat(ui): add interactive LitReview AI Scholar Web UI template with Search and RAG Workspace
7e5bfc3 docs(journal): ghi lại việc test AI logging tools
bb180e5 Initial commit
