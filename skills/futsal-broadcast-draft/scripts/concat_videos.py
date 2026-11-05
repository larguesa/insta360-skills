"""Passo 8: concatena os videos reenquadrados (mesmo codec/resolucao) sem re-encode.
python concat_videos.py --out jogo_completo.mp4 a.mp4 b.mp4 ..."""
import argparse, os, subprocess, tempfile
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("files", nargs="+"); a = ap.parse_args()
lst = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
for f in a.files: lst.write("file '" + os.path.abspath(f).replace("'", "'\\''") + "'\n")
lst.close()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", "-movflags", "+faststart", a.out], check=True)
os.unlink(lst.name); print("ok", a.out)
