import base64
from typing import List

import cv2
import numpy as np
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from loguru import logger
from paddleocr import PaddleOCR

from apps.ocr_server.user_types.paddle_ocr_request import PaddleOcrRequest


class PaddleOcrRunnable:
    def __init__(self):
        self.ocr_engine = PaddleOCR(table=True, show_log=True, lang='ch', use_angle_cls=True, )

    def execute(self, request: PaddleOcrRequest) -> List[Document]:
        # base64 str to opencv img
        base_image = base64.b64decode(request.file)
        nparr = np.frombuffer(base_image, np.uint8)

        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image")
            return []

        result = self.ocr_engine.ocr(img, cls=True)
        try:
            recognized_texts = ''
            for lines in result:
                for line in lines:
                    recognized_texts += line[1][0] + ''

            return [Document(page_content=recognized_texts)]
        except Exception as e:
            logger.warning(f"Failed to recognize text: {e}")
            return []

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=PaddleOcrRequest, output_type=List[Document])