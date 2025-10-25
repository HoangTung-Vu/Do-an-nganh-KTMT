### Note
Backend quản lý thư viện dependencies bằng uv :
* Trước tiên cài đặt python version >= 3.12
* Sau đó cài uv trên python mặc định của máy thông qua : 
```pip install uv```
* Tôi đã kích hoạt `uv init` trên backend nên không cần init lại. Tuy nhiên khi `git clone` project về máy, sẽ chưa có môi trường ảo venv do tôi đã gitignore. Vì vậy trước tiên cần `uv sync` để lấy toàn bộ thư viện từ `pyproject.toml`. Mỗi khi chạy code luôn đảm bảo môi trường đã được activate (lệnh activate như * cuối cùng)
* Khi thêm thư viện thì 
```uv add <tên-thư-viện>```
* Sync lại toàn các thư viện : 
```uv sync```
* Activate lại môi trường venv : 
```​source .venv/bin/activate``` ​( đối với Linux) 
hoặc ```​venv\Scripts\activate``` (đối với Windows)