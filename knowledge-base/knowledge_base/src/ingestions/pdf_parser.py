from docling.datamodel.pipeline_options import PdfPipelineOptions,TableFormerMode
from docling.document_converter import DocumentConverter,PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import gc
from pathlib import Path



class PDFParser:
    def __init__(self,do_ocr:bool,do_table_structure:bool,generate_picture_images:bool,cell_matching:bool,image_scale:float):
        print("Start configuring")
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = do_ocr
        self.pipeline_options.do_table_structure = do_table_structure
        self.pipeline_options.generate_picture_images = generate_picture_images
        self.pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        self.pipeline_options.table_structure_options.do_cell_matching = cell_matching
        self.pipeline_options.images_scale = image_scale
        try :
            self.converter = DocumentConverter(
                format_options = {
                    InputFormat.PDF : PdfFormatOption(
                        pipeline_options=self.pipeline_options,
                        backend=PyPdfiumDocumentBackend
                    )
                }
            )

        except Exception as e :
            raise Exception("Failed to initialize the pdf parser") from e 
    
    def parse(self,source_dir:str,output_dir:str) -> None:
        print("Start Parsing")
        SOURCE_DIR = Path(source_dir)
        print(SOURCE_DIR)
        OUTPUT_DIR = Path(output_dir)
        print(OUTPUT_DIR)
        if not OUTPUT_DIR.is_dir() or  not OUTPUT_DIR.exists():
            raise Exception("The output folder doesn't exist")
        if not SOURCE_DIR.is_dir() or  not SOURCE_DIR.exists():
            raise Exception("The input folder doesn't exist")

        file_list = list(SOURCE_DIR.glob("*.pdf"))
        for file in file_list:
            print(f"Starting conversion: {file.name}")
            try:
                print("Converting PDF...")
                result = self.converter.convert(file)
                print("PDF conversion completed")
                document = result.document
                print("Exporting Markdown...")
                markdown = document.export_to_markdown()
                filename = file.stem + ".md"
                destination = OUTPUT_DIR / filename
                destination.write_text(markdown, encoding="utf-8")
                print(f"Saved: {destination}")
                del document, result
                gc.collect()
            except Exception as e:
                print(f"Failed to process {file.name}: {e}", flush=True)
                raise
        






