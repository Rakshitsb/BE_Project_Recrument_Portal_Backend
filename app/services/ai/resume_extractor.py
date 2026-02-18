import pdfplumber
import docx
import io
from fastapi import UploadFile, HTTPException

class ResumeExtractor:
    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        filename = file.filename.lower()
        content = await file.read()
        file_stream = io.BytesIO(content)
        
        text = ""
        
        try:
            if filename.endswith(".pdf"):
                with pdfplumber.open(file_stream) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                            
            elif filename.endswith(".docx"):
                doc = docx.Document(file_stream)
                text = "\n".join([para.text for para in doc.paragraphs])
                
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF and DOCX are supported.")
                
            if not text.strip():
                 raise HTTPException(status_code=400, detail="Could not extract text from the file.")
                 
            return text.strip()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
