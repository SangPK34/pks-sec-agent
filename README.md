# PKS — Đội AI an ninh mạng trong terminal 🕵️

> *Burp is slow, Metasploit is old, and PKS is gold* 🤡

> Tool không build từ code, tool build bằng cà phê, Sting dâu và những bài lab thiếu
> tài liệu, vận hành bởi 30+ con agent tranh nhau một bộ nhớ chung. Tự động fuzz web,
> đánh nhau với binary, đọc flag trước khi mì tôm kịp chín. **Mục đích chính:** giải CTF.
> **Mục đích phụ:** phá đám admin hoặc chặn những thằng phá đám khác. Khi lệnh `pks` gõ
> xuống, pass hay không không quan trọng — quan trọng là niềm tin. *Run and dream...*

**PKS** (tên thân mật *"Tool Nhà Nghèo"*) là một AI **đa agent, tự động** cho an ninh
mạng — cả tấn công lẫn phòng thủ — chạy hoàn toàn trong terminal. Một Selection agent
điều phối mỗi tác vụ tới đúng chuyên gia — pentest, bug bounty, red team, blue team,
DFIR, reverse engineering, web, recon, reporting — và tất cả dùng chung một bộ nhớ. Kèm
theo **chế độ CTF** tự giải pwn / reverse / web / forensic / crypto từ đầu đến cuối.

> ⚖️ **Chỉ dùng khi được phép** — pentest có hợp đồng, hệ thống của chính bạn, môi
> trường lab, thi CTF, và học tập/nghiên cứu. Xem mục **Đạo đức sử dụng** ở cuối.

---

## Điểm nổi bật

- **30+ agent chuyên biệt** phủ toàn bộ phổ — tấn công (pentest, bug bounty, red team,
  web, recon, reverse) và phòng thủ (blue team, DFIR, điều tra memory/network, purple
  team, reporting, compliance) — cộng thêm một **agent giải CTF** riêng (pwn · reverse ·
  web · forensic · crypto) với đầy đủ toolbox nằm sẵn trong "playbook".
- **Bộ nhớ chung (blackboard)** — mọi lệnh và phát hiện của bất kỳ agent nào đều được ghi
  lên một bảng chung, nhồi vào ngữ cảnh của mọi agent. Hỏi *"nãy giờ tìm được gì rồi?"* là
  nó trả lời chính xác, kể cả sau khi chuyển agent, bị ngắt, hay nén ngữ cảnh.
- **Tự động** — không hỏi xác nhận giữa chừng; cứ chạy tới khi xong hoặc bạn dừng.
- **Đọc được chữ trong ảnh** — `pks-ocr` OCR đa lượt + đối chiếu chéo để moi flag/bằng
  chứng từ ảnh chụp ngay cả khi model không có "mắt".
- **Gọn & nhanh** — cắt output tool thông minh (giữ flag/key, bỏ nhiễu), ước lượng token
  nhanh, render markdown chịu lỗi, tự nhận diện cửa sổ ngữ cảnh theo từng model.
- **Chạy nhiều mục tiêu cùng lúc** — mỗi mục tiêu/challenge một instance riêng, không lẫn.
- **Riêng tư mặc định** — không telemetry, không gửi dữ liệu ra ngoài, không thu thập.
- **Trả lời bạn bằng tiếng Việt.**

---

## Yêu cầu

- **Linux / WSL** (khuyên dùng Kali Linux — hầu hết công cụ đã cài sẵn).
- **Python 3.10+** (khuyên 3.13).
- **Một endpoint LLM tương thích OpenAI.** PKS không kèm model; nó nói chuyện với bất kỳ
  API tương thích OpenAI nào — gateway local (LiteLLM / vLLM / Ollama chế độ openai) hoặc
  endpoint hosted. Bạn tự cấp URL, key và tên model trong `.env`.

---

## Cài đặt — tải về, sửa `.env`, chạy

```bash
# 1. Lấy code
git clone <your-repo-url> pks-sec-agent     # hoặc copy nguyên thư mục
cd pks-sec-agent

# 2. Tạo virtualenv và cài PKS + phụ thuộc
python3 -m venv venv
source venv/bin/activate
pip install -e .                            # bước này tạo ra lệnh `pks`

# 3. Cấu hình — BƯỚC DUY NHẤT để chạy được
cp .env.example .env
nano .env                                   # điền OPENAI_API_KEY, OPENAI_API_BASE, PKS_MODEL

# 4. Chạy
pks
```

Vậy là xong — sửa 3 giá trị trong `.env` là `pks` khởi động.

**Đã có sẵn venv?** bỏ qua bước 2, dùng script kèm theo (tự set `PYTHONPATH` và nạp `.env`):

```bash
./run_pks.sh            # sửa đường dẫn venv bên trong script cho khớp máy bạn
```

**Toolbox:** để làm việc thật PKS gọi các công cụ hệ thống (`nmap`, `ffuf`, `sqlmap`,
`pwntools`, `ghidra`, `radare2`, `angr`, `binwalk`, `steghide`, `hashcat`, `volatility3`,
`tesseract`, …). Trên Kali hầu hết đã có; cái nào `which <tool>` báo thiếu thì cài thêm.

---

## Sử dụng

```bash
pks                       # mở REPL, rồi mô tả tác vụ bất kỳ
pks --yolo               # bỏ xác nhận lệnh nhạy cảm (tự động hoàn toàn)
pks --unrestricted       # bật steering (uncensored) trên endpoint của bạn
pks --prompt "recon và liệt kê dịch vụ trên 10.10.10.5"   # chạy 1 tác vụ rồi thôi
```

Cứ mô tả điều bạn muốn — *"pentest con máy này"*, *"triage mục tiêu bug bounty"*,
*"điều tra bản dump memory này"*, *"giải bài CTF trong ./chall"* — Selection agent sẽ giao
cho đúng chuyên gia. Lệnh hữu ích: `/agent` (liệt kê/đổi agent), `/model`, `/env`,
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
watch -n5 'grep -h FLAG ~/.pks/bb_*.json 2>/dev/null || echo "chưa xác nhận gì"'
```

---

## Cấu hình (`.env`)

| Biến | Ý nghĩa |
|---|---|
| `OPENAI_API_KEY` | key cho endpoint LLM của bạn **(bắt buộc)** |
| `OPENAI_API_BASE` / `OPENAI_BASE_URL` | URL endpoint tương thích OpenAI **(bắt buộc)** |
| `PKS_MODEL` | tên model endpoint của bạn phục vụ **(bắt buộc)** |
| `PKS_LICENSE_OFF=1` | chế độ mở — không kiểm license, không gửi dữ liệu ra ngoài |
| `PKS_STREAM=true` | stream output của model |
| `PKS_TUI=false` | dùng REPL compact (không dùng TUI nặng) |
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
pricings/         bảng cửa sổ ngữ cảnh / pricing theo model
tools/            tiện ích replay / asciinema / gif
tests/            bộ test
run_pks.sh        launcher (set PYTHONPATH, nạp .env)
.env.example      copy sang .env rồi sửa
```

---

## Đạo đức sử dụng

PKS là công cụ an ninh mạng lưỡng dụng. Chỉ dùng ở nơi bạn **được phép rõ ràng**: các
engagement có hợp đồng, hệ thống của chính bạn, môi trường lab, các giải CTF, và học
tập/nghiên cứu có sự cho phép. Bạn chịu trách nhiệm cho cách mình sử dụng.

## Giấy phép

Giấy phép kép (MIT và Proprietary) — xem `LICENSE` / `LICENSE-MIT`.

---

<sub>*Customized from CAI.*</sub>
