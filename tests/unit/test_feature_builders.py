"""特徴量ビルダーのユニットテスト."""

from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.analysis.feature import (
    FEATURE_REGISTRY,
    CompositeFeatureBuilder,
    DiffFeatureBuilder,
    MovingAvgFeatureBuilder,
    MovingStdFeatureBuilder,
    RawWorkTimeFeatureBuilder,
    create_feature_builder,
)
from backend.interfaces.feature import (
    FeatureBuilder,
    FeatureConfig,
    FeatureSpec,
)


class TestCompositeFeatureBuilder:
    """CompositeFeatureBuilder のユニットテスト."""

    def test_hstack_two_builders(self):
        """2つの RawWorkTimeFeatureBuilder を結合 → shape (n, 2)."""
        b1 = RawWorkTimeFeatureBuilder()
        b2 = RawWorkTimeFeatureBuilder()
        composite = CompositeFeatureBuilder([b1, b2])
        result = composite.build([10.0, 20.0, 30.0])
        assert result.shape == (3, 2)
        np.testing.assert_array_equal(result[:, 0], [10.0, 20.0, 30.0])
        np.testing.assert_array_equal(result[:, 1], [10.0, 20.0, 30.0])

    def test_empty_builders_raises_value_error(self):
        """空リストで構築 → ValueError."""
        with pytest.raises(ValueError, match="At least one builder"):
            CompositeFeatureBuilder([])

    def test_empty_input_returns_correct_shape(self):
        """空の work_times → shape (0, 2)."""
        b1 = RawWorkTimeFeatureBuilder()
        b2 = RawWorkTimeFeatureBuilder()
        composite = CompositeFeatureBuilder([b1, b2])
        result = composite.build([])
        assert result.shape == (0, 2)

    def test_single_builder(self):
        """単一ビルダー → shape (n, 1)（1ビルダーでもCompositeで動作）."""
        b1 = RawWorkTimeFeatureBuilder()
        composite = CompositeFeatureBuilder([b1])
        result = composite.build([10.0, 20.0])
        assert result.shape == (2, 1)

    def test_timestamps_forwarded_to_inner_builders(self):
        """timestamps が内部ビルダーの build() に渡されること."""
        mock_builder = MagicMock(spec=FeatureBuilder)
        mock_builder.build.return_value = np.array([[1.0], [2.0]])
        composite = CompositeFeatureBuilder([mock_builder])

        ts = [datetime(2025, 1, 1), datetime(2025, 2, 1)]
        composite.build([10.0, 20.0], timestamps=ts)

        mock_builder.build.assert_called_once_with([10.0, 20.0], ts)


class TestDiffFeatureBuilder:
    """DiffFeatureBuilder のユニットテスト."""

    def test_basic_diff(self):
        """[10, 20, 35] → diff=[0, 10, 15], shape (3, 1)."""
        builder = DiffFeatureBuilder()
        result = builder.build([10.0, 20.0, 35.0])
        assert result.shape == (3, 1)
        np.testing.assert_array_almost_equal(
            result.flatten(), [0.0, 10.0, 15.0]
        )

    def test_first_element_zero_padded(self):
        """先頭要素は 0 パディング."""
        builder = DiffFeatureBuilder()
        result = builder.build([5.0, 8.0])
        assert result[0, 0] == 0.0

    def test_empty_input(self):
        """空入力 → shape (0, 1)."""
        builder = DiffFeatureBuilder()
        result = builder.build([])
        assert result.shape == (0, 1)

    def test_single_element(self):
        """1件 → [0.0], shape (1, 1)."""
        builder = DiffFeatureBuilder()
        result = builder.build([42.0])
        assert result.shape == (1, 1)
        assert result[0, 0] == 0.0


class TestMovingAvgFeatureBuilder:
    """MovingAvgFeatureBuilder のユニットテスト."""

    def test_basic_moving_avg(self):
        """window=3, [10, 20, 30, 40, 50] → index2=20, index3=30."""
        builder = MovingAvgFeatureBuilder(window=3)
        result = builder.build([10.0, 20.0, 30.0, 40.0, 50.0])
        assert result.shape == (5, 1)
        assert result[2, 0] == pytest.approx(20.0)
        assert result[3, 0] == pytest.approx(30.0)

    def test_padding_is_zero(self):
        """window 未満の先頭は 0 パディング."""
        builder = MovingAvgFeatureBuilder(window=3)
        result = builder.build([10.0, 20.0, 30.0])
        assert result[0, 0] == 0.0
        assert result[1, 0] == 0.0

    def test_default_window_is_5(self):
        """デフォルト window=5."""
        builder = MovingAvgFeatureBuilder()
        result = builder.build([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        assert result.shape == (6, 1)
        # index 0-3: 0パディング, index 4: avg(1,2,3,4,5)=3.0
        assert result[4, 0] == pytest.approx(3.0)

    def test_empty_input(self):
        """空入力 → shape (0, 1)."""
        builder = MovingAvgFeatureBuilder()
        result = builder.build([])
        assert result.shape == (0, 1)


class TestMovingStdFeatureBuilder:
    """MovingStdFeatureBuilder のユニットテスト."""

    def test_constant_data_zero_std(self):
        """定数データ → std=0."""
        builder = MovingStdFeatureBuilder(window=3)
        result = builder.build([5.0, 5.0, 5.0, 5.0])
        assert result[2, 0] == pytest.approx(0.0)
        assert result[3, 0] == pytest.approx(0.0)

    def test_padding_is_zero(self):
        """window 未満の先頭は 0 パディング."""
        builder = MovingStdFeatureBuilder(window=3)
        result = builder.build([10.0, 20.0, 30.0])
        assert result[0, 0] == 0.0
        assert result[1, 0] == 0.0

    def test_default_window_is_5(self):
        """デフォルト window=5."""
        builder = MovingStdFeatureBuilder()
        result = builder.build([1.0] * 6)
        assert result.shape == (6, 1)

    def test_known_std(self):
        """既知データで母集団標準偏差を検証."""
        builder = MovingStdFeatureBuilder(window=3)
        result = builder.build([10.0, 20.0, 30.0])
        expected = np.std([10.0, 20.0, 30.0])
        assert result[2, 0] == pytest.approx(expected)

    def test_empty_input(self):
        """空入力 → shape (0, 1)."""
        builder = MovingStdFeatureBuilder()
        result = builder.build([])
        assert result.shape == (0, 1)


class TestFeatureRegistry:
    """FEATURE_REGISTRY の検証."""

    def test_raw_work_time_registered(self):
        """'raw_work_time' がレジストリに存在."""
        assert "raw_work_time" in FEATURE_REGISTRY

    def test_registry_entry_has_builder(self):
        """エントリに builder クラスが含まれる."""
        entry = FEATURE_REGISTRY["raw_work_time"]
        assert entry["builder"] is RawWorkTimeFeatureBuilder

    def test_registry_entry_has_metadata(self):
        """エントリに label, description, params_schema."""
        entry = FEATURE_REGISTRY["raw_work_time"]
        assert isinstance(entry["label"], str)
        assert len(entry["label"]) > 0
        assert isinstance(entry["description"], str)
        assert len(entry["description"]) > 0
        assert isinstance(entry["params_schema"], dict)

    def test_all_adopted_features_registered(self):
        """採用された全特徴量が登録されている."""
        for key in ["raw_work_time", "diff", "moving_avg", "moving_std"]:
            assert key in FEATURE_REGISTRY

    def test_all_entries_have_metadata(self):
        """全エントリに必須メタデータがある."""
        for key, entry in FEATURE_REGISTRY.items():
            assert "builder" in entry, f"{key}: builder missing"
            assert isinstance(entry["label"], str)
            assert isinstance(entry["description"], str)
            assert isinstance(entry["params_schema"], dict)


class TestCreateFeatureBuilder:
    """create_feature_builder ファクトリのユニットテスト."""

    def test_empty_config_returns_raw_builder(self):
        """空の FeatureConfig → RawWorkTimeFeatureBuilder."""
        config = FeatureConfig(features=[])
        builder = create_feature_builder(config)
        assert isinstance(builder, RawWorkTimeFeatureBuilder)

    def test_single_spec_returns_direct_builder(self):
        """単一 FeatureSpec → RawWorkTimeFeatureBuilder."""
        config = FeatureConfig(
            features=[FeatureSpec(feature_type="raw_work_time")]
        )
        builder = create_feature_builder(config)
        assert isinstance(builder, RawWorkTimeFeatureBuilder)
        assert not isinstance(builder, CompositeFeatureBuilder)

    def test_multiple_specs_returns_composite(self):
        """複数 FeatureSpec → CompositeFeatureBuilder."""
        config = FeatureConfig(
            features=[
                FeatureSpec(feature_type="raw_work_time"),
                FeatureSpec(feature_type="raw_work_time"),
            ]
        )
        builder = create_feature_builder(config)
        assert isinstance(builder, CompositeFeatureBuilder)
        result = builder.build([10.0, 20.0])
        assert result.shape == (2, 2)

    def test_unknown_feature_type_raises(self):
        """未知の feature_type → ValueError."""
        config = FeatureConfig(
            features=[FeatureSpec(feature_type="nonexistent_feature")]
        )
        with pytest.raises(ValueError, match="Unknown feature type"):
            create_feature_builder(config)

    def test_diff_spec(self):
        """diff FeatureSpec → DiffFeatureBuilder."""
        config = FeatureConfig(features=[FeatureSpec(feature_type="diff")])
        builder = create_feature_builder(config)
        assert isinstance(builder, DiffFeatureBuilder)

    def test_composite_with_all_features(self):
        """raw + diff + moving_avg + moving_std → Composite, 4次元."""
        config = FeatureConfig(
            features=[
                FeatureSpec(feature_type="raw_work_time"),
                FeatureSpec(feature_type="diff"),
                FeatureSpec(feature_type="moving_avg"),
                FeatureSpec(feature_type="moving_std"),
            ]
        )
        builder = create_feature_builder(config)
        assert isinstance(builder, CompositeFeatureBuilder)
        result = builder.build([10.0, 20.0, 30.0, 40.0, 50.0])
        assert result.shape == (5, 4)


class TestFeatureSpecDataclass:
    """FeatureSpec / FeatureConfig dataclass のテスト."""

    def test_feature_spec_defaults(self):
        """FeatureSpec の params デフォルトは空dict."""
        spec = FeatureSpec(feature_type="raw_work_time")
        assert spec.feature_type == "raw_work_time"
        assert spec.params == {}

    def test_feature_spec_with_params(self):
        """FeatureSpec にパラメータ指定."""
        spec = FeatureSpec(feature_type="moving_avg", params={"window": 5})
        assert spec.params == {"window": 5}

    def test_feature_config_defaults(self):
        """FeatureConfig の features デフォルトは空リスト."""
        config = FeatureConfig()
        assert config.features == []

    def test_feature_spec_frozen(self):
        """FeatureSpec は frozen=True で変更不可."""
        spec = FeatureSpec(feature_type="raw_work_time")
        with pytest.raises(AttributeError):
            spec.feature_type = "other"

    def test_feature_config_frozen(self):
        """FeatureConfig は frozen=True で変更不可."""
        config = FeatureConfig()
        with pytest.raises(AttributeError):
            config.features = []
