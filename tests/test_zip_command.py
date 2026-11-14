import zipfile
from pathlib import Path

from commands.custom_commands import ZipCommand
from core.context import ShellContext


def _context(tmp_path: Path) -> ShellContext:
    return ShellContext(cwd=tmp_path)


def test_zip_creates_a_verified_archive_without_partial_final_file(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("hello", encoding="utf-8")
    (source / "empty").mkdir()
    destination = tmp_path / "release.zip"

    result = ZipCommand().execute(_context(tmp_path), ["source", "release.zip"])

    assert result.success
    assert destination.is_file()
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert archive.read("hello.txt") == b"hello"
        assert "empty/" in archive.namelist()


def test_zip_refuses_an_archive_inside_its_source_folder(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("hello", encoding="utf-8")

    result = ZipCommand().execute(_context(tmp_path), ["source", "source/archive.zip"])

    assert not result.success
    assert "outside" in result.output
    assert not (source / "archive.zip").exists()


def test_zip_cancel_keeps_an_existing_archive_untouched(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("hello", encoding="utf-8")
    destination = tmp_path / "release.zip"
    destination.write_bytes(b"previous archive")
    context = _context(tmp_path)
    context.cancel_event.set()

    result = ZipCommand().execute(context, ["source", "release.zip"])

    assert not result.success
    assert destination.read_bytes() == b"previous archive"
