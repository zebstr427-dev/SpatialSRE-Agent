from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image as PILImage
from reportlab.pdfgen import canvas


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
COLLECTION = PROJECT_ROOT.parents[1] / "流程图集合"
REPORT = PROJECT_ROOT / "output" / "pdf" / "super-biz-agent-architecture-report.pdf"

DIAGRAMS = {
    "01-system-overview.png": "2.1-系统总览.pdf",
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


def main() -> None:
    COLLECTION.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in DIAGRAMS.items():
        image_to_pdf(HERE / source_name, COLLECTION / target_name, target_name.removesuffix(".pdf"))

    shutil.copy2(HERE / "01-system-overview.svg", COLLECTION / "完整ai项目流程图.svg")
    shutil.copy2(HERE / "03-durable-aiops.png", COLLECTION / "graph aiops runtime.png")
    shutil.copy2(REPORT, COLLECTION / "完整项目pdf版.pdf")
    shutil.copy2(REPORT, COLLECTION / "SuperBizAgent_项目详解_易懂增强版.pdf")


if __name__ == "__main__":
    main()
