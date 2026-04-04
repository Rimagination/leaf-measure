from __future__ import annotations

from pathlib import Path

from engine.macros import build_full_macro, build_thumbnails_macro


def test_build_full_macro_injects_paths_and_results(tmp_path: Path) -> None:
    template = tmp_path / "full.ijm"
    template.write_text(
        (
            'inputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/01_Input_files");\n'
            '///inputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/01b_Bandpass_files");\n'
            '///inputdir3 = getDirectory("/Type_the_path_directory/Desktop/AREA/01c_Contrasted_files");\n'
            'outputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/02_Leaf_area");\n'
            'outputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/03_Leaf_outline");\n'
            'setTool(0);\n'
            '/// saveAs("Jpeg", inputdir2+list1[i]);\n'
            '/// saveAs("Jpeg", inputdir3+list1[i]);\n'
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite");\n'
            'run("Read and Write Excel", " dataset_label=[Data are in pixels]");\n'
            'setBatchMode(false);\n'
        ),
        encoding="utf-8",
    )

    macro = build_full_macro(
        template_path=template,
        input_dir=tmp_path / "input",
        bandpass_dir=tmp_path / "bandpass",
        contrasted_dir=tmp_path / "contrasted",
        area_dir=tmp_path / "area",
        outline_dir=tmp_path / "outline",
        results_csv=tmp_path / "results.csv",
    )

    assert "getDirectory" not in macro
    assert "setTool(0)" not in macro
    assert 'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite exclude");' in macro
    assert 'saveAs("Results"' in macro
    assert 'run("Quit");' in macro


def test_build_thumbnails_macro_inserts_crop_before_mask(tmp_path: Path) -> None:
    template = tmp_path / "thumbs.ijm"
    template.write_text(
        (
            'inputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/01_Input_files");\n'
            '///inputdir1a = getDirectory("/Type_the_path_directory/Desktop/AREA/01a_Bandpass_files");\n'
            '///inputdir1b = getDirectory("/Type_the_path_directory/Desktop/AREA/01b_Contrasted_files");\n'
            'inputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/02_thumbnails");\n'
            'outputdir1 = getDirectory("/Type_the_path_directory/Desktop/AREA/03_Leaf_area");\n'
            'outputdir2 = getDirectory("/Type_the_path_directory/Desktop/AREA/04_Leaf_outline");\n'
            'setTool(0);\n'
            '/// saveAs("Jpeg", inputdir1a+list1[i]);\n'
            '/// saveAs("Jpeg", inputdir1b+list1[i]);\n'
            'run("Duplicate...", "title=RGB");\n\trun("Create Mask");\n'
            'run("Analyze Particles...", "size=80-Infinity show=[Overlay Masks] composite clear add");\n'
            'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite");\n'
            'run("Read and Write Excel", " dataset_label=[Data are in pixels]");\n'
            'setBatchMode(false);\n'
        ),
        encoding="utf-8",
    )

    macro = build_thumbnails_macro(
        template_path=template,
        input_dir=tmp_path / "input",
        bandpass_dir=tmp_path / "bandpass",
        contrasted_dir=tmp_path / "contrasted",
        thumbnails_dir=tmp_path / "thumbs",
        area_dir=tmp_path / "area",
        outline_dir=tmp_path / "outline",
        results_csv=tmp_path / "results.csv",
    )

    assert "setTool(0)" not in macro
    assert 'run("Crop");' in macro
    assert macro.index('run("Crop");') < macro.index('run("Create Mask");')
    assert 'run("Analyze Particles...", "size=80-Infinity show=[Overlay Masks] composite clear add");' in macro
    assert 'run("Analyze Particles...", "size=80-Infinity show=Outlines display composite");' in macro
    assert 'saveAs("Results"' in macro
    assert 'run("Quit");' in macro
