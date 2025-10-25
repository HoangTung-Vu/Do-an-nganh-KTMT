# Ở đây viết logic để xử lý file PDF, bao gồm việc trích xuất văn bản, phân đoạn nội dung, và chuẩn bị dữ liệu cho quá trình embedding và indexing.
# Gồm 2 phần chính 
# - PDF text extraction: sử dụng các thư viện như PyMuPDF, pdfplumber để trích xuất văn bản từ file PDF
# - PDF figure extraction: sử dụng layout detection để tách hình ảnh, biểu đồ từ file PDF