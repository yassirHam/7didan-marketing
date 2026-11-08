from .crawler import crawl_web
from .pdf_parser import PDFParser



async def ingest(scrape_web:bool,parse_pdf:bool,crawler_config:dict,parser_config:dict):

    if scrape_web:
        if crawler_config is None:
            raise Exception("crawler configuration is not provided")
        await crawl_web(**crawler_config)
    if parse_pdf:
        if parser_config is None:
            raise Exception("'parser_config' is required")
        parser = PDFParser(
            do_ocr=parser_config['do_ocr'],
            do_table_structure=parser_config['do_table_structure'],
            generate_picture_images=parser_config['generate_picture_images'],
            cell_matching=parser_config['cell_matching'],
            image_scale=parser_config['image_scale']
            )
        
        parser.parse(parser_config['source_dir'],parser_config['output_dir'])

    print("Injection Completed")
        
        











