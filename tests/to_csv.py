import csv
import os
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path, encoding='utf-8'):
    """
    从PDF文件中提取文本内容
    :param pdf_path: PDF文件路径
    :param encoding: 编码格式，默认utf-8
    :return: 提取的文本字符串
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        # 遍历PDF所有页面提取文本
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.encode(encoding, errors='ignore').decode(encoding)
    except Exception as e:
        print(f"读取PDF文件失败 {pdf_path}: {str(e)}")
        return ""

def text_to_csv(input_text, csv_path, delimiter=',', encoding='utf-8'):
    """
    将文本内容写入CSV文件
    :param input_text: 待转换的文本内容
    :param csv_path: 输出CSV文件路径
    :param delimiter: CSV分隔符，默认逗号
    :param encoding: 编码格式，默认utf-8
    """
    try:
        # 按行分割文本
        lines = input_text.strip().split('\n')
        with open(csv_path, 'w', newline='', encoding=encoding) as csvfile:
            writer = csv.writer(csvfile, delimiter=delimiter)
            # 遍历每一行，按分隔符分割后写入CSV
            for line in lines:
                # 过滤空行
                if line.strip():
                    row = [cell.strip() for cell in line.split(delimiter)]
                    writer.writerow(row)
        print(f"成功生成CSV文件: {csv_path}")
    except Exception as e:
        print(f"写入CSV文件失败 {csv_path}: {str(e)}")

def convert_file_to_csv(input_path, output_dir=None, delimiter=',', encoding='utf-8'):
    """
    统一转换函数：支持PDF/TXT转CSV
    :param input_path: 输入文件路径（PDF/TXT）
    :param output_dir: 输出目录，默认和输入文件同目录
    :param delimiter: CSV分隔符，默认逗号
    :param encoding: 编码格式，默认utf-8
    """
    # 校验输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误：文件 {input_path} 不存在！")
        return

    # 处理输出路径
    if output_dir is None:
        output_dir = os.path.dirname(input_path)
    os.makedirs(output_dir, exist_ok=True)

    # 获取文件名（不含后缀）
    filename = os.path.splitext(os.path.basename(input_path))[0]
    csv_path = os.path.join(output_dir, f"{filename}.csv")

    # 根据文件后缀处理
    file_ext = os.path.splitext(input_path)[1].lower()
    if file_ext == '.txt':
        # 读取TXT文件
        with open(input_path, 'r', encoding=encoding, errors='ignore') as f:
            text_content = f.read()
        text_to_csv(text_content, csv_path, delimiter, encoding)

    elif file_ext == '.pdf':
        # 提取PDF文本并转换
        text_content = extract_text_from_pdf(input_path, encoding)
        if text_content:
            text_to_csv(text_content, csv_path, delimiter, encoding)
        else:
            print(f"警告：PDF文件 {input_path} 未提取到有效文本！")

    else:
        print(f"错误：不支持的文件格式 {file_ext}，仅支持PDF/TXT！")

# ------------------- 示例用法 -------------------
if __name__ == "__main__":
    # 示例1：转换单个TXT文件
    convert_file_to_csv(
        input_path=r"C:\Users\14032\Desktop\to_csv\txt\test_ecommerce.txt",          # 你的TXT文件路径
        output_dir=r"C:\Users\14032\Desktop\to_csv\csv",            # 输出目录
        delimiter=',',                  # 分隔符（比如空格用' '，制表符用'\t'）
        encoding='utf-8'                # 编码（中文建议用utf-8或gbk）
    )

    # # 示例2：转换单个PDF文件
    # convert_file_to_csv(
    #     input_path=r"C:\Users\14032\Desktop\to_csv\pdf\pdf_test_ecommerce.pdf",          # 你的PDF文件路径
    #     output_dir=r"C:\Users\14032\Desktop\to_csv\csv"
    # )

    # # 示例3：批量转换指定目录下的所有PDF/TXT文件
    # input_dir = "your_files_dir"       # 存放PDF/TXT的目录
    # for file in os.listdir(input_dir):
    #     file_path = os.path.join(input_dir, file)
    #     if file.lower().endswith(('.pdf', '.txt')):
    #         convert_file_to_csv(file_path, "output")