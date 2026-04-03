from __future__ import annotations

from pathlib import Path


def macro_string(path: Path) -> str:
    text = path.resolve().as_posix()
    if not text.endswith("/"):
        text += "/"
    return text


def original_macro(root: Path, mode: str) -> Path:
    mapping = {
        "full": root / "macros" / "original" / "Fameles_v2_Full_image.ijm",
        "thumbnails": root / "macros" / "original" / "Fameles_v2_Thumbnails.ijm",
    }
    return mapping[mode]


def _replace_results_export(macro: str, results_csv: Path) -> str:
    return macro.replace(
        'run("Read and Write Excel", " dataset_label=[Data are in pixels]");',
        f'saveAs("Results", "{results_csv.resolve().as_posix()}");',
    )


def _append_quit(macro: str) -> str:
    return macro.replace("setBatchMode(false);", 'setBatchMode(false);\nrun("Quit");')


def build_full_macro(
    *,
    template_path: Path,
    input_dir: Path,
    bandpass_dir: Path,
    contrasted_dir: Path,
    area_dir: Path,
    outline_dir: Path,
    results_csv: Path,
) -> str:
    macro = template_path.read_text(encoding="utf-8", errors="ignore")
    replacements = {
        'inputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/01_Input_files");':
            f'inputdir1 = "{macro_string(input_dir)}";',
        '///inputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/01b_Bandpass_files");':
            f'inputdir2 = "{macro_string(bandpass_dir)}";',
        '///inputdir3 = getDirectory("/Type_the_path_directory/Desktop/AREA/01c_Contrasted_files");':
            f'inputdir3 = "{macro_string(contrasted_dir)}";',
        'outputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/02_Leaf_area");':
            f'outputdir1 = "{macro_string(area_dir)}";',
        'outputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/03_Leaf_outline");':
            f'outputdir2 = "{macro_string(outline_dir)}";',
        '/// saveAs("Jpeg", inputdir2+list1[i]);':
            'saveAs("Jpeg", inputdir2+list1[i]);',
        '/// saveAs("Jpeg", inputdir3+list1[i]);':
            'saveAs("Jpeg", inputdir3+list1[i]);',
        "setTool(0);\n": "",
    }
    for old, new in replacements.items():
        macro = macro.replace(old, new)
    macro = _replace_results_export(macro, results_csv)
    return _append_quit(macro)


def build_thumbnails_macro(
    *,
    template_path: Path,
    input_dir: Path,
    bandpass_dir: Path,
    contrasted_dir: Path,
    thumbnails_dir: Path,
    area_dir: Path,
    outline_dir: Path,
    results_csv: Path,
) -> str:
    macro = template_path.read_text(encoding="utf-8", errors="ignore")
    replacements = {
        'inputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/01_Input_files");':
            f'inputdir1 = "{macro_string(input_dir)}";',
        '///inputdir1a = getDirectory("/Type_the_path_directory/Desktop/AREA/01a_Bandpass_files");':
            f'inputdir1a = "{macro_string(bandpass_dir)}";',
        '///inputdir1b = getDirectory("/Type_the_path_directory/Desktop/AREA/01b_Contrasted_files");':
            f'inputdir1b = "{macro_string(contrasted_dir)}";',
        'inputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/02_thumbnails");':
            f'inputdir2 = "{macro_string(thumbnails_dir)}";',
        'outputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/03_Leaf_area");':
            f'outputdir1 = "{macro_string(area_dir)}";',
        'outputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/04_Leaf_outline");':
            f'outputdir2 = "{macro_string(outline_dir)}";',
        '/// saveAs("Jpeg", inputdir1a+list1[i]);':
            'saveAs("Jpeg", inputdir1a+list1[i]);',
        '/// saveAs("Jpeg", inputdir1b+list1[i]);':
            'saveAs("Jpeg", inputdir1b+list1[i]);',
        "setTool(0);\n": "",
        'run("Duplicate...", "title=RGB");\n\trun("Create Mask");':
            'run("Duplicate...", "title=RGB");\n\trun("Crop");\n\trun("Create Mask");',
    }
    for old, new in replacements.items():
        macro = macro.replace(old, new)
    macro = _replace_results_export(macro, results_csv)
    return _append_quit(macro)

