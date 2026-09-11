"""`AisleConfig` as a value, and the lookups this layer reconciles.

Upstream's `category_for` is exact-match while its `common_name_for` is
case-insensitive and alias-aware, so the same ingredient could have a common
name and no category. These tests pin that the wrapper keeps the two in step,
and that a config behaves like the other model types: equal by content, and
pickled by re-parsing rather than by carrying a native pointer.
"""

from __future__ import annotations

import pickle

import pytest

import cooklang
from cooklang import AisleConfig

CONFIG = "[produce]\nonion|onions|brown onion\n\n[dairy]\nButter\n"


@pytest.fixture
def config() -> AisleConfig:
    return cooklang.parse_aisle_config(CONFIG)


class TestCategoryFor:
    @pytest.mark.parametrize("name", ["onion", "onions", "Onions", "Brown Onion"])
    def test_matches_like_common_name_for(self, config, name):
        assert config.category_for(name) == "produce"

    def test_case_differences_in_the_config_itself_resolve(self, config):
        assert config.category_for("butter") == "dairy"

    def test_unlisted_is_still_none(self, config):
        assert config.category_for("saffron") is None

    def test_group_by_category_no_longer_strands_a_capitalised_name(self, config):
        assert config.group_by_category(["Onions"]) == {"produce": ("Onions",)}


class TestAisleConfigIsAValue:
    def test_from_text_is_parse_aisle_config(self, config):
        assert AisleConfig.from_text(CONFIG) == config

    def test_constructor_takes_text(self, config):
        assert AisleConfig(CONFIG) == config

    def test_constructor_rejects_non_text(self):
        with pytest.raises(TypeError, match="text must be str"):
            AisleConfig(None)

    def test_equal_configs_hash_alike(self, config):
        assert hash(AisleConfig(CONFIG)) == hash(config)

    def test_different_configs_are_unequal(self, config):
        assert config != cooklang.parse_aisle_config("[produce]\nfennel\n")

    def test_pickle_round_trips_by_reparsing(self, config):
        copy = pickle.loads(pickle.dumps(config))

        assert copy == config
        assert copy.category_for("Onions") == "produce"
