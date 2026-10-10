# SATARKK UI Refresh — Baseline Verification Results

**Date of Execution:** 2026-10-10  
**Target Branch:** `feature/satarkk-ui-refresh`  
**Base Tag:** `pre-satarkk-refresh`  
**Environment:** Windows 11, Node v24.17.0, npm 12.0.2, Python 3.14.5 (virtualenv)

---

## 1. Baseline Test Executions

### 1.1 Frontend Static Typing (`tsc --noEmit`)
- **Command:** `npx tsc --noEmit`
- **Working Directory:** `GrantLens Frontend`
- **Result:** **PASS (0 errors, 0 warnings)**

### 1.2 Frontend Production Build (`npm run build`)
- **Command:** `npm run build` (`tsc -b && vite build`)
- **Working Directory:** `GrantLens Frontend`
- **Result:** **PASS (0 errors)**
  - Chunks generated:
    - `dist/index.html` (0.73 kB)
    - `dist/assets/index-NCuvIETT.css` (47.69 kB)
    - `dist/assets/framework-DbvLWIGu.js` (87.43 kB)
    - `dist/assets/index-CZ4SXjge.js` (335.18 kB)
    - `dist/assets/charts-DibZZlbW.js` (417.76 kB)
    - `dist/assets/graph-BB4DxJjf.js` (443.04 kB)
  - Duration: 11.22s

### 1.3 Frontend Component & Router Tests (`vitest run`)
- **Command:** `npm test`
- **Working Directory:** `GrantLens Frontend`
- **Result:** **PASS (28/28 tests passed across 4 test suites)**
  - `tests/api.test.ts` (16 passed)
  - `tests/graph.test.tsx` (2 passed)
  - `tests/v2.test.tsx` (5 passed)
  - `tests/components.test.tsx` (5 passed)
  - Duration: 8.31s

### 1.4 Backend Pytest Suite
- **Command:** `pytest -q --basetemp=.pytest_tmp`
- **Working Directory:** `grantlens-backend`
- **Result:** **PASS (19/19 tests passed, 1 warning)**
  - Warning: Starlette deprecation warning regarding httpx with `starlette.testclient`
  - Duration: 13.25s

---

## 2. Summary
All test suites and builds compile cleanly without pre-existing failures.
Baseline established on tag `pre-satarkk-refresh`.
