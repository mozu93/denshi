"""
ndlocr_server.py
ndlocr-lite のモデルを起動時に1回だけロードし、
stdin からファイルパスを受け取って OCR 結果を JSON で stdout に返す常駐サーバー。

このスクリプトは ndlocr-lite の Python 環境で実行される。
"""
import sys
import json
import os
import numpy as np
from pathlib import Path
from PIL import Image

# ocr.py のある site-packages を参照
BASE_DIR = Path(__file__).resolve().parent

# ---------- モデルパス ----------
_NDL_SITE = None
for p in sys.path:
    if os.path.isfile(os.path.join(p, "ocr.py")):
        _NDL_SITE = p
        break

if _NDL_SITE is None:
    print(json.dumps({"error": "ocr.py が見つかりません"}), flush=True)
    sys.exit(1)

sys.path.insert(0, _NDL_SITE)

from ocr import get_detector, get_recognizer, process_cascade, RecogLine
from xml.etree import ElementTree as ET
from yaml import safe_load

site = Path(_NDL_SITE)

class _Args:
    det_weights          = str(site / "model" / "deim-s-1024x1024.onnx")
    det_classes          = str(site / "config" / "ndl.yaml")
    det_score_threshold  = 0.2
    det_conf_threshold   = 0.25
    det_iou_threshold    = 0.2
    rec_weights          = str(site / "model" / "parseq-ndl-24x768-100-tiny-153epoch-tegaki3-r8data-202604.onnx")
    rec_weights30        = str(site / "model" / "parseq-ndl-24x256-30-tiny-189epoch-tegaki3-r8data-202604.onnx")
    rec_weights50        = str(site / "model" / "parseq-ndl-24x384-50-tiny-300epoch-tegaki3-r8data-202604.onnx")
    rec_classes          = str(site / "config" / "NDLmoji.yaml")
    device               = "cpu"
    simple_mode          = False
    enable_tcy           = False

args = _Args()

# --- モデルを1回だけロード ---
try:
    detector      = get_detector(args)
    recognizer100 = get_recognizer(args=args)
    recognizer30  = get_recognizer(args=args, weights_path=args.rec_weights30)
    recognizer50  = get_recognizer(args=args, weights_path=args.rec_weights50)
except Exception as e:
    print(json.dumps({"error": f"モデルロード失敗: {e}"}), flush=True)
    sys.exit(1)

classeslist = list(detector.classes.values())

# 準備完了を通知
print("READY", flush=True)


def run_ocr(img_path: str) -> dict:
    """1枚の画像に対して OCR を実行し JSON 辞書を返す。"""
    pil_image = Image.open(img_path).convert("RGB")
    img_w, img_h = pil_image.size
    img_np = np.array(pil_image)

    detections = detector.detect(img_np)

    # XML ツリー構築（process() から抜粋）
    root = ET.Element("OCRDATASET")
    page = ET.SubElement(root, "PAGE")
    page.set("IMAGENAME", os.path.basename(img_path))
    page.set("WIDTH",  str(img_w))
    page.set("HEIGHT", str(img_h))

    alllineobj  = []
    tatelinecnt = 0
    alllinecnt  = 0

    for idx, det in enumerate(detections):
        xmin, ymin, xmax, ymax = det["box"]
        line_w = int(xmax - xmin)
        line_h = int(ymax - ymin)
        if line_w <= 0 or line_h <= 0:
            continue
        line_elem = ET.SubElement(page, "LINE")
        c_idx = int(det["class_index"])
        type_name = classeslist[c_idx] if c_idx < len(classeslist) else "本文"
        line_elem.set("TYPE",  type_name)
        line_elem.set("X",     str(int(xmin)))
        line_elem.set("Y",     str(int(ymin)))
        line_elem.set("WIDTH", str(line_w))
        line_elem.set("HEIGHT",str(line_h))
        pred_char_cnt = det.get("pred_char_count", 100.0)
        line_elem.set("PRED_CHAR_CNT", f"{pred_char_cnt:.3f}")
        if line_h > line_w:
            tatelinecnt += 1
        alllinecnt += 1
        lineimg = img_np[int(ymin):int(ymax), int(xmin):int(xmax), :]
        alllineobj.append(RecogLine(lineimg, idx, pred_char_cnt))

    if len(alllineobj) == 0:
        return {"contents": [[]], "imginfo": {"img_width": img_w, "img_height": img_h,
                                               "img_path": img_path, "img_name": os.path.basename(img_path)}}

    resultlinesall = process_cascade(alllineobj, recognizer30, recognizer50, recognizer100, is_cascade=True)

    resjsonarray = []
    for idx, lineobj in enumerate(root.findall(".//LINE")):
        lineobj.set("STRING", resultlinesall[idx])
        xmin_l = int(lineobj.get("X"))
        ymin_l = int(lineobj.get("Y"))
        lw     = int(lineobj.get("WIDTH"))
        lh     = int(lineobj.get("HEIGHT"))
        try:
            conf = float(lineobj.get("CONF", "0"))
        except Exception:
            conf = 0.0
        type_str = lineobj.get("TYPE", "")
        c_idx_l = classeslist.index(type_str) if type_str in classeslist else 1
        resjsonarray.append({
            "boundingBox": [[xmin_l, ymin_l], [xmin_l, ymin_l + lh],
                            [xmin_l + lw, ymin_l], [xmin_l + lw, ymin_l + lh]],
            "id": idx,
            "isVertical":  "true",
            "text":        resultlinesall[idx],
            "isTextline":  "true",
            "confidence":  conf,
            "class_index": c_idx_l,
        })

    return {
        "contents": [resjsonarray],
        "imginfo": {
            "img_width":  img_w,
            "img_height": img_h,
            "img_path":   img_path,
            "img_name":   os.path.basename(img_path),
        }
    }


# --- メインループ：stdin からパスを受け取り stdout に JSON を返す ---
for raw_line in sys.stdin:
    img_path = raw_line.strip()
    if not img_path:
        continue
    try:
        result = run_ocr(img_path)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
