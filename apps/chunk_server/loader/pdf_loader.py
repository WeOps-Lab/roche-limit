import base64
import re
from io import BytesIO
from typing import List

import fitz
from langchain_core.documents import Document
from langserve import RemoteRunnable
from loguru import logger
from tqdm import tqdm
from tabula.io import read_pdf
import pandas as pd


class PDFLoader:

    def __init__(self, file_path, ocr_provider_address, enable_ocr_parse):
        self.file_path = file_path
        self.ocr_provider_address = ocr_provider_address
        self.enable_ocr_parse = enable_ocr_parse

    def remove_unicode_chars(self, text):
        return re.sub(r'\\u[fF]{1}[0-9a-fA-F]{3}', '', text)

    def _get_table_areas(self, pdf):
        """获取所有页面的表格区域"""
        table_areas = []
        for page in pdf:
            # 使用 fitz 的表格检测功能
            tables = page.find_tables()
            if tables and tables.tables:
                for table in tables.tables:
                    # 保存表格的边界框
                    table_areas.append((page.number, table.bbox))
        return table_areas

    def _is_in_table_area(self, page_num, bbox, table_areas):
        """检查文本块是否在任何表格区域内"""
        try:
            x0, y0, x1, y1 = bbox
            for page_number, table_bbox in table_areas:
                if page_num == page_number:
                    tx0, ty0, tx1, ty1 = table_bbox
                    # 检查重叠
                    if x0 < tx1 and x1 > tx0 and y0 < ty1 and y1 > ty0:
                        return True
            return False
        except Exception as e:
            logger.error(f"检查文本块是否在表格区域内失败: {e}")
            return False

    def load(self) -> List[Document]:

        table_docs = []
        text_docs = []

        with fitz.open(self.file_path) as pdf:
            # 首先获取所有表格区域
            table_areas = self._get_table_areas(pdf)

            # OCR处理部分保持不变
            if self.enable_ocr_parse:
                try:
                    file_remote = RemoteRunnable(self.ocr_provider_address)
                    # 解析图片
                    for page_number in tqdm(range(1, len(pdf) + 1), desc=f"解析PDF图片[{self.file_path}]"):
                        page = pdf[page_number - 1]
                        for image_number, image in enumerate(page.get_images(), start=1):
                            xref_value = image[0]
                            base_image = pdf.extract_image(xref_value)
                            image_bytes = base_image["image"]
                            file = BytesIO(image_bytes)

                            # 完善这部分的代码
                            content = file_remote.invoke({
                                "file": base64.b64encode(file.read()).decode('utf-8'),
                            })
                            # remove content where page_content is empty
                            for doc in content:
                                if doc.page_content:
                                    doc.metadata["format"] = "image"
                                    text_docs.append(doc)
                except Exception as e:
                    logger.error(f"OCR解析PDF图片失败: {e}")

            # 解析文本，跳过表格区域

            full_text = ""
            try:
                for page in tqdm(pdf, desc=f"解析PDF文本[{self.file_path}]"):
                    page_dict = page.get_text("dict")
                    for block in page_dict["blocks"]:
                        if block["type"] == 0:  # 文本块
                            if not self._is_in_table_area(page.number, block["bbox"], table_areas):
                                for line in block["lines"]:
                                    for span in line["spans"]:
                                        text = span["text"].strip()
                                        if text:
                                            text = self.remove_unicode_chars(text)
                                            full_text += text + " "
            except Exception as e:
                logger.error(f"解析PDF文本失败: {e}")

            if full_text:
                text_docs.append(Document(full_text.strip()))

        # 处理表格部分保持不变
        try:
            tables = read_pdf(self.file_path, pages='all')
            for table in tqdm(tables, desc=f"解析PDF表格[{self.file_path}]"):
                df = pd.DataFrame(table)
                markdown_content = df.to_markdown(index=False)
                table_docs.append(Document(markdown_content, metadata={"format": "table"}))
        except Exception as e:
            logger.error(f"解析PDF表格失败: {e}")

        logger.info(f'解析PDF文件完成：{self.file_path}')

        all_docs = text_docs + table_docs
        return all_docs
