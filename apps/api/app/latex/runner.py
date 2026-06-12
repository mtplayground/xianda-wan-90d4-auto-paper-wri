from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from app.config import Settings, get_settings

MAX_SOURCE_BUNDLE_BYTES = 5 * 1024 * 1024
MAX_CAPTURED_TEXT_CHARS = 80_000
TEX_ERROR_PATTERN = re.compile(r"^! .+$|^.+?:\d+: .+$", re.MULTILINE)


class TexLiveRunnerError(RuntimeError):
    pass


class TexLiveUnavailableError(TexLiveRunnerError):
    pass


class TexCompileInputError(TexLiveRunnerError, ValueError):
    pass


SourceBundle = dict[str, str | bytes]


@dataclass(frozen=True)
class TexCompileResult:
    success: bool
    pdf: bytes | None
    log: str
    stdout: str
    stderr: str
    errors: list[str] = field(default_factory=list)
    return_code: int | None = None
    timed_out: bool = False


@dataclass(frozen=True)
class _ValidatedBundle:
    files: dict[PurePosixPath, bytes]
    main_file: PurePosixPath


class TexLiveRunner:
    def __init__(
        self,
        *,
        command: str | None = None,
        timeout_seconds: int | None = None,
        max_runs: int | None = None,
        max_bundle_bytes: int = MAX_SOURCE_BUNDLE_BYTES,
        settings: Settings | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        self.command = command or resolved_settings.texlive_command
        self.timeout_seconds = (
            timeout_seconds or resolved_settings.texlive_timeout_seconds
        )
        self.max_runs = max_runs or resolved_settings.texlive_max_runs
        self.max_bundle_bytes = max_bundle_bytes
        if self.timeout_seconds < 1:
            raise TexCompileInputError("TeX Live timeout must be at least 1 second")
        if self.max_runs < 1:
            raise TexCompileInputError("TeX Live max runs must be at least 1")

    def compile(self, bundle: SourceBundle, *, main_file: str) -> TexCompileResult:
        validated = self._validate_bundle(bundle, main_file)
        executable = shutil.which(self.command)
        if executable is None:
            raise TexLiveUnavailableError(
                f"TeX Live command '{self.command}' was not found"
            )

        with TemporaryDirectory(prefix="texlive-") as temp_dir:
            work_dir = Path(temp_dir)
            self._write_bundle(work_dir, validated)
            return self._run_texlive(executable, work_dir, validated.main_file)

    def _run_texlive(
        self,
        executable: str,
        work_dir: Path,
        main_file: PurePosixPath,
    ) -> TexCompileResult:
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        return_code: int | None = None
        timed_out = False

        command = [
            executable,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            main_file.as_posix(),
        ]
        for _ in range(self.max_runs):
            try:
                completed = subprocess.run(
                    command,
                    cwd=work_dir,
                    capture_output=True,
                    check=False,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                stdout_parts.append(_decode_process_text(exc.stdout))
                stderr_parts.append(_decode_process_text(exc.stderr))
                timed_out = True
                break
            stdout_parts.append(_decode_process_text(completed.stdout))
            stderr_parts.append(_decode_process_text(completed.stderr))
            return_code = completed.returncode
            if completed.returncode != 0:
                break

        stdout = _clip_text("\n".join(part for part in stdout_parts if part))
        stderr = _clip_text("\n".join(part for part in stderr_parts if part))
        log = _clip_text(
            _read_first_text_file(_output_candidates(work_dir, main_file, ".log"))
            or stdout
        )
        pdf_path = _first_existing_path(_output_candidates(work_dir, main_file, ".pdf"))
        pdf = pdf_path.read_bytes() if pdf_path.exists() else None
        success = not timed_out and return_code == 0 and pdf is not None
        errors = _extract_errors(log, stderr)
        if timed_out:
            errors.insert(0, "TeX Live compilation timed out")
        elif return_code not in (0, None) and not errors:
            errors.append(f"TeX Live exited with status {return_code}")
        elif return_code == 0 and pdf is None:
            errors.append("TeX Live completed without producing a PDF")
        return TexCompileResult(
            success=success,
            pdf=pdf if success else None,
            log=log,
            stdout=stdout,
            stderr=stderr,
            errors=errors,
            return_code=return_code,
            timed_out=timed_out,
        )

    def _validate_bundle(
        self,
        bundle: SourceBundle,
        main_file: str,
    ) -> _ValidatedBundle:
        if not bundle:
            raise TexCompileInputError("Source bundle must include at least one file")
        main_path = _safe_relative_path(main_file)
        if main_path.suffix.lower() != ".tex":
            raise TexCompileInputError("Main TeX file must use a .tex extension")

        files: dict[PurePosixPath, bytes] = {}
        total_bytes = 0
        for raw_name, raw_content in bundle.items():
            path = _safe_relative_path(raw_name)
            if path in files:
                raise TexCompileInputError(f"Duplicate source file: {path.as_posix()}")
            if isinstance(raw_content, str):
                content = raw_content.encode("utf-8")
            else:
                content = bytes(raw_content)
            if not content:
                raise TexCompileInputError(f"Source file is empty: {path.as_posix()}")
            total_bytes += len(content)
            if total_bytes > self.max_bundle_bytes:
                raise TexCompileInputError("Source bundle is too large")
            files[path] = content

        if main_path not in files:
            raise TexCompileInputError("Main TeX file is missing from the bundle")
        return _ValidatedBundle(files=files, main_file=main_path)

    @staticmethod
    def _write_bundle(work_dir: Path, bundle: _ValidatedBundle) -> None:
        for relative_path, content in bundle.files.items():
            destination = work_dir / relative_path.as_posix()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)


def _safe_relative_path(path: str) -> PurePosixPath:
    stripped = path.strip().replace("\\", "/")
    if not stripped:
        raise TexCompileInputError("Source file path must not be blank")
    candidate = PurePosixPath(stripped)
    if candidate.is_absolute():
        raise TexCompileInputError("Source file path must be relative")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise TexCompileInputError("Source file path contains an invalid segment")
    return candidate


def _decode_process_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _clip_text(value: str) -> str:
    if len(value) <= MAX_CAPTURED_TEXT_CHARS:
        return value
    return value[-MAX_CAPTURED_TEXT_CHARS:]


def _output_candidates(
    work_dir: Path,
    main_file: PurePosixPath,
    suffix: str,
) -> list[Path]:
    base_name = f"{main_file.with_suffix('').name}{suffix}"
    nested_name = f"{main_file.with_suffix('').as_posix()}{suffix}"
    return [work_dir / base_name, work_dir / nested_name]


def _first_existing_path(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _read_first_text_file(paths: list[Path]) -> str:
    path = _first_existing_path(paths)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_errors(log: str, stderr: str) -> list[str]:
    combined = "\n".join(part for part in (log, stderr) if part)
    seen: set[str] = set()
    errors: list[str] = []
    for match in TEX_ERROR_PATTERN.finditer(combined):
        line = match.group(0).strip()
        if line and line not in seen:
            seen.add(line)
            errors.append(line)
    return errors[:20]
