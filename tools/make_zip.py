import os, sys, zipfile, time
def make(src_dir, out_zip, arc_root=None):
    """壓縮資料夾：中文檔名標記 UTF-8（Windows 不亂碼），.command／.sh 保留可執行權限（Mac 才能雙擊執行）。"""
    arc_root = arc_root or os.path.basename(src_dir.rstrip("/"))
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                p = os.path.join(root, f)
                zi = zipfile.ZipInfo(os.path.join(arc_root, os.path.relpath(p, src_dir)), time.localtime(os.path.getmtime(p))[:6])
                zi.create_system = 3
                zi.external_attr = ((0o755 if f.endswith((".command", ".sh")) else 0o644) | 0o100000) << 16
                zi.compress_type = zipfile.ZIP_DEFLATED
                if not zi.filename.isascii():
                    zi.flag_bits |= 0x800
                with open(p, "rb") as fh:
                    z.writestr(zi, fh.read())
if __name__ == "__main__":
    make(*sys.argv[1:])
