"""Build and verify the user-facing, machine-independent print package."""
from pathlib import Path
import hashlib
import json
import zipfile

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PACK=ROOT/'source_cad/print_pack/2026-10-21_handle'

def main():
    report=json.loads((PACK/'export_manifest.json').read_text(encoding='utf-8'))
    guide=(ROOT/'docs/mechanical/TEACHING_HANDLE_V1_PRINT_GUIDE.md').read_text(encoding='utf-8')
    # Full text included, with image/link paths useful in the repository; PNG
    # previews are also included as ordinary files for independent transfer.
    lead='ATOM 独立径向把手打印包 — 2026-10-21\n\n完整把手打印 1 件；试配环可选，不能当承载件。\n按毫米、100% 导入，保持文件平放方向，完整把手 Z 高度 26 mm。\n新增安装环厚 16 mm，需重新核对 M6 长度。详细说明如下。\n\n'
    (PACK/'打印与试装说明.txt').write_text(lead+guide,encoding='utf-8-sig')
    files=[PACK/p['print_filename'] for p in report['parts'].values()]
    files += [PACK/'打印与试装说明.txt',PACK/'export_manifest.json']
    for name in ['handle_preview.png','print_orientation_preview.png','backplate_handle_fit_preview.png']:
        target=PACK/name; target.write_bytes((OUT/name).read_bytes()); files.append(target)
    archive=PACK.parent/'ATOM_handle_20261021.zip'
    for p in report['parts'].values():
        assert hashlib.sha256((PACK/p['print_filename']).read_bytes()).hexdigest()==p['sha256']
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f,arcname=f.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
        for f in files: assert z.read(f.name)==f.read_bytes()
    print(f'Verified {len(files)} files: {archive}')

if __name__=='__main__': main()
