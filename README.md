# Burp is slow, Metasploit is old, and PKS is gold 🤡
**PKS** là một framework AI agent, tự động cho an ninh mạng — cả tấn công lẫn phòng thủ — chạy hoàn toàn trong terminal. Một `Root agent` điều phối mỗi tác vụ tới đúng chuyên gia: pentest, bug bounty, red team, blue team, DFIR, reverse engineering, web, recon, reporting... Ngoài ra có thể giải CTF pwn / reverse / web / forensic / crypto.
- Tool không build từ code, tool build bằng cà phê, Sting dâu và những bài lab thiếu tài liệu.  
- Vận hành bởi 30+ con agent tranh nhau một bộ nhớ chung.  
- Tự động fuzz web,đánh nhau với binary, chôm flag trước khi mì tôm kịp chín.  
- Mục đích chính: giải CTF, mục đích phụ: phá đám admin hoặc chặn những đứa phá đám khác.  
- Khi lệnh `pks` gõ xuống, pass hay không không quan trọng — quan trọng là có niềm tin...  
> ***Run and dream...***

---

## Điểm nổi bật

- **30+ agent chuyên biệt** phủ toàn bộ phổ — tấn công (pentest, bug bounty, red team, web, recon, reverse) và phòng thủ (blue team, DFIR, điều tra memory/network, purple team, reporting, compliance) — Có agent giải CTF (pwn · reverse · web · forensic · crypto) với đầy đủ toolbox nằm sẵn trong "playbook".
- **Bộ nhớ chung (blackboard)** — mọi lệnh và phát hiện của bất kỳ agent nào đều được ghi lên một `note_finding` chung, đưa vào ngữ cảnh của mọi agent, giúp các agent hiểu được ngữ cảnh của nhau kể cả sau khi chuyển agent, bị ngắt, hay nén ngữ cảnh.
- **Tự động** — không hỏi xác nhận giữa chừng; cứ chạy tới khi xong hoặc bạn dừng.
- **Đọc được chữ trong ảnh** — `pks-ocr` OCR đa lượt + đối chiếu chéo để moi flag/bằng chứng từ ảnh chụp ngay cả khi model không có "mắt".
- **Gọn & nhanh** — cắt output tool thông minh (giữ flag/key, bỏ nhiễu), ước lượng token nhanh, render markdown chịu lỗi, tự nhận diện cửa sổ ngữ cảnh theo từng model.
- **Chạy nhiều mục tiêu cùng lúc** — mỗi mục tiêu/challenge một instance riêng, không đụng nhau.

---

## Yêu cầu

- **Linux / WSL** (nên dùng Kali Linux — nhiều công cụ hỗ trợ).
- **Python 3.10+** (khuyên 3.13).
- **Một endpoint LLM tương thích.** Bạn tự cấu hình trong file `.env`.

---

## Cài đặt 

```bash
# 1. Clone source
git clone https://github.com/SangPK34/pks-sec-agent.git   
cd pks-sec-agent

# 2. Tạo virtualenv và cài PKS + phụ thuộc
python3 -m venv venv
source venv/bin/activate
pip install -e .    

# 3. Cấu hình LLM
cp .env.example .env
nano .env                # điền API_KEY, BASE_URL, MODEL..

# 4. Boot
pks
```


**Đã có sẵn venv?** bỏ qua bước 2, dùng script kèm theo (tự set `PYTHONPATH` và nạp `.env`):

```bash
./run_pks.sh        # sửa đường dẫn venv trong script cho khớp của bạn
```

**Toolbox:** để làm việc thật PKS gọi các công cụ hệ thống (`nmap`, `ffuf`, `sqlmap`,
`pwntools`, `ghidra`, `radare2`, `angr`, `binwalk`, `steghide`, `hashcat`, `volatility3`,
`tesseract`, …). Trên Kali hầu hết đã có; cái nào `which <tool>` báo thiếu thì cài thêm.

---

## Sử dụng

```bash
pks                      # mở REPL, rồi mô tả tác vụ bất kỳ
pks --yolo               # bỏ xác nhận lệnh nhạy cảm (tự động hoàn toàn)
pks --prompt "<your prompt>"   # chạy 1 tác vụ rồi thôi
```

Một số lệnh hữu ích: `/agent` (liệt kê/đổi agent), `/model`, `/env`,
`/parallel` (chạy nhiều agent trên cùng một mục tiêu).

### Chạy nhiều mục tiêu cùng lúc

Mỗi mục tiêu một instance **riêng biệt** — có bảng nhớ chung và scratch `/tmp` riêng, không
lẫn nhau:

```bash
cd ~/work/target1 && pks     # terminal 1  (id instance = target1)
cd ~/work/target2 && pks     # terminal 2
cd ~/CTF/chall1   && pks     # terminal 3
```

Theo dõi tất cả từ một terminal khác:

```bash
watch -n5 'grep -h FLAG ~/.pks/bb_*.json 2>/dev/null || echo "no findings"
```

---

## Cấu hình (`.env`)

| Biến | Ý nghĩa |
|---|---|
| `OPENAI_API_KEY` | key cho endpoint LLM của bạn **(bắt buộc)** |
| `OPENAI_API_BASE` / `OPENAI_BASE_URL` | URL endpoint tương thích OpenAI **(bắt buộc)** |
| `PKS_MODEL` | tên model endpoint của bạn phục vụ **(bắt buộc)** |
| `PKS_LICENSE_OFF=1` | chế độ mở, không kiểm tra license|
| `PKS_STREAM=true` | stream phản hồi của model thời gian thực|
| `PKS_TUI=false` | dùng REPL compact (Nhẹ hơn TUI) |
| `PKS_TELEMETRY=false` | tắt telemetry |
| `PKS_COMPACT_REPL=0` | `0` hiện output tool inline; `1` gom thành pill |
| `PKS_CYBER_PROFILE_MODE` | cỡ baseline cyber: `lite` \| `full` \| `off` |

Các tùy chỉnh nâng cao (cửa sổ ngữ cảnh, ước lượng token, cắt output, blackboard riêng theo
instance) được ghi trong `.env.example`.

---

## Cấu trúc dự án

```
src/pks/          framework (agents, tools, prompts, SDK, REPL/TUI)
src/pks/prompts/  playbook của từng agent (CTF, DFIR, reverse, web, red/blue team, …)
tools/            tiện ích replay / asciinema / gif
tests/            bộ test
run_pks.sh        launcher (set PYTHONPATH, nạp .env)
.env.example      mẫu, copy sang .env rồi sửa
```

---
## Demo mini CTF

<img width="1734" height="994" alt="Screenshot 2026-07-27 084531" src="https://github.com/user-attachments/assets/6e762fc4-f89f-4323-890c-22ee5413767f" />

<img width="1400" height="996" alt="Screenshot 2026-07-27 084945" src="https://github.com/user-attachments/assets/3824bce9-9a50-48e3-9143-208382ab83c0" />

## Vấn đề đạo đức

PKS là công cụ an ninh mạng chỉ được sử dụng với những mục tiêu **được cấp phép**: các engagement có hợp đồng, hệ thống của bạn, môi trường lab, các giải CTF, và học tập/nghiên cứu. Bạn sẽ phải chịu trách nhiệm cho cách sử dụng của mình.

## Giấy phép

Giấy phép kép (MIT và Proprietary) — xem `LICENSE` / `LICENSE-MIT`.

---

<sub>*Customized from cai.*</sub>
