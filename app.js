/**
 * VocabMatrix - Core Application Logic
 * Supports "GitHub Source -> CDN Edge -> Client Dual-Layer Cache (Memory + IndexedDB)"
 * Slices 14,200+ CEFR English words across 22 topic datasets.
 */

// Native IndexedDB Configuration
const DB_NAME = 'VocabMatrixCacheDB';
const DB_VERSION = 6; // Version 6 loads 34 curated scene categories across 14,200 words with purified tech and expanded beverages
const STORE_NAME = 'slices';

// Application State
const state = {
  manifest: null,               // categories.json
  categories: [],               // list of category metadata
  categoriesMap: {},            // id -> category
  currentCategoryId: 'psychology',
  loadedWords: [],              // currently active category words
  memoryCache: new Map(),       // Layer 1 Cache: Map<sliceId, wordsArray>
  activeView: 'browse',
  exploreMode: 'topicFirst',    // 'topicFirst' or 'levelFirst'
  selectedDomainGroup: 'all',
  selectedTopic: 'All',
  selectedLevel: 'All',
  searchQuery: '',
  sortBy: 'level-asc',
  showOnlyFavorites: false,
  favorites: new Set(),
  // CDN Config
  cdnMode: 'cloud',             // 'cloud' enabled by default using user's repo
  githubUser: localStorage.getItem('vm_gh_user') || 'katherine54321',
  githubRepo: localStorage.getItem('vm_gh_repo') || 'my-vocab-repo',
  githubBranch: (() => {
    const saved = localStorage.getItem('vm_gh_branch');
    if (!saved || saved === 'v4.0.0' || saved === 'v3.0.0' || saved === 'v2.0.0' || saved === 'v1.0.0') {
      localStorage.setItem('vm_gh_branch', 'v5.0.0');
      return 'v5.0.0';
    }
    return saved;
  })(),
  // Flashcard State
  fcIndex: 0,
  fcList: [],
  // Quiz State
  quizIndex: 0,
  quizScore: 0,
  quizStreak: 0,
  currentQuizWord: null,
  quizOptions: []
};

// Level ordering hierarchy
const LEVEL_WEIGHT = {
  'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6
};

// ==========================================
// 1. IndexedDB Helper (Layer 2 Cache)
// ==========================================
function openIndexedDB() {
  return new Promise((resolve) => {
    if (!window.indexedDB) {
      resolve(null);
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (db.objectStoreNames.contains(STORE_NAME)) {
        db.deleteObjectStore(STORE_NAME);
      }
      db.createObjectStore(STORE_NAME, { keyPath: 'id' });
    };
    request.onsuccess = (e) => resolve(e.target.result);
    request.onerror = (e) => {
      console.warn('IndexedDB unavailable:', e);
      resolve(null);
    };
  });
}

async function getFromIndexedDB(id) {
  const db = await openIndexedDB();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    } catch (e) {
      resolve(null);
    }
  });
}

async function saveToIndexedDB(id, data) {
  const db = await openIndexedDB();
  if (!db) return;
  try {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put({ id, data, updatedAt: Date.now() });
  } catch (e) {
    console.warn('IndexedDB write error:', e);
  }
}

async function getIndexedDBKeys() {
  const db = await openIndexedDB();
  if (!db) return [];
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAllKeys();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    } catch (e) {
      resolve([]);
    }
  });
}

async function clearIndexedDB() {
  const db = await openIndexedDB();
  if (!db) return;
  try {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.clear();
  } catch (e) {
    console.warn('IndexedDB clear error:', e);
  }
}

// ==========================================
// 2. Lifecycle & CDN Slice Loader
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
  initPwaInstall();
  loadFavorites();
  initEventListeners();
  await loadCategoriesManifest();
  await loadInitialSlice();
  updateCacheStatusUI();

  // Handle URL shortcut parameters
  const urlParams = new URLSearchParams(window.location.search);
  const targetView = urlParams.get('view');
  if (targetView && ['browse', 'matrix', 'flashcards', 'quiz'].includes(targetView)) {
    switchView(targetView);
  }
});

// Dynamic 9 Domain Groups Definition
const DOMAIN_GROUPS = [
  { id: 'all', name_zh: '全部大类', icon: '🌐' },
  { id: 'academic', name_zh: '人文学科', icon: '🎓' },
  { id: 'human', name_zh: '人类与生理', icon: '🫀' },
  { id: 'food', name_zh: '食品与餐饮', icon: '🍽️' },
  { id: 'living', name_zh: '生活与空间', icon: '🏠' },
  { id: 'nature_geo', name_zh: '地理与自然', icon: '🗺️' },
  { id: 'leisure_transport', name_zh: '出行与文体', icon: '✈️' },
  { id: 'education_work', name_zh: '教育与职场', icon: '💼' },
  { id: 'science_tech', name_zh: '科技与数理', icon: '💻' },
  { id: 'core_language', name_zh: '核心语言', icon: '💬' }
];

function renderDomainGroups() {
  const container = document.getElementById('domainGroupPills');
  if (!container) return;
  container.innerHTML = '';

  const groupCounts = {};
  let totalCount = 0;
  (state.categories || []).forEach(cat => {
    const cnt = Number(cat.word_count ?? cat.count ?? 0);
    groupCounts[cat.group] = (groupCounts[cat.group] || 0) + cnt;
    totalCount += cnt;
  });
  groupCounts['all'] = totalCount;

  DOMAIN_GROUPS.forEach(grp => {
    const count = groupCounts[grp.id] || 0;
    const isActive = state.selectedDomainGroup === grp.id;
    const btn = document.createElement('button');
    btn.className = `pill-btn ${isActive ? 'active' : ''}`;
    btn.dataset.group = grp.id;
    btn.innerHTML = `${grp.icon} ${grp.name_zh} <span class="pill-count">${count.toLocaleString()}</span>`;

    btn.addEventListener('click', async () => {
      document.querySelectorAll('#domainGroupPills button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedDomainGroup = grp.id;
      state.selectedLevel = 'All';

      const visibleCategories = state.selectedDomainGroup === 'all'
        ? state.categories
        : state.categories.filter(c => c.group === state.selectedDomainGroup);

      if (visibleCategories.length > 0) {
        const isCurrentVisible = visibleCategories.some(c => c.id === state.currentCategoryId);
        if (!isCurrentVisible) {
          state.currentCategoryId = visibleCategories[0].id;
          state.loadedWords = await loadSlice(state.currentCategoryId);
        }
      }

      renderFilters();
      renderWordCards();
      renderMatrixTable();
      initFlashcards();
      initQuiz();
    });

    container.appendChild(btn);
  });
}

// Load Categories Manifest (categories.json)
async function loadCategoriesManifest() {
  try {
    if (window.CATEGORIES_INDEX && window.CATEGORIES_INDEX.categories) {
      state.manifest = window.CATEGORIES_INDEX;
    } else if (window.CATEGORIES_DATA && window.CATEGORIES_DATA.categories) {
      state.manifest = window.CATEGORIES_DATA;
    } else {
      const res = await fetch('categories.json?_t=' + Date.now());
      if (res.ok) {
        state.manifest = await res.json();
      } else {
        throw new Error('Failed to fetch categories.json');
      }
    }
  } catch (err) {
    console.warn('Could not load categories.json, loading fallback...', err);
    state.manifest = {
      version: '5.0.0',
      total_words: 14200,
      total_categories: 34,
      categories: []
    };
  }

  state.categories = state.manifest.categories || [];
  state.categoriesMap = {};
  state.categories.forEach(c => {
    state.categoriesMap[c.id] = c;
  });

  // Render Dynamic Domain Groups
  renderDomainGroups();

  // Update Header Badges
  const total = (state.manifest.total_words || 14200).toLocaleString();
  const navTotalEl = document.getElementById('navTotalCount');
  if (navTotalEl) navTotalEl.textContent = total;
  const filterTotalEl = document.getElementById('filterTotalCount');
  if (filterTotalEl) filterTotalEl.textContent = total;
  const matrixTotalEl = document.getElementById('matrixTotalCount');
  if (matrixTotalEl) matrixTotalEl.textContent = total;
  const csTotalWordsEl = document.getElementById('csTotalWords');
  if (csTotalWordsEl) csTotalWordsEl.textContent = total;
}

// Construct CDN / Local URL for slice
function getSliceUrl(sliceId) {
  if (state.cdnMode === 'cloud' && state.githubUser && state.githubRepo) {
    return `https://cdn.jsdelivr.net/gh/${state.githubUser}/${state.githubRepo}@${state.githubBranch}/data/${sliceId}.json`;
  }
  return `data/${sliceId}.json`;
}

// Detect if a cached slice contains obsolete placeholder text
function isStaleSlice(data) {
  if (!Array.isArray(data) || data.length === 0) return true;
  return data.some(it => {
    const zh = it.definition_zh || '';
    const en = it.definition_en || '';
    return zh.includes('相关词汇') || en.startsWith('Denoting ');
  });
}

// Core Slice Loading with Dual-Layer Cache
async function loadSlice(sliceId) {
  // 1. Memory Cache
  if (state.memoryCache.has(sliceId)) {
    const memData = state.memoryCache.get(sliceId);
    if (!isStaleSlice(memData)) {
      return memData;
    }
    state.memoryCache.delete(sliceId);
  }

  // 2. IndexedDB Cache
  const dbData = await getFromIndexedDB(sliceId);
  if (dbData && Array.isArray(dbData) && dbData.length > 0) {
    if (!isStaleSlice(dbData)) {
      state.memoryCache.set(sliceId, dbData);
      updateCacheStatusUI();
      return dbData;
    }
    console.log(`[Cache Refresh] Detected stale placeholder data for '${sliceId}', refreshing from source...`);
  }

  // 3. Network Fetch via CDN / Local static file (with cache buster)
  const baseUrl = getSliceUrl(sliceId);
  const url = `${baseUrl}?_t=${Date.now()}`;
  const cat = state.categoriesMap[sliceId];
  const catTitle = cat ? cat.name_zh : sliceId;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Store in both caches
    state.memoryCache.set(sliceId, data);
    await saveToIndexedDB(sliceId, data);
    updateCacheStatusUI();
    showToast(`⚡ 已载入 [${catTitle}] 权威释义并存入本地`);
    return data;
  } catch (err) {
    console.warn(`Fetch error for ${url}, trying local fallback...`, err);
    try {
      const fallbackRes = await fetch(`data/${sliceId}.json?_t=${Date.now()}`);
      const fallbackData = await fallbackRes.json();
      state.memoryCache.set(sliceId, fallbackData);
      await saveToIndexedDB(sliceId, fallbackData);
      updateCacheStatusUI();
      return fallbackData;
    } catch (e2) {
      console.error('All slice fetch fallbacks failed:', e2);
      return [];
    }
  }
}

// Load default initial slice (psychology)
async function loadInitialSlice() {
  const initialId = state.currentCategoryId || 'psychology';
  state.loadedWords = await loadSlice(initialId);
  renderFilters();
  renderWordCards();
  renderMatrixTable();
  initFlashcards();
  initQuiz();
}

// Update Cache Status in Settings Modal
async function updateCacheStatusUI() {
  const keys = await getIndexedDBKeys();
  const cachedSlicesEl = document.getElementById('csCachedSlices');
  if (cachedSlicesEl) {
    cachedSlicesEl.textContent = `${keys.length} / ${state.categories.length || 34}`;
  }

  let totalCachedWords = 0;
  for (const k of keys) {
    const cat = state.categoriesMap[k];
    if (cat) totalCachedWords += Number(cat.word_count ?? cat.count ?? 0);
  }
  const cachedWordsEl = document.getElementById('csCachedWords');
  if (cachedWordsEl) {
    cachedWordsEl.textContent = totalCachedWords.toLocaleString();
  }
}

// ==========================================
// 3. User Interface & Filters Rendering
// ==========================================
function initEventListeners() {
  // Navigation tabs (Desktop top nav & Mobile bottom tab bar)
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });
  document.querySelectorAll('.bottom-nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // CDN Modal Controls
  const cdnBtn = document.getElementById('cdnSettingsBtn');
  const cdnModal = document.getElementById('cdnModal');
  const cdnModalClose = document.getElementById('cdnModalCloseBtn');
  if (cdnBtn) {
    cdnBtn.addEventListener('click', () => {
      syncCdnInputs();
      cdnModal.style.display = 'flex';
    });
  }
  if (cdnModalClose) {
    cdnModalClose.addEventListener('click', () => {
      cdnModal.style.display = 'none';
    });
  }
  if (cdnModal) {
    cdnModal.addEventListener('click', (e) => {
      if (e.target.id === 'cdnModal') cdnModal.style.display = 'none';
    });
  }

  // CDN Form Input listeners
  const inUser = document.getElementById('cfgGithubUser');
  const inRepo = document.getElementById('cfgGithubRepo');
  const inBranch = document.getElementById('cfgGithubBranch');
  const onCdnCfgChange = () => {
    state.githubUser = inUser.value.trim() || 'your-github-username';
    state.githubRepo = inRepo.value.trim() || 'my-vocab-repo';
    state.githubBranch = inBranch.value.trim() || 'v4.0.0';
    localStorage.setItem('vm_gh_user', state.githubUser);
    localStorage.setItem('vm_gh_repo', state.githubRepo);
    localStorage.setItem('vm_gh_branch', state.githubBranch);
    updateCdnPreview();
  };
  if (inUser) inUser.addEventListener('input', onCdnCfgChange);
  if (inRepo) inRepo.addEventListener('input', onCdnCfgChange);
  if (inBranch) inBranch.addEventListener('input', onCdnCfgChange);

  // CDN Mode toggle
  const btnSrcLocal = document.getElementById('btnSourceLocal');
  const btnSrcCdn = document.getElementById('btnSourceCDN');
  if (btnSrcLocal && btnSrcCdn) {
    btnSrcLocal.addEventListener('click', () => {
      state.cdnMode = 'local';
      btnSrcLocal.classList.add('active');
      btnSrcCdn.classList.remove('active');
      document.getElementById('cdnStatusText').textContent = '本地高速';
      showToast('已切换至: 本地极速切片模式');
    });
    btnSrcCdn.addEventListener('click', () => {
      state.cdnMode = 'cloud';
      btnSrcCdn.classList.add('active');
      btnSrcLocal.classList.remove('active');
      document.getElementById('cdnStatusText').textContent = 'CDN 加速';
      showToast('已切换至: jsDelivr 全球 CDN 边缘分发模式');
    });
  }

  // Prefetch All Slices into IndexedDB
  const btnPrefetch = document.getElementById('btnPrefetchAll');
  if (btnPrefetch) {
    btnPrefetch.addEventListener('click', async () => {
      btnPrefetch.disabled = true;
      btnPrefetch.textContent = '⏳ 正在预加载全部 14,200 词...';
      let done = 0;
      for (const cat of state.categories) {
        await loadSlice(cat.id);
        done++;
        btnPrefetch.textContent = `⏳ 预加载中 (${done}/${state.categories.length})...`;
      }
      btnPrefetch.disabled = false;
      btnPrefetch.textContent = '✅ 全部 14,200 词已常驻离线存储！';
      updateCacheStatusUI();
      showToast(`🎉 全部 ${state.categories.length} 个场景静态切片已成功持久化至本地 IndexedDB！`);
    });
  }

  // Clear Cache
  const btnClear = document.getElementById('btnClearCache');
  if (btnClear) {
    btnClear.addEventListener('click', async () => {
      if (confirm('确认清空所有已缓存至本地 IndexedDB 的切片数据吗？')) {
        await clearIndexedDB();
        state.memoryCache.clear();
        updateCacheStatusUI();
        showToast('已清空本地切片缓存');
      }
    });
  }

  // Cross explore mode toggles (if present)
  const btnModeT = document.getElementById('modeTopicFirst');
  const btnModeL = document.getElementById('modeLevelFirst');
  if (btnModeT) btnModeT.addEventListener('click', () => setExploreMode('topicFirst'));
  if (btnModeL) btnModeL.addEventListener('click', () => setExploreMode('levelFirst'));

  // Search input
  const searchInput = document.getElementById('searchInput');
  const clearSearch = document.getElementById('clearSearch');
  searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    clearSearch.style.display = state.searchQuery ? 'block' : 'none';
    renderWordCards();
  });
  clearSearch.addEventListener('click', () => {
    searchInput.value = '';
    state.searchQuery = '';
    clearSearch.style.display = 'none';
    renderWordCards();
  });

  // Favorites filter
  document.getElementById('favFilterBtn').addEventListener('click', () => {
    state.showOnlyFavorites = !state.showOnlyFavorites;
    const btn = document.getElementById('favFilterBtn');
    btn.style.background = state.showOnlyFavorites ? '#fef08a' : '';
    btn.style.borderColor = state.showOnlyFavorites ? '#eab308' : '';
    showToast(state.showOnlyFavorites ? '仅查看已收藏词汇' : '查看全部词汇');
    renderWordCards();
  });

  // Sort select
  document.getElementById('sortSelect').addEventListener('change', (e) => {
    state.sortBy = e.target.value;
    renderWordCards();
  });

  // Reset filter button
  document.getElementById('resetFiltersBtn').addEventListener('click', () => {
    state.selectedTopic = 'All';
    state.selectedLevel = 'All';
    state.searchQuery = '';
    state.showOnlyFavorites = false;
    document.getElementById('searchInput').value = '';
    renderFilters();
    renderWordCards();
  });

  // Flashcards Interactions
  const fcCard = document.getElementById('mainFlashcard');
  fcCard.addEventListener('click', () => fcCard.classList.toggle('flipped'));
  document.getElementById('fcFlip').addEventListener('click', (e) => {
    e.stopPropagation();
    fcCard.classList.toggle('flipped');
  });
  document.getElementById('fcPrev').addEventListener('click', (e) => {
    e.stopPropagation();
    prevFlashcard();
  });
  document.getElementById('fcNext').addEventListener('click', (e) => {
    e.stopPropagation();
    nextFlashcard();
  });

  // Touch swipe gesture for mobile flashcards
  let touchStartX = 0;
  let touchStartY = 0;
  fcCard.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
  }, { passive: true });

  fcCard.addEventListener('touchend', (e) => {
    const diffX = e.changedTouches[0].screenX - touchStartX;
    const diffY = e.changedTouches[0].screenY - touchStartY;
    if (Math.abs(diffX) > 40 && Math.abs(diffX) > Math.abs(diffY)) {
      if (diffX < 0) {
        nextFlashcard(); // swipe left -> next
      } else {
        prevFlashcard(); // swipe right -> previous
      }
    }
  }, { passive: true });

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {
    if (state.activeView === 'flashcards') {
      if (e.code === 'Space') {
        e.preventDefault();
        fcCard.classList.toggle('flipped');
      } else if (e.code === 'ArrowLeft') {
        prevFlashcard();
      } else if (e.code === 'ArrowRight') {
        nextFlashcard();
      }
    }
  });

  // Modal Close
  document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
  document.getElementById('wordModal').addEventListener('click', (e) => {
    if (e.target.id === 'wordModal') closeModal();
  });

  // Quiz Next
  document.getElementById('quizNextBtn').addEventListener('click', nextQuizQuestion);
}

function syncCdnInputs() {
  const inUser = document.getElementById('cfgGithubUser');
  const inRepo = document.getElementById('cfgGithubRepo');
  const inBranch = document.getElementById('cfgGithubBranch');
  if (inUser) inUser.value = state.githubUser;
  if (inRepo) inRepo.value = state.githubRepo;
  if (inBranch) inBranch.value = state.githubBranch;
  updateCdnPreview();
}

function updateCdnPreview() {
  const preview = document.getElementById('cdnPreviewUrl');
  if (preview) {
    preview.textContent = `https://cdn.jsdelivr.net/gh/${state.githubUser}/${state.githubRepo}@${state.githubBranch}/data/psychology.json`;
  }
}

function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });
  document.querySelectorAll('.bottom-nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });
  document.querySelectorAll('.app-view').forEach(view => {
    view.classList.remove('active');
  });

  const activeSec = document.getElementById(`view${capitalize(viewName)}`);
  if (activeSec) activeSec.classList.add('active');

  if (viewName === 'flashcards') {
    initFlashcards();
  } else if (viewName === 'quiz') {
    initQuiz();
  }
}

function setExploreMode(mode) {
  state.exploreMode = mode;
  const btnT = document.getElementById('modeTopicFirst');
  const btnL = document.getElementById('modeLevelFirst');
  if (btnT) btnT.classList.toggle('active', mode === 'topicFirst');
  if (btnL) btnL.classList.toggle('active', mode === 'levelFirst');
  renderFilters();
  renderWordCards();
}

// Render Category Filter Pills
function renderFilters() {
  const primaryLabel = document.getElementById('primaryFilterLabel');
  const secondaryLabel = document.getElementById('secondaryFilterLabel');
  const primaryPills = document.getElementById('primaryPills');
  const secondaryPills = document.getElementById('secondaryPills');

  primaryPills.innerHTML = '';
  secondaryPills.innerHTML = '';

  const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

  // Filter visible categories based on Domain Group
  const visibleCategories = state.selectedDomainGroup === 'all'
    ? state.categories
    : state.categories.filter(c => c.group === state.selectedDomainGroup);

  let groupTotal = 0;
  visibleCategories.forEach(c => {
    groupTotal += Number(c.word_count ?? c.count ?? 0);
  });

  if (state.exploreMode === 'topicFirst') {
    if (primaryLabel) primaryLabel.textContent = `场景切片 (${visibleCategories.length} 类)：`;
    if (secondaryLabel) secondaryLabel.textContent = '交叉难度 (CEFR)：';

    // Topic Pills
    visibleCategories.forEach(cat => {
      const isCur = cat.id === state.currentCategoryId;
      const label = `${cat.icon} ${cat.name_zh}`;
      const cnt = Number(cat.word_count ?? cat.count ?? 0);
      const pill = createPill(label, cat.id, isCur, cnt, async (val) => {
        state.currentCategoryId = val;
        state.selectedLevel = 'All';
        state.loadedWords = await loadSlice(val);
        renderFilters();
        renderWordCards();
        initFlashcards();
        initQuiz();
      });
      primaryPills.appendChild(pill);
    });

    // Level Pills for currently loaded category
    const activeCat = state.categoriesMap[state.currentCategoryId];
    const activeCatCount = activeCat ? Number(activeCat.word_count ?? activeCat.count ?? 0) : groupTotal;
    const catDist = activeCat ? activeCat.level_distribution : {};

    const allLevelBtn = createPill('全部难度', 'All', state.selectedLevel === 'All', activeCatCount, (val) => {
      state.selectedLevel = val;
      renderFilters();
      renderWordCards();
    });
    secondaryPills.appendChild(allLevelBtn);

    levels.forEach(lvl => {
      const cnt = (catDist && catDist[lvl]) || 0;
      const pill = createPill(lvl, lvl, state.selectedLevel === lvl, cnt, (val) => {
        state.selectedLevel = val;
        renderFilters();
        renderWordCards();
      }, `pill-level-${lvl}`);
      secondaryPills.appendChild(pill);
    });

  } else {
    // Mode 2: Level First
    if (primaryLabel) primaryLabel.textContent = '选择难度 (CEFR)：';
    if (secondaryLabel) secondaryLabel.textContent = `交叉场景切片 (${visibleCategories.length} 类)：`;

    // Level Pills Primary
    const allLevelBtn = createPill('全部难度', 'All', state.selectedLevel === 'All', groupTotal, (val) => {
      state.selectedLevel = val;
      renderFilters();
      renderWordCards();
    });
    primaryPills.appendChild(allLevelBtn);

    levels.forEach(lvl => {
      let lvlSum = 0;
      visibleCategories.forEach(c => {
        lvlSum += (c.level_distribution && c.level_distribution[lvl]) || 0;
      });
      const pill = createPill(lvl, lvl, state.selectedLevel === lvl, lvlSum, (val) => {
        state.selectedLevel = val;
        renderFilters();
        renderWordCards();
      }, `pill-level-${lvl}`);
      primaryPills.appendChild(pill);
    });

    // Topic Pills Secondary
    visibleCategories.forEach(cat => {
      const isCur = cat.id === state.currentCategoryId;
      let count = Number(cat.word_count ?? cat.count ?? 0);
      if (state.selectedLevel !== 'All' && cat.level_distribution) {
        count = cat.level_distribution[state.selectedLevel] || 0;
      }
      const label = `${cat.icon} ${cat.name_zh}`;
      const pill = createPill(label, cat.id, isCur, count, async (val) => {
        state.currentCategoryId = val;
        state.loadedWords = await loadSlice(val);
        renderFilters();
        renderWordCards();
      });
      secondaryPills.appendChild(pill);
    });
  }
}

function createPill(label, value, isActive, count, onClick, extraClass = '') {
  const btn = document.createElement('button');
  btn.className = `pill-btn ${extraClass} ${isActive ? 'active' : ''}`.trim();
  const countNum = (count !== null && count !== undefined) ? Number(count) : null;
  const countHtml = (countNum !== null && !isNaN(countNum))
    ? `<span class="pill-count">${countNum.toLocaleString()}</span>`
    : '';
  btn.innerHTML = `${label} ${countHtml}`;
  btn.addEventListener('click', () => onClick(value));
  return btn;
}

// Filter and Sort Word Cards
function getFilteredWords() {
  if (!state.loadedWords || state.loadedWords.length === 0) return [];

  return state.loadedWords.filter(item => {
    // Filter by Level
    if (state.selectedLevel !== 'All' && item.level !== state.selectedLevel) {
      return false;
    }
    // Filter by Favorites
    if (state.showOnlyFavorites && !state.favorites.has(item.id)) {
      return false;
    }
    // Filter by Search Query
    if (state.searchQuery) {
      const q = state.searchQuery;
      const matchWord = item.word.toLowerCase().includes(q);
      const matchEn = (item.definition_en || '').toLowerCase().includes(q);
      const matchZh = (item.definition_zh || '').includes(q);
      if (!matchWord && !matchEn && !matchZh) {
        return false;
      }
    }
    return true;
  }).sort((a, b) => {
    if (state.sortBy === 'level-asc') {
      return (LEVEL_WEIGHT[a.level] || 0) - (LEVEL_WEIGHT[b.level] || 0) || a.word.localeCompare(b.word);
    } else if (state.sortBy === 'level-desc') {
      return (LEVEL_WEIGHT[b.level] || 0) - (LEVEL_WEIGHT[a.level] || 0) || a.word.localeCompare(b.word);
    } else if (state.sortBy === 'alpha-asc') {
      return a.word.localeCompare(b.word);
    } else if (state.sortBy === 'alpha-desc') {
      return b.word.localeCompare(a.word);
    }
    return 0;
  });
}

// Render Word Cards
function renderWordCards() {
  const container = document.getElementById('wordsContainer');
  const noResults = document.getElementById('noResults');
  const matchedCountEl = document.getElementById('matchedCount');
  const selectionDescEl = document.getElementById('selectionDesc');

  if (!container) return;

  const words = getFilteredWords();
  if (matchedCountEl) matchedCountEl.textContent = words.length.toLocaleString();

  const curCat = state.categoriesMap[state.currentCategoryId];
  const catTitle = curCat ? `${curCat.icon} ${curCat.name_zh}` : state.currentCategoryId;
  const levelTxt = state.selectedLevel === 'All' ? '全部难度 (A1-C2)' : `CEFR ${state.selectedLevel}`;
  if (selectionDescEl) selectionDescEl.textContent = `[ ${catTitle} × ${levelTxt} ]`;

  if (words.length === 0) {
    container.innerHTML = '';
    if (noResults) noResults.style.display = 'block';
    return;
  }
  if (noResults) noResults.style.display = 'none';

  // Render first 150 for instant snappy responsiveness if list is huge
  const displaySlice = words.slice(0, 150);

  try {
    container.innerHTML = displaySlice.map(item => {
      const isFav = state.favorites.has(item.id);
      const egObj = item.examples && item.examples.length > 0 ? item.examples[0] : null;
      const egEn = egObj ? (typeof egObj === 'object' ? (egObj.en || '') : String(egObj)) : '';
      const highlightedEg = egEn ? highlightWord(egEn, item.word) : '';
      const safeId = String(item.id || '').replace(/'/g, "\\'");
      const safeWord = String(item.word || '').replace(/'/g, "\\'");

      return `
        <div class="word-card" data-id="${item.id}">
          <div class="card-top">
            <span class="level-badge ${item.level}">${item.level}</span>
            <div class="card-tags">
              <span class="topic-tag">${item.topic || ''}</span>
              <span class="pos-badge">${item.part_of_speech || ''}</span>
            </div>
          </div>

          <div class="card-main" onclick="openWordModal('${safeId}')">
            <div class="word-header">
              <h3 class="word-title">${item.word}</h3>
              ${item.phonetic ? `<span class="phonetic">${item.phonetic}</span>` : ''}
              <button class="audio-btn" onclick="event.stopPropagation(); playPronunciation('${safeWord}', '${item.audio || ''}')" title="发音">🔊</button>
            </div>
            <div class="word-def-zh">${item.definition_zh || item.definition_en || ''}</div>
          </div>

          <div class="card-footer">
            <button class="fav-star ${isFav ? 'active' : ''}" onclick="event.stopPropagation(); toggleFavorite('${safeId}')" title="收藏">
              ${isFav ? '⭐' : '☆'}
            </button>
            <span class="card-detail-hint" onclick="openWordModal('${safeId}')">查看详尽例句 & 释义 →</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error rendering word cards:', err);
    container.innerHTML = `<div style="padding:20px;color:red;">渲染词汇列表失败: ${err.message}</div>`;
  }
}

function highlightWord(sentence, word) {
  if (!sentence) return '';
  const text = typeof sentence === 'object' ? (sentence.en || '') : String(sentence);
  if (!text) return '';
  try {
    const escapedWord = (word || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!escapedWord) return text;
    const regex = new RegExp(`\\b(${escapedWord})\\b`, 'gi');
    return text.replace(regex, '<strong>$1</strong>');
  } catch (e) {
    return text;
  }
}

function toggleFavorite(id) {
  if (state.favorites.has(id)) {
    state.favorites.delete(id);
    showToast('已取消收藏');
  } else {
    state.favorites.add(id);
    showToast('已加入收藏夹 ⭐');
  }
  saveFavorites();
  renderWordCards();
}

function playPronunciation(word, audioUrl, rate = 0.9) {
  if (audioUrl) {
    const audio = new Audio(audioUrl);
    audio.play().catch(() => speechFallback(word, rate));
  } else {
    speechFallback(word, rate);
  }
}

function speechFallback(word, rate = 0.9) {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    utterance.rate = rate;
    window.speechSynthesis.speak(utterance);
  }
}

// Modal Word Detail
function openWordModal(id) {
  const item = state.loadedWords.find(x => x.id === id);
  if (!item) return;

  document.getElementById('mWord').textContent = item.word;
  document.getElementById('mPhonetic').textContent = item.phonetic || '';
  document.getElementById('mLevel').textContent = item.level;
  document.getElementById('mLevel').className = `level-badge ${item.level}`;
  document.getElementById('mPos').textContent = item.part_of_speech;
  document.getElementById('mTopic').textContent = item.topic;
  document.getElementById('mDefZh').textContent = item.definition_zh || item.definition_en;
  document.getElementById('mDefEn').textContent = item.definition_en;

  const audioBtn = document.getElementById('mAudioBtn');
  audioBtn.onclick = () => playPronunciation(item.word, item.audio);

  const slowBtn = document.getElementById('mPronounceBtn');
  slowBtn.onclick = () => playPronunciation(item.word, '', 0.6);

  const favBtn = document.getElementById('mFavBtn');
  const isFav = state.favorites.has(item.id);
  favBtn.textContent = isFav ? '⭐ 取消收藏' : '⭐ 收藏单词';
  favBtn.onclick = () => {
    toggleFavorite(item.id);
    favBtn.textContent = state.favorites.has(item.id) ? '⭐ 取消收藏' : '⭐ 收藏单词';
  };

  const egList = document.getElementById('mExamplesList');
  if (item.examples && item.examples.length > 0) {
    egList.innerHTML = item.examples.map(eg => {
      const en = typeof eg === 'object' ? (eg.en || '') : String(eg);
      const zh = typeof eg === 'object' ? (eg.zh || '') : '';
      return `<li>
        <div class="eg-en">${highlightWord(en, item.word)}</div>
        ${zh ? `<div class="eg-zh" style="color:var(--text-muted);font-size:0.9rem;margin-top:2px;">${zh}</div>` : ''}
      </li>`;
    }).join('');
    document.getElementById('mExamplesSection').style.display = 'block';
  } else {
    egList.innerHTML = '';
    document.getElementById('mExamplesSection').style.display = 'none';
  }

  document.getElementById('wordModal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('wordModal').style.display = 'none';
}

// ==========================================
// 4. 2D Heatmap Matrix Table
// ==========================================
function renderMatrixTable() {
  const table = document.getElementById('matrixTable');
  if (!table) return;

  const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

  let html = `
    <thead>
      <tr>
        <th class="matrix-topic-cell">场景切片 (${state.categories.length || 34} 个主题分类)</th>
        ${levels.map(l => `<th>${l}</th>`).join('')}
        <th>场景词汇小计</th>
      </tr>
    </thead>
    <tbody>
  `;

  let grandTotal = 0;
  const colTotals = { 'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0 };

  state.categories.forEach(cat => {
    html += `<tr><td class="matrix-topic-cell">${cat.icon} ${cat.name_zh}</td>`;
    const dist = cat.level_distribution || {};
    let rowSum = 0;

    levels.forEach(lvl => {
      const count = dist[lvl] || 0;
      rowSum += count;
      colTotals[lvl] += count;

      let countClass = 'count-0';
      if (count > 0 && count <= 50) countClass = 'count-low';
      else if (count > 50 && count <= 200) countClass = 'count-mid';
      else if (count > 200) countClass = 'count-high';

      html += `
        <td>
          <span class="matrix-cell-count ${countClass}" onclick="drillDownMatrixSlice('${cat.id}', '${lvl}')" title="点击下钻: ${cat.name_zh} × ${lvl}">
            ${count}
          </span>
        </td>
      `;
    });

    grandTotal += rowSum;
    html += `<td><strong>${rowSum.toLocaleString()}</strong></td></tr>`;
  });

  html += `
    </tbody>
    <tfoot>
      <tr style="font-weight: 700; background: #f8fafc;">
        <td class="matrix-topic-cell">全词库难度合计</td>
        ${levels.map(lvl => `<td><span class="matrix-cell-count count-mid">${colTotals[lvl].toLocaleString()}</span></td>`).join('')}
        <td style="color:var(--primary); font-size:1.05rem;"><strong>${grandTotal.toLocaleString()}</strong></td>
      </tr>
    </tfoot>
  `;

  table.innerHTML = html;
}

async function drillDownMatrixSlice(sliceId, level) {
  state.currentCategoryId = sliceId;
  state.selectedLevel = level;
  state.loadedWords = await loadSlice(sliceId);
  renderFilters();
  renderWordCards();
  switchView('browse');
  const cat = state.categoriesMap[sliceId];
  showToast(`已定位: ${cat ? cat.name_zh : sliceId} × ${level}`);
}

// ==========================================
// 5. Flashcards & Quiz Engine
// ==========================================
function initFlashcards() {
  state.fcList = getFilteredWords();
  if (state.fcList.length === 0) {
    state.fcList = state.loadedWords;
  }
  state.fcIndex = 0;
  updateFlashcard();
}

function updateFlashcard() {
  if (!state.fcList || state.fcList.length === 0) return;
  const item = state.fcList[state.fcIndex];
  const card = document.getElementById('mainFlashcard');
  card.classList.remove('flipped');

  document.getElementById('fcIndex').textContent = state.fcIndex + 1;
  document.getElementById('fcTotal').textContent = state.fcList.length.toLocaleString();

  const curCat = state.categoriesMap[state.currentCategoryId];
  const topicScope = curCat ? curCat.name_zh : '全部主题';
  const levelScope = state.selectedLevel === 'All' ? '全部难度' : state.selectedLevel;
  document.getElementById('fcScope').textContent = `刷词范围：${topicScope} × ${levelScope}`;

  // Front Face
  document.getElementById('fcWord').textContent = item.word;
  document.getElementById('fcLevel').textContent = item.level;
  document.getElementById('fcLevel').className = `level-badge ${item.level}`;
  document.getElementById('fcTopic').textContent = item.topic;
  document.getElementById('fcPos').textContent = item.part_of_speech;
  document.getElementById('fcPhonetic').textContent = item.phonetic || '';

  const audioBtn = document.getElementById('fcAudioBtn');
  audioBtn.onclick = (e) => {
    e.stopPropagation();
    playPronunciation(item.word, item.audio);
  };

  // Back Face
  document.getElementById('fcLevelBack').textContent = item.level;
  document.getElementById('fcLevelBack').className = `level-badge ${item.level}`;
  document.getElementById('fcTopicBack').textContent = item.topic;
  document.getElementById('fcDefZh').textContent = item.definition_zh || item.definition_en;
  document.getElementById('fcDefEn').textContent = item.definition_en;

  const egObj = item.examples && item.examples.length > 0 ? item.examples[0] : null;
  const egEn = egObj ? (typeof egObj === 'object' ? (egObj.en || '') : String(egObj)) : '';
  const egZh = egObj && typeof egObj === 'object' ? (egObj.zh || '') : '';
  const egBox = document.getElementById('fcExampleBox');
  if (egEn) {
    document.getElementById('fcEgText').innerHTML = `
      <div>${highlightWord(egEn, item.word)}</div>
      ${egZh ? `<div style="font-size:0.88rem;color:var(--text-muted);margin-top:4px;">${egZh}</div>` : ''}
    `;
    egBox.style.display = 'block';
  } else {
    egBox.style.display = 'none';
  }
}

function prevFlashcard() {
  if (state.fcIndex > 0) {
    state.fcIndex--;
    updateFlashcard();
  }
}

function nextFlashcard() {
  if (state.fcIndex < state.fcList.length - 1) {
    state.fcIndex++;
    updateFlashcard();
  } else {
    showToast('🎉 本组词汇已全部刷完！');
    state.fcIndex = 0;
    updateFlashcard();
  }
}

// Quiz Mode
function initQuiz() {
  state.quizScore = 0;
  state.quizStreak = 0;
  state.quizIndex = 0;
  updateQuizStats();
  nextQuizQuestion();
}

function updateQuizStats() {
  document.getElementById('quizScore').textContent = state.quizScore;
  document.getElementById('quizStreak').textContent = `${state.quizStreak} 🔥`;
  document.getElementById('quizCurrent').textContent = state.quizIndex + 1;
}

function nextQuizQuestion() {
  document.getElementById('quizFeedback').style.display = 'none';
  const words = state.loadedWords;
  if (!words || words.length < 4) return;

  const target = words[Math.floor(Math.random() * words.length)];
  state.currentQuizWord = target;

  const distractors = [];
  while (distractors.length < 3) {
    const candidate = words[Math.floor(Math.random() * words.length)];
    if (candidate.id !== target.id && !distractors.includes(candidate)) {
      distractors.push(candidate);
    }
  }

  const options = [target, ...distractors].sort(() => Math.random() - 0.5);
  state.quizOptions = options;

  document.getElementById('qWord').textContent = target.word;
  document.getElementById('qLevel').textContent = target.level;
  document.getElementById('qLevel').className = `level-badge ${target.level}`;
  document.getElementById('qTopic').textContent = target.topic;
  document.getElementById('qPos').textContent = target.part_of_speech;
  document.getElementById('qPhonetic').textContent = target.phonetic || '';

  document.getElementById('qAudioBtn').onclick = () => playPronunciation(target.word, target.audio);

  const optsContainer = document.getElementById('quizOptions');
  optsContainer.innerHTML = options.map((opt, idx) => `
    <button class="quiz-opt-btn" onclick="checkQuizAnswer(${idx})">
      <strong>${String.fromCharCode(65 + idx)}.</strong> ${opt.definition_zh || opt.definition_en}
    </button>
  `).join('');
}

function checkQuizAnswer(selectedIdx) {
  const chosen = state.quizOptions[selectedIdx];
  const buttons = document.querySelectorAll('.quiz-opt-btn');
  buttons.forEach(b => b.disabled = true);

  const feedbackBox = document.getElementById('quizFeedback');
  const feedbackMsg = document.getElementById('quizFeedbackMsg');

  if (chosen.id === state.currentQuizWord.id) {
    buttons[selectedIdx].classList.add('correct');
    state.quizScore += 10 + state.quizStreak * 2;
    state.quizStreak++;
    feedbackMsg.innerHTML = '<span style="color:#15803d; font-weight:700;">✅ 回答正确！精准掌握！</span>';
  } else {
    buttons[selectedIdx].classList.add('wrong');
    state.quizStreak = 0;
    state.quizOptions.forEach((opt, i) => {
      if (opt.id === state.currentQuizWord.id) {
        buttons[i].classList.add('correct');
      }
    });
    feedbackMsg.innerHTML = `<span style="color:#b91c1c; font-weight:700;">❌ 选错了，正确答案是：${state.currentQuizWord.definition_zh || state.currentQuizWord.definition_en}</span>`;
  }

  state.quizIndex++;
  updateQuizStats();
  feedbackBox.style.display = 'flex';
}

// Architecture Sample Inspector
function renderArchitectureSample() {
  const viewer = document.getElementById('jsonSampleViewer');
  if (!viewer || !state.loadedWords || state.loadedWords.length === 0) return;

  const sample = state.loadedWords[0];
  viewer.textContent = JSON.stringify(sample, null, 2);
}

// Favorites helper
function loadFavorites() {
  try {
    const saved = localStorage.getItem('vocab_matrix_favs');
    if (saved) {
      state.favorites = new Set(JSON.parse(saved));
      updateFavCountDisplay();
    }
  } catch (e) {
    console.warn('LocalStorage error:', e);
  }
}

function saveFavorites() {
  try {
    localStorage.setItem('vocab_matrix_favs', JSON.stringify(Array.from(state.favorites)));
    updateFavCountDisplay();
  } catch (e) {
    console.warn('LocalStorage error:', e);
  }
}

function updateFavCountDisplay() {
  const el = document.getElementById('favCount');
  if (el) el.textContent = state.favorites.size;
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2400);
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ==========================================
// 5. PWA Mobile App Support & Installation
// ==========================================
let deferredPrompt = null;

function initPwaInstall() {
  // 1. Service Worker registration for PWA offline capability
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then(reg => {
          console.log('[PWA] Service Worker registered successfully, scope:', reg.scope);
        })
        .catch(err => {
          console.warn('[PWA] Service Worker registration failed:', err);
        });
    });
  }

  // 2. Intercept beforeinstallprompt for Android / Chrome / Edge
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('[PWA] Captured beforeinstallprompt event');
    const installBtn = document.getElementById('pwaInstallBtn');
    if (installBtn) {
      installBtn.style.display = 'inline-flex';
    }
  });

  // 3. Listen to appinstalled event
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    showToast('🎉 VocabMatrix 词汇矩阵已成功安装至您的手机主屏幕！');
    const installBtn = document.getElementById('pwaInstallBtn');
    if (installBtn) installBtn.style.display = 'none';
    const pwaModal = document.getElementById('pwaModal');
    if (pwaModal) pwaModal.style.display = 'none';
  });

  // 4. Check if already running in standalone mode (installed app)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
  const installBtn = document.getElementById('pwaInstallBtn');
  if (isStandalone && installBtn) {
    installBtn.style.display = 'none';
  }

  // 5. Modal & button event listeners
  const pwaModal = document.getElementById('pwaModal');
  const pwaModalClose = document.getElementById('pwaModalCloseBtn');
  const btnPwaDismiss = document.getElementById('btnPwaDismiss');
  const btnDoInstallPwa = document.getElementById('btnDoInstallPwa');

  if (installBtn) {
    installBtn.addEventListener('click', () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choice) => {
          if (choice.outcome === 'accepted') {
            console.log('[PWA] User accepted installation');
          }
          deferredPrompt = null;
        });
      } else {
        // Show the guide modal (essential for iOS Safari & manual browser steps)
        if (pwaModal) pwaModal.style.display = 'flex';
      }
    });
  }

  if (btnDoInstallPwa) {
    btnDoInstallPwa.addEventListener('click', () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
          deferredPrompt = null;
          if (pwaModal) pwaModal.style.display = 'none';
        });
      } else {
        showToast('💡 请按照上方指引，点击浏览器底部的分享或菜单按钮添加到主屏幕');
      }
    });
  }

  if (pwaModalClose) {
    pwaModalClose.addEventListener('click', () => {
      if (pwaModal) pwaModal.style.display = 'none';
    });
  }

  if (btnPwaDismiss) {
    btnPwaDismiss.addEventListener('click', () => {
      if (pwaModal) pwaModal.style.display = 'none';
    });
  }

  if (pwaModal) {
    pwaModal.addEventListener('click', (e) => {
      if (e.target.id === 'pwaModal') pwaModal.style.display = 'none';
    });
  }
}
