from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from PIL import Image as PILImage
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
COLLECTION = PROJECT_ROOT.parents[1] / "流程图集合"
REPORT = PROJECT_ROOT / "output" / "pdf" / "super-biz-agent-architecture-report.pdf"
PROJECT_GUIDE = PROJECT_ROOT / "output" / "pdf" / "super-biz-agent-project-guide.pdf"

DIAGRAMS = {
    "01-system-overview.pdf": "2.1-系统总览.pdf",
    "02-chat-knowledge.png": "2.2-普通聊天与知识入库.pdf",
    "03-durable-aiops.png": "2.3-持久化AIOps诊断.pdf",
    "04-enterprise-workflow.png": "2.4-企业多智能体事故分析.pdf",
    "05-runtime-storage.png": "2.5-启动存储与运行边界.pdf",
}


def image_to_pdf(source: Path, target: Path, title: str) -> None:
    with PILImage.open(source) as image:
        width, height = image.size
    page_width = width * 0.75
    page_height = height * 0.75
    document = canvas.Canvas(str(target), pagesize=(page_width, page_height), pageCompression=1)
    document.setTitle(title)
    document.setAuthor("SpatialSRE-Agent")
    document.drawImage(
        str(source),
        0,
        0,
        width=page_width,
        height=page_height,
        preserveAspectRatio=True,
        mask="auto",
    )
    document.showPage()
    document.save()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_guides() -> None:
    complete_target = COLLECTION / "完整项目pdf版.pdf"
    guide_target = COLLECTION / "SuperBizAgent_项目详解_易懂增强版.pdf"

    if not REPORT.exists():
        raise FileNotFoundError(f"Architecture report not found: {REPORT}")
    if not PROJECT_GUIDE.exists():
        raise FileNotFoundError(f"Project guide not found: {PROJECT_GUIDE}")

    shutil.copy2(REPORT, complete_target)
    shutil.copy2(PROJECT_GUIDE, guide_target)

    if sha256(complete_target) == sha256(guide_target):
        raise RuntimeError("The architecture report and project guide must be different PDFs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--guide-only",
        action="store_true",
        help="Only export the two multi-page documents and validate their hashes.",
    )
    args = parser.parse_args()

    COLLECTION.mkdir(parents=True, exist_ok=True)
    if not args.guide_only:
        for source_name, target_name in DIAGRAMS.items():
            source = HERE / source_name
            target = COLLECTION / target_name
            if source.suffix.lower() == ".pdf":
                shutil.copy2(source, target)
            else:
                image_to_pdf(source, target, target_name.removesuffix(".pdf"))

        shutil.copy2(HERE / "01-system-overview.svg", COLLECTION / "完整ai项目流程图.svg")
        shutil.copy2(HERE / "03-durable-aiops.png", COLLECTION / "graph aiops runtime.png")

    export_guides()


if __name__ == "__main__":
    main()
