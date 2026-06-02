"""数据结构定义."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceResult:
    """单个数据源的查询结果."""

    version: str | None = None
    version_code: str | None = None
    updated_ts: int | None = None
    error: str | None = None
    detail_url: str | None = None       # 指向详情/下载页的 URL（用于后续下载）
    download_urls: list[str] = field(default_factory=list)  # APK 直链列表

    @property
    def ok(self) -> bool:
        return bool(self.version) and self.error is None


@dataclass
class GameResult:
    """单个游戏的综合排查结果."""

    package: str
    name: str = ""
    google: SourceResult = field(default_factory=SourceResult)
    apkpure: SourceResult = field(default_factory=SourceResult)
    apkcombo: SourceResult = field(default_factory=SourceResult)
    apkvision: SourceResult = field(default_factory=SourceResult)
    apkmirror: SourceResult = field(default_factory=SourceResult)
    apkdl: SourceResult = field(default_factory=SourceResult)
    current_backend_version: str = ""
    current_backend_version_code: str = ""
    has_update: bool = False
    update_detail: str = ""

    @property
    def all_versions(self) -> list[str]:
        """返回所有非空版本号列表."""
        return [
            v
            for v in (
                self.google.version,
                self.apkpure.version,
                self.apkcombo.version,
                self.apkvision.version,
                self.apkmirror.version,
                self.apkdl.version,
            )
            if v
        ]

    @property
    def all_version_codes(self) -> list[str]:
        """返回所有非空 version_code 列表."""
        return [
            vc
            for vc in (
                self.google.version_code,
                self.apkpure.version_code,
                self.apkcombo.version_code,
                self.apkvision.version_code,
                self.apkmirror.version_code,
                self.apkdl.version_code,
            )
            if vc
        ]

    @property
    def best_version_code(self) -> str | None:
        """返回第一个可用的 version_code."""
        for s in (self.google, self.apkpure, self.apkcombo, self.apkvision, self.apkmirror, self.apkdl):
            if s.version_code:
                return s.version_code
        return None

    @staticmethod
    def from_source_results(
        package: str,
        source_results: dict[str, SourceResult],
        *,
        name: str = "",
        current_version: str = "",
        current_version_code: str = "",
    ) -> GameResult:
        """从 query_all_sources() 返回的字典构造 GameResult."""
        return GameResult(
            package=package,
            name=name,
            current_backend_version=current_version,
            current_backend_version_code=current_version_code,
            google=source_results.get("Google Play", SourceResult()),
            apkpure=source_results.get("APKPure", SourceResult()),
            apkcombo=source_results.get("APKCombo", SourceResult()),
            apkvision=source_results.get("APKVision", SourceResult()),
            apkmirror=source_results.get("APKMirror", SourceResult()),
            apkdl=source_results.get("APKDL", SourceResult()),
        )
