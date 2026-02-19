import { useReducer, useEffect, useCallback } from 'react';
import {
  fetchRecords,
  fetchResults,
  fetchBaselineConfig,
  saveBaselineConfig,
  deleteBaselineConfig,
} from '../services/api';

const INITIAL_SENSITIVITY = 0.5;

const INITIAL_STATE = {
  // データ
  records: [],
  trend: null,
  anomalies: [],
  // ベースライン設定
  baselineStatus: 'unconfigured', // 'unconfigured' | 'configured'
  baselineRange: null,            // { start, end } | null
  excludedIndices: [],
  sensitivity: INITIAL_SENSITIVITY,
  // UI
  interactionMode: 'select',     // 'select' | 'operate'
  loadingRecords: false,
  error: null,
  savingBaseline: false,
};

// アクション型
const A = {
  FETCH_START: 'FETCH_START',
  FETCH_SUCCESS: 'FETCH_SUCCESS',
  FETCH_ERROR: 'FETCH_ERROR',
  BASELINE_LOADED: 'BASELINE_LOADED',
  BASELINE_NOT_FOUND: 'BASELINE_NOT_FOUND',
  RESET_ALL: 'RESET_ALL',
  SET_INTERACTION_MODE: 'SET_INTERACTION_MODE',
  SET_BASELINE_RANGE: 'SET_BASELINE_RANGE',
  SET_SENSITIVITY: 'SET_SENSITIVITY',
  TOGGLE_EXCLUDE: 'TOGGLE_EXCLUDE',
  SAVE_START: 'SAVE_START',
  SAVE_SUCCESS: 'SAVE_SUCCESS',
  SAVE_ERROR: 'SAVE_ERROR',
  DELETE_SUCCESS: 'DELETE_SUCCESS',
  DELETE_RESULTS_UPDATED: 'DELETE_RESULTS_UPDATED',
  DELETE_ERROR: 'DELETE_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

/**
 * 状態遷移を一箇所に集約する reducer。
 * baselineStatus と interactionMode の連動をアトミックに処理する。
 */
export function reducer(state, action) {
  switch (action.type) {
    case A.FETCH_START:
      return { ...state, loadingRecords: true, error: null };

    case A.FETCH_SUCCESS:
      return {
        ...state,
        records: action.records,
        trend: action.trend,
        anomalies: action.anomalies,
        loadingRecords: false,
      };

    case A.FETCH_ERROR:
      return { ...state, error: action.error, loadingRecords: false };

    case A.BASELINE_LOADED:
      return {
        ...state,
        baselineStatus: 'configured',
        baselineRange: { start: action.baseline_start, end: action.baseline_end },
        sensitivity: action.sensitivity,
        excludedIndices: action.excludedIndices,
        interactionMode: 'operate',
      };

    case A.BASELINE_NOT_FOUND:
      return {
        ...state,
        baselineStatus: 'unconfigured',
        baselineRange: null,
        excludedIndices: [],
        sensitivity: INITIAL_SENSITIVITY,
        interactionMode: 'select',
      };

    case A.RESET_ALL:
      return INITIAL_STATE;

    case A.SET_INTERACTION_MODE:
      return { ...state, interactionMode: action.mode };

    case A.SET_BASELINE_RANGE:
      return { ...state, baselineRange: action.range };

    case A.SET_SENSITIVITY:
      return { ...state, sensitivity: action.sensitivity };

    case A.TOGGLE_EXCLUDE: {
      const idx = action.index;
      const prev = state.excludedIndices;
      return {
        ...state,
        excludedIndices: prev.includes(idx)
          ? prev.filter((i) => i !== idx)
          : [...prev, idx],
      };
    }

    case A.SAVE_START:
      return { ...state, savingBaseline: true };

    case A.SAVE_SUCCESS:
      return {
        ...state,
        savingBaseline: false,
        baselineStatus: 'configured',
        trend: action.trend,
        anomalies: action.anomalies,
        interactionMode: 'operate',
      };

    case A.SAVE_ERROR:
      return { ...state, savingBaseline: false, error: action.error };

    case A.DELETE_SUCCESS:
      return {
        ...state,
        baselineStatus: 'unconfigured',
        baselineRange: null,
        excludedIndices: [],
        sensitivity: INITIAL_SENSITIVITY,
        anomalies: [],
        interactionMode: 'select',
      };

    case A.DELETE_RESULTS_UPDATED:
      return {
        ...state,
        trend: action.trend,
        anomalies: action.anomalies,
      };

    case A.DELETE_ERROR:
      return { ...state, error: action.error };

    case A.CLEAR_ERROR:
      return { ...state, error: null };

    default:
      return state;
  }
}

/**
 * ベースライン設定の状態管理とAPI操作を担うカスタムhook。
 *
 * categoryId が変わると自動的にデータを取得し、
 * ベースラインの保存・削除・除外点トグル等の操作を提供する。
 */
export function useBaselineManager(categoryId) {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);

  // categoryId 変更時にレコード・分析結果・ベースライン設定を一括取得
  useEffect(() => {
    if (categoryId == null) {
      dispatch({ type: A.RESET_ALL });
      return;
    }
    let cancelled = false;
    dispatch({ type: A.FETCH_START });
    (async () => {
      try {
        const [recs, results] = await Promise.all([
          fetchRecords(categoryId),
          fetchResults(categoryId),
        ]);
        if (cancelled) return;
        dispatch({
          type: A.FETCH_SUCCESS,
          records: recs,
          trend: results.trend,
          anomalies: results.anomalies || [],
        });
        try {
          const cfg = await fetchBaselineConfig(categoryId);
          if (cancelled) return;
          const excluded = new Set(cfg.excluded_points);
          const excludedIndices = recs
            .map((r, i) => (excluded.has(r.recorded_at) ? i : -1))
            .filter((i) => i >= 0);
          dispatch({
            type: A.BASELINE_LOADED,
            baseline_start: cfg.baseline_start,
            baseline_end: cfg.baseline_end,
            sensitivity: cfg.sensitivity,
            excludedIndices,
          });
        } catch (err) {
          if (cancelled) return;
          if (err.response && err.response.status === 404) {
            dispatch({ type: A.BASELINE_NOT_FOUND });
          } else {
            throw err;
          }
        }
      } catch (err) {
        if (!cancelled) {
          dispatch({ type: A.FETCH_ERROR, error: `データ取得エラー: ${err.message}` });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [categoryId]);

  // ベースライン設定をAPIに保存し、分析結果を再取得
  const saveBaseline = useCallback(async () => {
    if (!categoryId || !state.baselineRange) return;
    dispatch({ type: A.SAVE_START });
    try {
      const excludedPoints = state.excludedIndices.map(
        (i) => state.records[i].recorded_at,
      );
      await saveBaselineConfig(categoryId, {
        baseline_start: state.baselineRange.start,
        baseline_end: state.baselineRange.end,
        sensitivity: state.sensitivity,
        excluded_points: excludedPoints,
      });
      const results = await fetchResults(categoryId);
      dispatch({
        type: A.SAVE_SUCCESS,
        trend: results.trend,
        anomalies: results.anomalies || [],
      });
    } catch (err) {
      dispatch({ type: A.SAVE_ERROR, error: `設定保存エラー: ${err.message}` });
    }
  }, [categoryId, state.baselineRange, state.excludedIndices, state.sensitivity, state.records]);

  // ベースライン設定を削除し、状態を初期化
  const deleteBaseline = useCallback(async () => {
    if (!categoryId) return;
    try {
      await deleteBaselineConfig(categoryId);
      dispatch({ type: A.DELETE_SUCCESS });
      const results = await fetchResults(categoryId);
      dispatch({
        type: A.DELETE_RESULTS_UPDATED,
        trend: results.trend,
        anomalies: results.anomalies || [],
      });
    } catch (err) {
      dispatch({ type: A.DELETE_ERROR, error: `設定リセットエラー: ${err.message}` });
    }
  }, [categoryId]);

  const toggleExclude = useCallback((idx) => {
    dispatch({ type: A.TOGGLE_EXCLUDE, index: idx });
  }, []);

  const setInteractionMode = useCallback((mode) => {
    dispatch({ type: A.SET_INTERACTION_MODE, mode });
  }, []);

  const setBaselineRange = useCallback((range) => {
    dispatch({ type: A.SET_BASELINE_RANGE, range });
  }, []);

  const setSensitivity = useCallback((sensitivity) => {
    dispatch({ type: A.SET_SENSITIVITY, sensitivity });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: A.CLEAR_ERROR });
  }, []);

  return {
    records: state.records,
    trend: state.trend,
    anomalies: state.anomalies,
    baselineStatus: state.baselineStatus,
    baselineRange: state.baselineRange,
    setBaselineRange,
    excludedIndices: state.excludedIndices,
    sensitivity: state.sensitivity,
    setSensitivity,
    savingBaseline: state.savingBaseline,
    interactionMode: state.interactionMode,
    setInteractionMode,
    loadingRecords: state.loadingRecords,
    error: state.error,
    clearError,
    saveBaseline,
    deleteBaseline,
    toggleExclude,
  };
}
