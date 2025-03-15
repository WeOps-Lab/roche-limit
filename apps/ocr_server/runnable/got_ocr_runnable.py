import base64
from typing import List

import cv2
import numpy as np
import torch
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from loguru import logger
from modelscope import AutoModel, AutoTokenizer
from apps.ocr_server.user_types.ocr_request import OcrRequest


class GotOcrRunnable:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = AutoModel.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True, low_cpu_mem_usage=True,
                                               device_map=device, use_safetensors=True,
                                               pad_token_id=self.tokenizer.eos_token_id)
        self.model = self.model.eval()
        if device == 'cuda':
            self.model = self.model.cuda()


        logger.info(f"GOT-OCR model running on {device}")

    def execute(self, request: OcrRequest) -> List[Document]:
        import tempfile
        import os

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
            res = self.model.chat(self.tokenizer, temp_path, ocr_type='format')
            print(res)
            # Process the image (add your processing code here)
            # The file will be automatically deleted when the with block exits

        return []

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=OcrRequest, output_type=List[Document])
