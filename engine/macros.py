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


def _exclude_on_edges(macro: str) -> str:
    replacements = {
        'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite");':
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite exclude");',
        'run("Analyze Particles...", "size=80-Infinity show=[Overlay Masks] composite clear add");':
            'run("Analyze Particles...", "size=80-Infinity show=[Overlay Masks] composite clear add exclude");',
    }
    for old, new in replacements.items():
        macro = macro.replace(old, new)
    return macro


def _manual_results_export_block(results_csv: Path) -> list[str]:
    return [
        'csv = "Label,Area,Perim.,Circ.,Length,Width ,Solidity\\n";',
        "for (row = 0; row < nResults; row++) {",
        '  csv += getResultLabel(row) + "," + getResult("Area", row) + "," + getResult("Perim.", row) + "," + getResult("Circ.", row) + "," + getResult("Length", row) + "," + getResult("Width ", row) + "," + getResult("Solidity", row) + "\\n";',
        "}",
        f'File.saveString(csv, "{results_csv.resolve().as_posix()}");',
    ]


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
    macro = _exclude_on_edges(macro)
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


def build_full_measurement_macro(
    *,
    area_dir: Path,
    outline_dir: Path,
    results_csv: Path,
) -> str:
    return "\n".join(
        [
            f'outputdir1 = "{macro_string(area_dir)}";',
            f'outputdir2 = "{macro_string(outline_dir)}";',
            "list2 = getFileList(outputdir1);",
            "Array.sort(list2);",
            "setBatchMode(true);",
            "for (i=0; i<list2.length; i++) {",
            " file2 = list2[i];",
            "  open(outputdir1+file2);",
            'run("Set Measurements...", "area perimeter feret\'s shape display redirect=None decimal=2");',
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite exclude");',
            'saveAs("png", outputdir2+list2[i]);',
            "close();",
            "}",
            'Table.deleteColumn("FeretX");',
            'Table.deleteColumn("FeretY");',
            'Table.deleteColumn("FeretAngle");',
            'Table.deleteColumn("AR");',
            'Table.deleteColumn("Round");',
            'Table.renameColumn("Feret", "Length");',
            'Table.renameColumn("MinFeret", "Width ");',
            *_manual_results_export_block(results_csv),
            'run("Close All");',
            'setBatchMode(false);',
            'run("Quit");',
            "",
        ]
    )


def build_thumbnail_measurement_macro(
    *,
    area_dir: Path,
    outline_dir: Path,
    results_csv: Path,
) -> str:
    return "\n".join(
        [
            f'outputdir1 = "{macro_string(area_dir)}";',
            f'outputdir2 = "{macro_string(outline_dir)}";',
            "list2 = getFileList(outputdir1);",
            "Array.sort(list2);",
            "setBatchMode(true);",
            "for (i=0; i<list2.length; i++) {",
            " file2 = list2[i];",
            "  open(outputdir1+file2);",
            'run("Set Measurements...", "area perimeter feret\'s shape display redirect=None decimal=2");',
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite exclude");',
            'saveAs("png", outputdir2+list2[i]);',
            "close();",
            "}",
            'Table.deleteColumn("FeretX");',
            'Table.deleteColumn("FeretY");',
            'Table.deleteColumn("FeretAngle");',
            'Table.deleteColumn("AR");',
            'Table.deleteColumn("Round");',
            'Table.renameColumn("Feret", "Length");',
            'Table.renameColumn("MinFeret", "Width ");',
            *_manual_results_export_block(results_csv),
            'run("Close All");',
            'setBatchMode(false);',
            'run("Quit");',
            "",
        ]
    )


def build_thumbnail_outline_macro(
    *,
    area_dir: Path,
    outline_dir: Path,
) -> str:
    return "\n".join(
        [
            f'outputdir1 = "{macro_string(area_dir)}";',
            f'outputdir2 = "{macro_string(outline_dir)}";',
            "list2 = getFileList(outputdir1);",
            "Array.sort(list2);",
            "setBatchMode(true);",
            "for (i=0; i<list2.length; i++) {",
            " file2 = list2[i];",
            "  open(outputdir1+file2);",
            'run("Set Measurements...", "area perimeter feret\'s shape display redirect=None decimal=2");',
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite");',
            'saveAs("png", outputdir2+list2[i]);',
            "close();",
            "}",
            'run("Close All");',
            'setBatchMode(false);',
            'run("Quit");',
            "",
        ]
    )
