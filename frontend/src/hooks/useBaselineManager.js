import { useState, useEffect, useCallback } from 'react';
import {
  fetchRecords,
  fetchResults,
  fetchBaselineConfig,
  saveBaselineConfig,
  deleteBaselineConfig,
} from '../services/api';

const INITIAL_SENSITIVITY = 0.5;

export function useBaselineManager(categoryId) {
  const [records, setRecords] = useState([]);
  const [trend, setTrend] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [baselineStatus, setBaselineStatus] = useState('unconfigured');
  const [baselineRange, setBaselineRange] = useState(null);
  const [excludedIndices, setExcludedIndices] = useState([]);
  const [sensitivity, setSensitivity] = useState(INITIAL_SENSITIVITY);
  const [savingBaseline, setSavingBaseline] = useState(false);
  const [interactionMode, setInteractionMode] = useState('select');
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setInteractionMode(
      baselineStatus === 'configured' ? 'operate' : 'select',
    );
  }, [baselineStatus]);

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
        const [recs, results] = await Promise.all([
          fetchRecords(categoryId),
          fetchResults(categoryId),
        ]);
        if (cancelled) return;
        setRecords(recs);
        setTrend(results.trend);
        setAnomalies(results.anomalies || []);
        try {
          const cfg = await fetchBaselineConfig(categoryId);
          if (cancelled) return;
          setBaselineStatus('configured');
          setBaselineRange({
            start: cfg.baseline_start,
            end: cfg.baseline_end,
          });
          setSensitivity(cfg.sensitivity);
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

  const saveBaseline = useCallback(async () => {
    if (!categoryId || !baselineRange) return;
    setSavingBaseline(true);
    try {
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
