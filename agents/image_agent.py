import os, json, base64, io, re
from agents.base_agent import BaseAgent
from config import STORAGE_DIR

class ImageAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "image_agent",
            "Analyze, process, convert, and generate information about images",
        )
        self.capabilities = ["image", "picture", "photo", "convert", "resize", "analyze", "exif"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "analyze" in t or "info" in t:
            fpath = self._extract_path(task)
            if fpath and os.path.isfile(fpath):
                return self._analyze_image(fpath)
            return "ImageAgent: Provide a valid image file path"

        if "resize" in t:
            return self._resize_help()
        if "convert" in t:
            return self._convert_help()
        if "list" in t or "find" in t:
            return self._find_images()
        return "ImageAgent: Available: analyze <path>, resize, convert, list"

    def _extract_path(self, task):
        for word in task.split():
            w = word.strip("\"'")
            if os.path.exists(w):
                return w
            for root, dirs, files in os.walk(STORAGE_DIR):
                for f in files:
                    if f.lower() == w.lower() or w.lower() in f.lower():
                        return os.path.join(root, f)
        return None

    def _analyze_image(self, fpath):
        try:
            from PIL import Image
            img = Image.open(fpath)
            exif_data = {}
            try:
                exif = img._getexif()
                if exif:
                    from PIL.ExifTags import TAGS
                    for k, v in exif.items():
                        name = TAGS.get(k, k)
                        if isinstance(v, bytes):
                            v = v.decode("utf-8", errors="replace")[:100]
                        exif_data[name] = str(v)[:100]
            except Exception:
                pass
            info = {
                "Filename": os.path.basename(fpath),
                "Size": f"{os.path.getsize(fpath):,} bytes",
                "Dimensions": f"{img.width} x {img.height}",
                "Format": img.format or "Unknown",
                "Mode": img.mode,
                "DPI": img.info.get("dpi", "N/A"),
            }
            result = "ImageAgent: Image Analysis\n"
            for k, v in info.items():
                result += f"  {k}: {v}\n"
            if exif_data:
                result += f"\n  EXIF Data:\n"
                for k, v in list(exif_data.items())[:10]:
                    result += f"    {k}: {v}\n"
            img.close()
            return result
        except ImportError:
            return "ImageAgent: PIL/Pillow not installed. Run: pip install pillow"
        except Exception as e:
            return f"ImageAgent: Error analyzing image: {e}"

    def _find_images(self):
        images = []
        exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff"}
        for root, dirs, files in os.walk(STORAGE_DIR):
            for f in files:
                if os.path.splitext(f)[1].lower() in exts:
                    fpath = os.path.join(root, f)
                    try:
                        images.append({"name": f, "path": fpath, "size": os.path.getsize(fpath)})
                    except Exception:
                        pass
                    if len(images) >= 50:
                        break
            if len(images) >= 50:
                break
        if images:
            return f"ImageAgent: Found {len(images)} images. Latest:\n" + "\n".join(
                f"  {img['name']} ({img['size']/1024:.1f} KB)" for img in images[:10]
            )
        return "ImageAgent: No images found"

    def _resize_help(self):
        return "ImageAgent: Resize usage: Use the Image Viewer app or run: python3 -c \"from PIL import Image; Image.open('input.jpg').resize((800,600)).save('output.jpg')\""

    def _convert_help(self):
        return "ImageAgent: Convert usage: Use the Image Viewer app or run: python3 -c \"from PIL import Image; Image.open('input.png').save('output.jpg')\""
