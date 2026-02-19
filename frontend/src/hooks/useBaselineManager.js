import { useState, useEffect, useCallback } from 'react';
import {
  fetchRecords,
  fetchResults,
  fetchBaselineConfig,
  saveBaselineConfig,
  deleteBaselineConfig,
} from '../services/api';

const INITIAL_SENSITIVITY = 0.5;

/**
 * ベースライン設定の状態管理とAPI操作を担うカスタムhook。
 *
 * categoryId が変わると自動的にデータを取得し、
 * ベースラインの保存・削除・除外点トグル等の操作を提供する。
 */
export function useBaselineManager(categoryId) {
  // --- データ ---
  const [records, setRecords] = useState([]);
  const [trend, setTrend] = useState(null);
  const [anomalies, setAnomalies] = useState([]);

  // --- ベースライン設定 ---
  const [baselineStatus, setBaselineStatus] = useState('unconfigured'); // 'unconfigured' | 'configured'
  const [baselineRange, setBaselineRange] = useState(null);             // { start, end } | null
  const [excludedIndices, setExcludedIndices] = useState([]);           // 除外するポイントのインデックス配列
  const [sensitivity, setSensitivity] = useState(INITIAL_SENSITIVITY);
  const [savingBaseline, setSavingBaseline] = useState(false);

  // --- インタラクションモード（Issue #41） ---
  const [interactionMode, setInteractionMode] = useState('select');     // 'select' | 'operate'
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [error, setError] = useState(null);

  // baselineStatus が変わったらデフォルトのモードに自動切替
  useEffect(() => {
    setInteractionMode(
      baselineStatus === 'configured' ? 'operate' : 'select',
    );
  }, [baselineStatus]);

  // categoryId 変更時にレコード・分析結果・ベースライン設定を一括取得
  useEffect(() => {
    if (categoryId == null) {
      setRecords([]);
      setTrend(null);
      setAnomalies([]);
      setBaselineStatus('unconfigured');
      setBaselineRange(null);
      setExcludedIndices([]);
      setSensitivity(INITIAL_SENSITIVITY);
      return;
    }
    let cancelled = false;
    setLoadingRecords(true);
    setError(null);
    (async () => {
      try {
        // レコードと分析結果を並列取得
        const [recs, results] = await Promise.all([
          fetchRecords(categoryId),
          fetchResults(categoryId),
        ]);
        if (cancelled) return;
        setRecords(recs);
        setTrend(results.trend);
        setAnomalies(results.anomalies || []);
        try {
          // ベースライン設定を取得（未設定なら404）
          const cfg = await fetchBaselineConfig(categoryId);
          if (cancelled) return;
          setBaselineStatus('configured');
          setBaselineRange({
            start: cfg.baseline_start,
            end: cfg.baseline_end,
          });
          setSensitivity(cfg.sensitivity);
          // APIの除外日付リスト → レコード配列のインデックスに変換
          const excluded = new Set(cfg.excluded_points);
          setExcludedIndices(
            recs
              .map((r, i) => (excluded.has(r.recorded_at) ? i : -1))
              .filter((i) => i >= 0),
          );
        } catch (err) {
          if (cancelled) return;
          if (err.response && err.response.status === 404) {
            setBaselineStatus('unconfigured');
            setBaselineRange(null);
            setExcludedIndices([]);
            setSensitivity(INITIAL_SENSITIVITY);
          } else {
            throw err;
          }
        }
      } catch (err) {
        if (!cancelled) setError(`データ取得エラー: ${err.message}`);
      } finally {
        if (!cancelled) setLoadingRecords(false);
      }
    })();
    return () => { cancelled = true; };
  }, [categoryId]);

  // ベースライン設定をAPIに保存し、分析結果を再取得
  const saveBaseline = useCallback(async () => {
    if (!categoryId || !baselineRange) return;
    setSavingBaseline(true);
    try {
      // インデックス → recorded_at 文字列に変換してAPI送信
      const excludedPoints = excludedIndices.map(
        (i) => records[i].recorded_at,
      );
      await saveBaselineConfig(categoryId, {
        baseline_start: baselineRange.start,
        baseline_end: baselineRange.end,
        sensitivity,
        excluded_points: excludedPoints,
      });
      setBaselineStatus('configured');
      const results = await fetchResults(categoryId);
      setTrend(results.trend);
      setAnomalies(results.anomalies || []);
    } catch (err) {
      setError(`設定保存エラー: ${err.message}`);
    } finally {
      setSavingBaseline(false);
    }
  }, [categoryId, baselineRange, excludedIndices, sensitivity, records]);

  // ベースライン設定を削除し、状態を初期化
  const deleteBaseline = useCallback(async () => {
    if (!categoryId) return;
    try {
      await deleteBaselineConfig(categoryId);
      setBaselineStatus('unconfigured');
      setBaselineRange(null);
      setExcludedIndices([]);
      setSensitivity(INITIAL_SENSITIVITY);
      setAnomalies([]);
      const results = await fetchResults(categoryId);
      setTrend(results.trend);
      setAnomalies(results.anomalies || []);
    } catch (err) {
      setError(`設定リセットエラー: ${err.message}`);
    }
  }, [categoryId]);

  // 除外点のトグル（クリックで追加/解除）
  const toggleExclude = useCallback((idx) => {
    setExcludedIndices((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx],
    );
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    records, trend, anomalies,
    baselineStatus, baselineRange, setBaselineRange,
    excludedIndices, sensitivity, setSensitivity,
    savingBaseline, interactionMode, setInteractionMode,
    loadingRecords, error, clearError,
    saveBaseline, deleteBaseline, toggleExclude,
  };
}
