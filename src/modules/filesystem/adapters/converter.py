"""
Converter.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Converter
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import json
import csv
import io

from src.core import ApiError

HAS_PANDAS = False
HAS_PYYAML = False
HAS_PIL = False
HAS_CHARDET = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pass

try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    pass

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    pass

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    pass

SUPPORTED_FORMATS = {
    "data": ["csv", "json", "xlsx", "xml", "yaml"],
    "image": ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"],
    "encoding": ["utf-8", "utf-16", "utf-16le", "utf-16be", "ascii", "latin-1", "cp1252"],
}

IMAGE_FORMAT_MAP = {
    "jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WebP",
    "bmp": "BMP", "tiff": "TIFF", "tif": "TIFF", "gif": "GIF",
}


def _detect_format(path: str, fmt: Optional[str], convert_type: str) -> Optional[str]:
    if fmt:
        return fmt.lower().replace("jpg", "jpeg")
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    if ext in SUPPORTED_FORMATS.get(convert_type, []):
        return ext
    return None


from src.core.utils.path import norm_path as _norm


class DiskConverter:
    """File converter: data (CSV/JSON/XLSX/XML/YAML), image (PIL), encoding."""

    @classmethod
    def convert(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        convert_type = params.get("convert_type", "")
        source_path = params.get("source_path", "")
        source_content = params.get("source_content")
        source_format = params.get("source_format")
        target_path = params.get("target_path", "")
        target_format = params.get("target_format")
        options = params.get("options") or {}
        overwrite = params.get("overwrite", False)
        dry_run = params.get("dry_run", False)

        if not target_path:
            raise ApiError("target_path is required", status_code=400, error_code="FS_004")
        if not source_path and not source_content:
            raise ApiError("Either source_path or source_content is required", status_code=400, error_code="FS_004")

        target_path_obj = Path(target_path).resolve()

        if not overwrite and target_path_obj.exists():
            raise ApiError(f"Target already exists: {target_path}", status_code=409, error_code="FS_004")

        sf = _detect_format(source_path, source_format, convert_type) if source_path else (source_format or "").lower()
        tf = _detect_format(target_path, target_format, convert_type)

        if convert_type == "data":
            return cls._convert_data(source_path, source_content, sf, target_path, tf, options, dry_run)
        elif convert_type == "image":
            return cls._convert_image(source_path, sf, target_path, tf, options, dry_run)
        elif convert_type == "encoding":
            return cls._convert_encoding(source_path, target_path, options, dry_run)
        else:
            raise ApiError(
                f"Unknown convert_type: {convert_type}. Use 'data', 'image', or 'encoding'.",
                status_code=400,
                error_code="FS_004",
                details={"supported_types": ["data", "image", "encoding"]},
            )

    # ---- DATA CONVERSION ----

    @classmethod
    def _convert_data(cls, source_path: str, source_content: Optional[str],
                      source_format: Optional[str], target_path: str,
                      target_format: Optional[str], options: Dict[str, Any],
                      dry_run: bool) -> Dict[str, Any]:

        if not source_format or not target_format:
            raise ApiError(
                "Could not detect source or target format",
                status_code=400,
                error_code="FS_004",
                details={"supported": SUPPORTED_FORMATS["data"]},
            )

        if source_format not in SUPPORTED_FORMATS["data"] or target_format not in SUPPORTED_FORMATS["data"]:
            raise ApiError(
                f"Unsupported data conversion: from '{source_format}' to '{target_format}'",
                status_code=400,
                error_code="FS_004",
                details={"supported_formats": SUPPORTED_FORMATS["data"]},
            )

        if dry_run:
            dry_data: Dict[str, Any] = {
                "status_code": 200,
                "message": f"DRY RUN: would convert {source_format} to {target_format}",
                "data": {"source_format": source_format, "target_format": target_format},
            }
            if source_path and source_format in ("csv", "json", "xlsx"):
                try:
                    if source_format == "csv":
                        with open(source_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        dry_data["data"]["estimated_rows"] = len(lines)
                        dry_data["data"]["estimated_columns"] = len(lines[0].split(",")) if lines else 0
                    elif source_format == "json":
                        with open(source_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        dry_data["data"]["estimated_rows"] = len(data) if isinstance(data, list) else 1
                        dry_data["data"]["estimated_columns"] = len(data[0]) if isinstance(data, list) and data else len(data)
                    elif source_format == "xlsx" and HAS_PANDAS:
                        df = pd.read_excel(source_path, nrows=0)
                        dry_data["data"]["estimated_rows"] = 0
                        dry_data["data"]["estimated_columns"] = len(df.columns)
                except Exception:
                    pass
            return dry_data

        if HAS_PANDAS:
            return cls._convert_data_pandas(source_path, source_content, source_format, target_path, target_format, options)
        else:
            return cls._convert_data_fallback(source_path, source_content, source_format, target_path, target_format, options)

    @classmethod
    def _convert_data_pandas(cls, source_path: str, source_content: Optional[str],
                              source_format: str, target_path: str,
                              target_format: str, options: Dict[str, Any]) -> Dict[str, Any]:
        try:
            delim = options.get("delimiter", ",")
            encoding = options.get("encoding", "utf-8")
            sheet_name = options.get("sheet_name", "Sheet1")
            has_header = options.get("has_header", True)
            json_orient = options.get("json_orient", "records")
            xml_root = options.get("xml_root", "root")

            if source_content:
                if source_format == "json":
                    df = pd.DataFrame(json.loads(source_content))
                elif source_format == "csv":
                    df = pd.read_csv(io.StringIO(source_content), delimiter=delim, header=0 if has_header else None, encoding=encoding)
                elif source_format == "yaml" and HAS_PYYAML:
                    data = yaml.safe_load(source_content)
                    df = pd.DataFrame(data)
                else:
                    raise ApiError(
                        f"Unsupported inline source format: {source_format}. Supported: json, csv, yaml.",
                        status_code=400,
                        error_code="FS_004",
                    )
            else:
                if source_format == "csv":
                    df = pd.read_csv(source_path, delimiter=delim, header=0 if has_header else None, encoding=encoding)
                elif source_format == "json":
                    df = pd.read_json(source_path, orient=json_orient)
                elif source_format == "xlsx":
                    df = pd.read_excel(source_path, sheet_name=sheet_name, header=0 if has_header else None)
                elif source_format == "yaml" and HAS_PYYAML:
                    with open(source_path, encoding=encoding) as f:
                        data = yaml.safe_load(f)
                    df = pd.DataFrame(data)
                elif source_format == "xml":
                    df = pd.read_xml(source_path, encoding=encoding)
                else:
                    raise ApiError(f"Unsupported source format: {source_format}", status_code=400, error_code="FS_004")

            if target_format == "csv":
                df.to_csv(target_path, index=False, header=has_header, encoding=encoding)
            elif target_format == "json":
                df.to_json(target_path, orient=json_orient, indent=2, force_ascii=False)
            elif target_format == "xlsx":
                df.to_excel(target_path, sheet_name=sheet_name, index=False)
            elif target_format == "yaml" and HAS_PYYAML:
                with open(target_path, "w", encoding=encoding) as f:
                    yaml.dump(df.to_dict(orient="records"), f, allow_unicode=True, default_flow_style=False)
            elif target_format == "xml":
                df.to_xml(target_path, root_name=xml_root, encoding=encoding)
            else:
                raise ApiError(f"Unsupported target format: {target_format}", status_code=400, error_code="FS_004")

            rows, cols = df.shape
            tgt_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
            src_size = os.path.getsize(source_path) if source_path else 0
            compression_ratio = round(src_size / tgt_size, 2) if tgt_size and src_size else None
            return {
                "status_code": 200,
                "message": f"Converted {source_format.upper()} to {target_format.upper()}",
                "data": {
                    "source_format": source_format, "target_format": target_format,
                    "source": _norm(source_path) if source_path else "inline",
                    "target": _norm(target_path),
                    "stats": {
                        "rows": int(rows), "columns": int(cols), "source_size_bytes": src_size,
                        "target_size_bytes": tgt_size,
                        "compression_ratio": compression_ratio,
                    },
                },
            }
        except ImportError as e:
            raise ApiError(
                f"Missing dependency: {e.name}. Install with: pip install {e.name}",
                status_code=500,
                error_code="FS_004",
            )
        except Exception as e:
            raise ApiError(f"Conversion failed: {e}", status_code=500, error_code="FS_004")

    @classmethod
    def _convert_data_fallback(cls, source_path: str, source_content: Optional[str],
                                source_format: str, target_path: str,
                                target_format: str, options: Dict[str, Any]) -> Dict[str, Any]:
        try:
            encoding = options.get("encoding", "utf-8")
            delim = options.get("delimiter", ",")
            has_header = options.get("has_header", True)

            if source_content:
                raw = source_content
            else:
                with open(source_path, "r", encoding=encoding) as f:
                    raw = f.read()

            if source_format == "json":
                data = json.loads(raw)
            elif source_format == "csv" and target_format == "json":
                lines = raw.strip().splitlines()
                reader = csv.DictReader(lines, delimiter=delim)
                data = list(reader)
            elif source_format == "yaml" and HAS_PYYAML:
                data = yaml.safe_load(raw)
            else:
                raise ApiError(
                    f"Fallback mode: cannot read {source_format}. Install pandas for full support.",
                    status_code=400,
                    error_code="FS_004",
                )

            if target_format == "json":
                out = json.dumps(data, indent=2, ensure_ascii=False)
            elif target_format == "csv":
                if isinstance(data, list) and data:
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=delim)
                    if has_header:
                        writer.writeheader()
                    writer.writerows(data)
                    out = output.getvalue()
                else:
                    raise ApiError("Cannot convert: data is not a list of objects", status_code=400, error_code="FS_004")
            elif target_format == "yaml" and HAS_PYYAML:
                out = yaml.dump(data, allow_unicode=True, default_flow_style=False)
            else:
                raise ApiError(
                    f"Fallback mode: cannot write {target_format}. Install pandas for full support.",
                    status_code=400,
                    error_code="FS_004",
                )

            with open(target_path, "w", encoding=encoding) as f:
                f.write(out)

            tgt_size = os.path.getsize(target_path)
            rows = len(data) if isinstance(data, list) else 1
            cols = len(data[0]) if isinstance(data, list) and data else 0

            return {
                "status_code": 200,
                "message": f"Converted {source_format.upper()} to {target_format.upper()} (fallback)",
                "data": {
                    "source_format": source_format, "target_format": target_format,
                    "source": _norm(source_path) if source_path else "inline",
                    "target": _norm(target_path),
                    "stats": {"rows": rows, "columns": cols, "target_size_bytes": tgt_size},
                },
            }
        except Exception as e:
            raise ApiError(f"Fallback conversion failed: {e}", status_code=500, error_code="FS_004")

    # ---- IMAGE CONVERSION ----

    @classmethod
    def _convert_image(cls, source_path: str, source_format: Optional[str],
                        target_path: str, target_format: Optional[str],
                        options: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        if not HAS_PIL:
            raise ApiError("Pillow (PIL) is required for image conversion. Install: pip install Pillow", status_code=500, error_code="FS_004")
        if not source_path:
            raise ApiError("source_path is required for image conversion", status_code=400, error_code="FS_004")
        if not source_format or not target_format:
            raise ApiError(
                "Could not detect source or target image format",
                status_code=400,
                error_code="FS_004",
                details={"supported": SUPPORTED_FORMATS["image"]},
            )

        src_pil = IMAGE_FORMAT_MAP.get(source_format)
        tgt_pil = IMAGE_FORMAT_MAP.get(target_format)
        if not src_pil or not tgt_pil:
            raise ApiError(
                f"Unsupported image conversion: from '{source_format}' to '{target_format}'",
                status_code=400,
                error_code="FS_004",
                details={"supported_formats": SUPPORTED_FORMATS["image"]},
            )

        if dry_run:
            return {
                "status_code": 200,
                "message": f"DRY RUN: would convert {source_format} to {target_format}",
                "data": {"source_format": source_format, "target_format": target_format},
            }

        try:
            img = Image.open(source_path)
            orig_size = os.path.getsize(source_path)
            orig_w, orig_h = img.size

            width = options.get("width")
            height = options.get("height")
            quality = options.get("quality", 85)
            bg = options.get("background")
            preserve_ratio = options.get("preserve_ratio", True)

            new_w, new_h = orig_w, orig_h
            if width or height:
                if preserve_ratio:
                    ratio = orig_w / orig_h
                    if width and height:
                        new_w, new_h = width, height
                    elif width:
                        new_w = width
                        new_h = int(width / ratio)
                    elif height:
                        new_h = height
                        new_w = int(height * ratio)
                else:
                    new_w = width or orig_w
                    new_h = height or orig_h
                img = img.resize((new_w, new_h), Image.LANCZOS)

            if img.mode == "RGBA" and tgt_pil in ("JPEG",):
                if bg:
                    background = Image.new("RGB", img.size, bg)
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert("RGB")

            save_kwargs: Dict[str, Any] = {}
            if tgt_pil in ("JPEG", "WebP"):
                save_kwargs["quality"] = quality
            if tgt_pil == "WebP" and img.mode == "RGBA":
                save_kwargs["lossless"] = False

            img.save(target_path, tgt_pil, **save_kwargs)
            tgt_size = os.path.getsize(target_path)

            preserved_alpha = img.mode == "RGBA" and tgt_pil in ("PNG", "WebP", "GIF", "TIFF")
            compression_ratio = round(orig_size / tgt_size, 2) if tgt_size else None
            size_change_pct = round((tgt_size - orig_size) / orig_size * 100, 1) if orig_size else 0

            return {
                "status_code": 200,
                "message": f"Image converted: {source_format.upper()} → {target_format.upper()}",
                "data": {
                    "source_format": source_format, "target_format": target_format,
                    "original_size_bytes": orig_size,
                    "target_size_bytes": tgt_size,
                    "original_dimensions": f"{orig_w}x{orig_h}",
                    "new_dimensions": f"{new_w}x{new_h}",
                    "preserved_alpha": preserved_alpha,
                    "compression_ratio": compression_ratio,
                    "size_change_percent": size_change_pct,
                },
            }
        except Exception as e:
            raise ApiError(f"Image conversion failed: {e}", status_code=500, error_code="FS_004")

    # ---- ENCODING CONVERSION ----

    @classmethod
    def _convert_encoding(cls, source_path: str, target_path: str,
                           options: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        if not source_path:
            raise ApiError("source_path is required for encoding conversion", status_code=400, error_code="FS_004")

        src_enc = options.get("source_encoding")
        tgt_enc = options.get("target_encoding")
        errors = options.get("errors", "strict")

        if not tgt_enc:
            raise ApiError(
                "target_encoding is required in options",
                status_code=400,
                error_code="FS_004",
                details={"supported": SUPPORTED_FORMATS["encoding"]},
            )

        if dry_run:
            return {
                "status_code": 200,
                "message": f"DRY RUN: would convert encoding to {tgt_enc}",
                "data": {"source_encoding": src_enc or "auto", "target_encoding": tgt_enc},
            }

        try:
            orig_size = os.path.getsize(source_path)

            if src_enc:
                with open(source_path, "r", encoding=src_enc, errors=errors) as f:
                    content = f.read()
            else:
                if HAS_CHARDET:
                    with open(source_path, "rb") as f:
                        raw = f.read(1024 * 1024)
                    detected = chardet.detect(raw)
                    src_enc = detected.get("encoding", "utf-8")
                    with open(source_path, "r", encoding=src_enc, errors=errors) as f:
                        content = f.read()
                else:
                    with open(source_path, "rb") as f:
                        raw = f.read()
                    content = raw.decode("utf-8", errors=errors)
                    src_enc = "utf-8"

            with open(target_path, "w", encoding=tgt_enc, errors=errors) as f:
                f.write(content)

            tgt_size = os.path.getsize(target_path)
            char_count = len(content)
            return {
                "status_code": 200,
                "message": f"Encoding converted: {src_enc} → {tgt_enc}",
                "data": {
                    "source_encoding": src_enc,
                    "target_encoding": tgt_enc,
                    "original_size_bytes": orig_size,
                    "target_size_bytes": tgt_size,
                    "character_count": char_count,
                    "encoding_confidence": "auto-detected" if not options.get("source_encoding") else "manual",
                },
            }
        except UnicodeDecodeError as e:
            raise ApiError(
                f"Encoding error: {e}. Try a different source_encoding or set errors='replace'.",
                status_code=400,
                error_code="FS_004",
            )
        except Exception as e:
            raise ApiError(f"Encoding conversion failed: {e}", status_code=500, error_code="FS_004")
