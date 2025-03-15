import base64
import tempfile
from typing import List

import cv2
import numpy as np
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from loguru import logger
from modelscope import AutoModel, AutoTokenizer

from apps.ocr_server.user_types.ocr_request import OcrRequest


class GotOcrRunnable:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True)
        self.model = AutoModel.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True, low_cpu_mem_usage=True,
                                               device_map='cuda', use_safetensors=True,
                                               pad_token_id=self.tokenizer.eos_token_id)
        self.model = self.model.eval()
        self.model = self.model.cuda()

    def execute(self, request: OcrRequest) -> List[Document]:
        base_image = base64.b64decode(request.file)
        nparr = np.frombuffer(base_image, np.uint8)

        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image")
            return []

        # Save the image to a temporary file that will be automatically deleted
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=True) as temp_file:
            temp_path = temp_file.name
            cv2.imwrite(temp_path, img)
            logger.info(f"Image saved temporarily to {temp_path}")
            recognized_texts = self.model.chat(self.tokenizer, temp_path, ocr_type='ocr')
            return [Document(page_content=recognized_texts)]

        return []

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=OcrRequest, output_type=List[Document])
