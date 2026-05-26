"""Tests fonctionnels de la Plugin API Pro.

On teste :
  - BasePlugin no-op par défaut
  - PluginManager.register / list / clear
  - Découverte d'un plugin via un dossier ``plugins/`` factice
  - Refus des doublons
  - Invocation des hooks dans l'ordre + résilience aux exceptions
  - Plugin exemple ``geotag_renamer``
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# -----------------------------------------------------------------------
# DEFERRED v3.0+ — pivot économique 2026-05-26
# Le module testé est gelé : Plugin API non exposée dans l'app v2.x.
# On garde le fichier intact pour réactivation conditionnelle.
# Cf. AUDIT.md §15 et docs/MONETIZATION.md §8.
# -----------------------------------------------------------------------
pytestmark = pytest.mark.skip(reason="Deferred to v3.0+ (see AUDIT.md §15)")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.photoorganizer_pro.plugins import (  # noqa: E402
    BasePlugin,
    OrganizeContext,
    PluginAction,
    PluginManager,
    get_plugin_manager,
)
from src.photoorganizer_pro.plugins.examples.geotag_renamer import (  # noqa: E402
    GeotagRenamerPlugin,
    _slug_from_coords,
)
from src.photoorganizer_pro.plugins.manager import reset_plugin_manager  # noqa: E402


# ---------------------------------------------------------------------
# BasePlugin : valeurs par défaut
# ---------------------------------------------------------------------
class TestBasePlugin:
    def test_filter_default_accepts_all(self):
        p = BasePlugin()
        ctx = OrganizeContext(source_dir=Path("."), target_dir=Path("."))
        assert p.filter_file(Path("x.jpg"), {}, ctx) is True

    def test_rename_default_returns_none(self):
        p = BasePlugin()
        ctx = OrganizeContext(source_dir=Path("."), target_dir=Path("."))
        assert p.rename(Path("x.jpg"), {}, "proposed.jpg", ctx) is None

    def test_pre_post_organize_dont_raise(self):
        p = BasePlugin()
        ctx = OrganizeContext(source_dir=Path("."), target_dir=Path("."))
        p.pre_organize(ctx)
        p.post_organize(ctx)
        p.post_action(Path("a"), Path("b"), PluginAction.COPY, ctx)

    def test_describe_default(self):
        p = BasePlugin()
        assert "unnamed" in p.describe()


# ---------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------
class _NoopPlugin(BasePlugin):
    name = "noop"
    version = "1.0.0"


class _RecordingPlugin(BasePlugin):
    name = "recorder"
    version = "1.0.0"

    def __init__(self):
        self.calls = []

    def pre_organize(self, context):
        self.calls.append(("pre_organize",))

    def filter_file(self, path, metadata, context):
        self.calls.append(("filter_file", path.name))
        return True

    def rename(self, path, metadata, proposed_name, context):
        self.calls.append(("rename", proposed_name))
        return f"recorded_{proposed_name}"

    def post_action(self, source, destination, action, context):
        self.calls.append(("post_action", action.value))

    def post_organize(self, context):
        self.calls.append(("post_organize",))


class _ExplodingPlugin(BasePlugin):
    name = "boom"
    version = "1.0.0"

    def pre_organize(self, context):
        raise RuntimeError("boom in pre_organize")

    def filter_file(self, path, metadata, context):
        raise RuntimeError("boom in filter")

    def rename(self, path, metadata, proposed_name, context):
        raise RuntimeError("boom in rename")

    def post_action(self, source, destination, action, context):
        raise RuntimeError("boom in post_action")


class _RejectAllPlugin(BasePlugin):
    name = "rejector"
    version = "1.0.0"

    def filter_file(self, path, metadata, context):
        return False


class TestPluginManager:
    def test_register_and_list(self):
        m = PluginManager()
        m.register(_NoopPlugin())
        assert len(m.list_plugins()) == 1
        assert m.list_plugins()[0].name == "noop"

    def test_register_rejects_non_plugin(self):
        m = PluginManager()
        with pytest.raises(TypeError):
            m.register("not a plugin")  # type: ignore[arg-type]

    def test_register_dedupe_by_name(self):
        m = PluginManager()
        m.register(_NoopPlugin())
        m.register(_NoopPlugin())  # même name → ignoré
        assert len(m.list_plugins()) == 1

    def test_clear(self):
        m = PluginManager()
        m.register(_NoopPlugin())
        m.clear()
        assert m.list_plugins() == []

    # -----------------------------------------------------------------
    # Invocation de hooks
    # -----------------------------------------------------------------
    def _make_ctx(self) -> OrganizeContext:
        return OrganizeContext(source_dir=Path("src"), target_dir=Path("dest"))

    def test_call_filter_file_all_accept(self):
        m = PluginManager()
        m.register(_NoopPlugin())
        m.register(_RecordingPlugin())
        ctx = self._make_ctx()
        assert m.call_filter_file(Path("x.jpg"), {}, ctx) is True

    def test_call_filter_file_one_rejects(self):
        m = PluginManager()
        m.register(_RecordingPlugin())
        m.register(_RejectAllPlugin())
        ctx = self._make_ctx()
        assert m.call_filter_file(Path("x.jpg"), {}, ctx) is False

    def test_call_rename_chains_plugins(self):
        """Si un plugin renomme, le suivant reçoit le nom renommé."""

        class _PrefixA(BasePlugin):
            name = "prefix_a"

            def rename(self, path, metadata, proposed_name, context):
                return f"A_{proposed_name}"

        class _PrefixB(BasePlugin):
            name = "prefix_b"

            def rename(self, path, metadata, proposed_name, context):
                return f"B_{proposed_name}"

        m = PluginManager()
        m.register(_PrefixA())
        m.register(_PrefixB())
        ctx = self._make_ctx()
        result = m.call_rename(Path("x.jpg"), {}, "img.jpg", ctx)
        # A puis B → B_A_img.jpg
        assert result == "B_A_img.jpg"

    def test_call_rename_none_preserves_previous(self):
        m = PluginManager()
        m.register(_NoopPlugin())  # rename retourne None par défaut
        ctx = self._make_ctx()
        assert m.call_rename(Path("x.jpg"), {}, "img.jpg", ctx) == "img.jpg"

    def test_exception_in_one_plugin_does_not_break_others(self):
        m = PluginManager()
        rec = _RecordingPlugin()
        m.register(rec)
        m.register(_ExplodingPlugin())
        ctx = self._make_ctx()
        # Aucune exception ne doit remonter, et le recorder doit
        # avoir été invoqué (sur ses propres hooks).
        m.call_pre_organize(ctx)
        m.call_post_action(Path("a"), Path("b"), PluginAction.COPY, ctx)
        # filter_file : le plugin qui explose ne doit pas masquer le True
        assert m.call_filter_file(Path("x"), {}, ctx) is True
        assert ("pre_organize",) in rec.calls

    # -----------------------------------------------------------------
    # Découverte via dossier
    # -----------------------------------------------------------------
    def test_discover_user_plugins_loads_subclass(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "my_plugin.py").write_text(
            "from src.photoorganizer_pro.plugins import BasePlugin\n"
            "class MyTestPlugin(BasePlugin):\n"
            "    name = 'my_test'\n"
            "    version = '0.1.0'\n",
            encoding="utf-8",
        )
        m = PluginManager()
        count = m.discover_user_plugins(plugins_dir=plugin_dir)
        assert count == 1
        assert m.list_plugins()[0].name == "my_test"

    def test_discover_user_plugins_skips_underscore(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "_private.py").write_text(
            "from src.photoorganizer_pro.plugins import BasePlugin\n"
            "class PrivatePlugin(BasePlugin):\n"
            "    name = 'private'\n",
            encoding="utf-8",
        )
        m = PluginManager()
        assert m.discover_user_plugins(plugins_dir=plugin_dir) == 0

    def test_discover_user_plugins_handles_missing_dir(self, tmp_path):
        m = PluginManager()
        # Dossier inexistant → 0, pas d'erreur
        assert m.discover_user_plugins(plugins_dir=tmp_path / "nope") == 0


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------
class TestSingleton:
    def setup_method(self):
        reset_plugin_manager()

    def teardown_method(self):
        reset_plugin_manager()

    def test_get_returns_same_instance(self):
        m1 = get_plugin_manager()
        m2 = get_plugin_manager()
        assert m1 is m2

    def test_reset(self):
        m1 = get_plugin_manager()
        reset_plugin_manager()
        m2 = get_plugin_manager()
        assert m1 is not m2


# ---------------------------------------------------------------------
# Plugin exemple : geotag_renamer
# ---------------------------------------------------------------------
class TestGeotagRenamerExample:
    def _ctx(self):
        return OrganizeContext(source_dir=Path("."), target_dir=Path("."))

    def test_slug_from_coords_paris(self):
        assert _slug_from_coords(48.85, 2.35) == "48N002E"

    def test_slug_from_coords_sydney(self):
        assert _slug_from_coords(-33.87, 151.21) == "33S151E"

    def test_slug_from_coords_la(self):
        assert _slug_from_coords(34.05, -118.24) == "34N118W"

    def test_rename_with_gps_prefixes(self):
        p = GeotagRenamerPlugin()
        ctx = self._ctx()
        p.pre_organize(ctx)
        result = p.rename(
            Path("IMG_4567.jpg"),
            {"GPSLatitude": 48.85, "GPSLongitude": 2.35},
            "IMG_4567.jpg",
            ctx,
        )
        assert result == "48N002E_IMG_4567.jpg"
        assert ctx.state["geotag_renamer"]["renamed"] == 1

    def test_rename_without_gps_returns_none(self):
        p = GeotagRenamerPlugin()
        ctx = self._ctx()
        p.pre_organize(ctx)
        result = p.rename(Path("IMG.jpg"), {}, "IMG.jpg", ctx)
        assert result is None
        assert ctx.state["geotag_renamer"]["skipped"] == 1

    def test_rename_already_prefixed_returns_none(self):
        p = GeotagRenamerPlugin()
        ctx = self._ctx()
        p.pre_organize(ctx)
        # Déjà préfixé : ne pas re-préfixer
        result = p.rename(
            Path("IMG.jpg"),
            {"GPSLatitude": 48.85, "GPSLongitude": 2.35},
            "48N002E_IMG.jpg",
            ctx,
        )
        assert result is None

    def test_post_organize_logs_summary(self, caplog):
        p = GeotagRenamerPlugin()
        ctx = self._ctx()
        p.pre_organize(ctx)
        ctx.state["geotag_renamer"]["renamed"] = 3
        ctx.state["geotag_renamer"]["skipped"] = 2
        # Le test vérifie juste que la méthode ne lève pas.
        p.post_organize(ctx)
