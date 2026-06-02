# ── 版本号解析 ──
from gvc.parser import extract_version, extract_version_code, extract_both


class TestExtractVersion:
    """版本号提取测试."""

    def test_standard_version_in_class(self):
        html = '<div class="app-version">4.4.0</div>'
        assert extract_version(html) == "4.4.0"

    def test_version_in_data_attr(self):
        html = '<div data-dt-version="3.21.0">text</div>'
        assert extract_version(html) == "3.21.0"

    def test_version_with_v_prefix(self):
        # _is_version strips v/V prefix via normalize(), so result is clean
        html = '<span class="version-name">v2.5.1</span>'
        assert extract_version(html) == "2.5.1"

    def test_no_version_found(self):
        html = "<div><p>No version here</p></div>"
        assert extract_version(html) is None

    def test_version_in_text_fallback(self):
        html = "<p>Current Version: 1.8.3</p>"
        assert extract_version(html) == "1.8.3"

    def test_version_in_tag_fallback(self):
        html = '<span class="something">>1.2.3<</span>'
        assert extract_version(html) == "1.2.3"

    def test_version_code_extraction(self):
        html = '<span>variant code: 123456789</span>'
        assert extract_version_code(html) == "123456789"

    def test_version_code_in_parens(self):
        html = '<div>3.21.0 (1234567)</div>'
        assert extract_version_code(html) == "1234567"

    def test_version_code_not_present(self):
        html = "<div>No codes here</div>"
        assert extract_version_code(html) is None

    # ── 新增模式测试 ──

    def test_vc_meta_tag(self):
        """模式 4：<meta property="versionCode" content="NNN"/>"""
        html = '<meta property="versionCode" content="12345678"/>'
        assert extract_version_code(html) == "12345678"

    def test_vc_json_embedded(self):
        """模式 5：JSON 内嵌 "versionCode":"NNN" """
        html = '<script>{"versionCode": "9876543"}</script>'
        assert extract_version_code(html) == "9876543"

    def test_vc_text_label(self):
        """模式 6：纯文本 Version Code: NNN"""
        html = '<span>Version Code: 555666</span>'
        assert extract_version_code(html) == "555666"

    def test_vc_text_label_colon(self):
        """模式 6 中文冒号变体"""
        html = '<span>Version Code：777888</span>'
        assert extract_version_code(html) == "777888"

    def test_vc_data_app_attr(self):
        """模式 7：data-app-versioncode="NNN" """
        html = '<div data-app-versioncode="111222">text</div>'
        assert extract_version_code(html) == "111222"

    def test_vc_apk_filename(self):
        """模式 8：APK 文件名内嵌 code"""
        html = '<a href="app_12345678.apk">Download</a>'
        assert extract_version_code(html) == "12345678"

    def test_vc_definition_list(self):
        """模式 9：定义列表 <dt>Version Code</dt><dd>NNN</dd>"""
        html = "<dt>Version Code</dt><dd>999888</dd>"
        assert extract_version_code(html) == "999888"

    def test_vc_loose_fallback(self):
        """模式 10：宽松兜底 — version 附近的数字"""
        html = '<div>version: 12345678</div>'
        assert extract_version_code(html) == "12345678"

    def test_vc_short_code(self):
        """短 version code（3-5 位）也应被提取"""
        html = '<span>variant code: 123</span>'
        assert extract_version_code(html) == "123"


class TestExtractBoth:
    """合并提取测试."""

    def test_extracts_both_version_and_code(self):
        html = '<div class="app-version">4.4.0</div><span>variant code: 123456</span>'
        v, vc = extract_both(html)
        assert v == "4.4.0"
        assert vc == "123456"

    def test_extracts_only_version(self):
        html = '<div data-dt-version="3.21.0">text</div>'
        v, vc = extract_both(html)
        assert v == "3.21.0"
        assert vc is None

    def test_extracts_only_code(self):
        html = '<span>Version Code: 555666</span>'
        v, vc = extract_both(html)
        assert v is None
        assert vc == "555666"

    def test_extracts_nothing(self):
        html = "<div>No data</div>"
        v, vc = extract_both(html)
        assert v is None
        assert vc is None


# ── 版本号处理 ──
from gvc.version import normalize, parse_version_tuple, compare_versions, best_version
from gvc.models import GameResult, SourceResult


class TestNormalize:
    """版本号标准化."""

    def test_strips_v_prefix(self):
        assert normalize("v4.4.0") == "4.4.0"

    def test_replaces_spaces_with_dots(self):
        assert normalize("4 4 0") == "4.4.0"

    def test_handles_varies_with_device(self):
        assert normalize("Varies with device") == ""
        assert normalize("Varies") == ""

    def test_keeps_valid_version(self):
        assert normalize("4.4.0") == "4.4.0"


class TestCompareVersions:
    """版本号比较."""

    def test_equal_versions(self):
        assert compare_versions("4.4.0", "4.4.0") == 0

    def test_major_upgrade(self):
        assert compare_versions("5.0.0", "4.9.9") == 1

    def test_patch_upgrade(self):
        assert compare_versions("4.4.1", "4.4.0") == 1

    def test_two_part_version(self):
        assert compare_versions("4.5", "4.4.9") == 1

    def test_downgrade(self):
        assert compare_versions("3.0", "4.0") == -1


class TestBestVersion:
    """最佳版本判定."""

    def test_consensus_two_sources(self):
        r = GameResult(package="com.test")
        r.google = SourceResult(version="4.4.0")
        r.apkpure = SourceResult(version="4.4.0")
        r.apkcombo = SourceResult(version="4.3.0")
        assert best_version(r) == "4.4.0"

    def test_single_source(self):
        r = GameResult(package="com.test")
        r.google = SourceResult(version="4.4.0")
        assert best_version(r) == "4.4.0"

    def test_no_consensus_prefer_google(self):
        r = GameResult(package="com.test")
        r.google = SourceResult(version="4.4.0")
        r.apkpure = SourceResult(version="4.4.1")
        r.apkcombo = SourceResult(version="5.0.0")
        assert best_version(r) == "4.4.0"  # Google Play preferred

    def test_no_results(self):
        r = GameResult(package="com.test")
        assert best_version(r) == "无法获取"


# ── 版本号比较 ──
from gvc.version import compare_version_codes, best_version_code as _best_vc_func


class TestCompareVersionCodes:
    """版本号整数比较."""

    def test_equal(self):
        assert compare_version_codes("12345", "12345") == 0

    def test_newer(self):
        assert compare_version_codes("12346", "12345") == 1

    def test_older(self):
        assert compare_version_codes("12344", "12345") == -1

    def test_invalid_returns_none(self):
        assert compare_version_codes("abc", "123") is None

    def test_int_args(self):
        assert compare_version_codes(200, 100) == 1

    def test_mixed_types(self):
        assert compare_version_codes("200", 100) == 1


class TestBestVersionCode:
    """最佳 version code 判定."""

    def test_consensus_two_sources(self):
        r = GameResult(package="com.test")
        r.apkpure = SourceResult(version="4.4.0", version_code="100")
        r.apkcombo = SourceResult(version="4.4.0", version_code="100")
        r.apkvision = SourceResult(version="4.3.0", version_code="99")
        assert _best_vc_func(r) == "100"

    def test_single_source(self):
        r = GameResult(package="com.test")
        r.apkpure = SourceResult(version_code="200")
        assert _best_vc_func(r) == "200"

    def test_no_consensus_picks_highest_int(self):
        r = GameResult(package="com.test")
        r.apkpure = SourceResult(version_code="100")
        r.apkcombo = SourceResult(version_code="200")
        r.apkvision = SourceResult(version_code="150")
        assert _best_vc_func(r) == "200"

    def test_no_codes_returns_empty(self):
        r = GameResult(package="com.test")
        r.google = SourceResult(version="4.4.0")
        assert _best_vc_func(r) == ""


# ── 对比逻辑（excel_handler） ──
from gvc.excel_handler import build_result_text


class TestBuildResultText:
    """build_result_text 版本号优先对比."""

    def test_vc_update_detected(self):
        r = GameResult(package="com.test", current_backend_version_code="100")
        r.apkpure = SourceResult(version="4.5.0", version_code="200")
        text = build_result_text(r)
        assert r.has_update is True
        assert "vc:100→200" in text

    def test_vc_no_change(self):
        r = GameResult(
            package="com.test",
            current_backend_version="4.4.0",
            current_backend_version_code="100",
        )
        r.apkpure = SourceResult(version="4.4.0", version_code="100")
        text = build_result_text(r)
        assert r.has_update is False
        assert text == "-"

    def test_fallback_to_name_when_no_vc(self):
        r = GameResult(
            package="com.test",
            current_backend_version="4.4.0",
            current_backend_version_code="",
        )
        r.google = SourceResult(version="4.5.0")
        text = build_result_text(r)
        assert r.has_update is True
        assert "4.4.0→4.5.0" in text

    def test_no_results_returns_fail(self):
        r = GameResult(package="com.test")
        text = build_result_text(r)
        assert text == "获取失败"
        assert r.has_update is False

    def test_vc_update_name_unchanged(self):
        """版本号变了但版本名不变."""
        r = GameResult(
            package="com.test",
            current_backend_version="4.4.0",
            current_backend_version_code="100",
        )
        r.apkpure = SourceResult(version="4.4.0", version_code="200")
        text = build_result_text(r)
        assert r.has_update is True
        assert "vc:100→200" in text
        assert "4.4.0→4.4.0" not in text  # 版本名相同不额外展示


# ── 数据结构 ──
class TestModels:
    """模型测试."""

    def test_source_result_ok(self):
        s = SourceResult(version="4.4.0")
        assert s.ok is True

    def test_source_result_error(self):
        s = SourceResult(error="Not found")
        assert s.ok is False

    def test_game_result_all_versions(self):
        r = GameResult(package="com.test")
        r.google = SourceResult(version="1.0")
        r.apkpure = SourceResult(version="2.0")
        assert r.all_versions == ["1.0", "2.0"]

    def test_best_version_code(self):
        r = GameResult(package="com.test")
        r.apkpure = SourceResult(version_code="12345678")
        assert r.best_version_code == "12345678"

    def test_all_version_codes(self):
        r = GameResult(package="com.test")
        r.apkpure = SourceResult(version_code="100")
        r.apkcombo = SourceResult(version_code="200")
        assert r.all_version_codes == ["100", "200"]

    def test_current_backend_version_code_default(self):
        r = GameResult(package="com.test")
        assert r.current_backend_version_code == ""


# ── 下载器 ──
from gvc.downloader import detect_arch, detect_installed_managers, get_download_manager


class TestDetectArch:
    """APK 架构检测."""

    def test_arm64_v8a_exact(self):
        assert detect_arch("app_arm64-v8a.apk") == "arm64-v8a"

    def test_arm64_generic(self):
        assert detect_arch("app_arm64.apk") == "arm64-v8a"

    def test_aarch64(self):
        assert detect_arch("app-aarch64-release.apk") == "arm64-v8a"

    def test_armeabi_v7a(self):
        assert detect_arch("app_armeabi-v7a.apk") == "armeabi-v7a"

    def test_armeabi_generic(self):
        assert detect_arch("app_armeabi.apk") == "armeabi-v7a"

    def test_universal(self):
        assert detect_arch("app_universal.apk") == "universal"

    def test_nodpi(self):
        assert detect_arch("app_nodpi.apk") == "universal"

    def test_unknown(self):
        assert detect_arch("app-release.apk") == "unknown"

    def test_case_insensitive(self):
        assert detect_arch("App_ARM64-V8A_release.apk") == "arm64-v8a"

    def test_from_page_label(self):
        assert detect_arch("CPU: arm64-v8a + armeabi-v7a") == "arm64-v8a"


class TestDownloadManagerDetection:
    """下载管理器检测."""

    def test_detect_returns_list(self):
        managers = detect_installed_managers()
        assert isinstance(managers, list)

    def test_get_auto_returns_none_or_manager(self):
        dm = get_download_manager()
        assert dm is None or hasattr(dm, "name")

    def test_get_nonexistent(self):
        dm = get_download_manager("nonexistent_manager_xyz")
        # 可能返回 None 或自动回退
        assert dm is None or hasattr(dm, "name")
