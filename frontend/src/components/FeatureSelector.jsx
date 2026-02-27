import React, { useCallback, useMemo } from 'react';
import { Checkbox, InputNumber, Space, Typography } from 'antd';

const { Text } = Typography;

const STYLE_DESCRIPTION = { fontSize: 11, display: 'block', marginLeft: 22 };
const STYLE_PARAM = { marginLeft: 22, marginTop: 2 };
const STYLE_SECTION_TITLE = { fontSize: 13 };

/**
 * 特徴量選択コンポーネント。
 * レジストリの特徴量一覧をチェックボックスで表示し、
 * パラメータ付き特徴量は選択時に入力欄を展開する。
 */
function FeatureSelector({
  registry,
  featureConfig,
  onFeatureConfigChange,
  disabled,
}) {
  // featureConfig から選択中の feature_type セットを導出
  const configMap = useMemo(() => {
    const entries = featureConfig || [{ feature_type: 'raw_work_time', params: {} }];
    const map = {};
    for (const entry of entries) {
      map[entry.feature_type] = entry.params || {};
    }
    return map;
  }, [featureConfig]);

  const selectedTypes = useMemo(() => Object.keys(configMap), [configMap]);

  // params_schema からデフォルト値を取得
  const getDefaultParams = useCallback((feat) => {
    const defaults = {};
    for (const [key, schema] of Object.entries(feat.params_schema)) {
      defaults[key] = schema.default;
    }
    return defaults;
  }, []);

  // チェックボックス変更
  const handleToggle = useCallback(
    (featureType, checked) => {
      let next;
      if (checked) {
        const feat = registry.find((f) => f.feature_type === featureType);
        const params =
          feat && Object.keys(feat.params_schema).length > 0
            ? getDefaultParams(feat)
            : {};
        const current = featureConfig || [
          { feature_type: 'raw_work_time', params: {} },
        ];
        next = [...current, { feature_type: featureType, params }];
      } else {
        const current = featureConfig || [
          { feature_type: 'raw_work_time', params: {} },
        ];
        next = current.filter((e) => e.feature_type !== featureType);
      }
      onFeatureConfigChange(next.length > 0 ? next : null);
    },
    [registry, featureConfig, onFeatureConfigChange, getDefaultParams],
  );

  // パラメータ変更
  const handleParamChange = useCallback(
    (featureType, paramKey, value) => {
      if (value == null) return;
      const current = featureConfig || [
        { feature_type: 'raw_work_time', params: {} },
      ];
      const next = current.map((entry) =>
        entry.feature_type === featureType
          ? { ...entry, params: { ...entry.params, [paramKey]: value } }
          : entry,
      );
      onFeatureConfigChange(next);
    },
    [featureConfig, onFeatureConfigChange],
  );

  if (!registry || registry.length === 0) return null;

  return (
    <div>
      <Text style={STYLE_SECTION_TITLE}>特徴量</Text>
      <Space direction="vertical" size={4} style={{ width: '100%', marginTop: 4 }}>
        {registry.map((feat) => {
          const isSelected = selectedTypes.includes(feat.feature_type);
          const hasParams = Object.keys(feat.params_schema).length > 0;
          return (
            <div key={feat.feature_type}>
              <Checkbox
                checked={isSelected}
                disabled={disabled}
                onChange={(e) =>
                  handleToggle(feat.feature_type, e.target.checked)
                }
              >
                {feat.label}
              </Checkbox>
              <Text type="secondary" style={STYLE_DESCRIPTION}>
                {feat.description}
              </Text>
              {isSelected && hasParams && (
                <div style={STYLE_PARAM}>
                  {Object.entries(feat.params_schema).map(([key, schema]) => (
                    <Space key={key} size="small">
                      <Text type="secondary">{key}:</Text>
                      <InputNumber
                        min={schema.min}
                        value={
                          configMap[feat.feature_type]?.[key] ?? schema.default
                        }
                        onChange={(v) =>
                          handleParamChange(feat.feature_type, key, v)
                        }
                        disabled={disabled}
                        size="small"
                      />
                    </Space>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </Space>
    </div>
  );
}

export default React.memo(FeatureSelector);
