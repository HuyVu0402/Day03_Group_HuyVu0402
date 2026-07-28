"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()


def run_tool(tool_name: str, *args):
    """Gọi một tool từ registry của tools.py."""
    tool_func = AVAILABLE_TOOLS.get(tool_name)
    if tool_func is None:
        return f"LỖI: Không tìm thấy tool '{tool_name}' trong registry."

    try:
        result = tool_func(*args)
        if result is None:
            return "LỖI: Tool không trả về dữ liệu."
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as exc:
        return f"LỖI: Tool '{tool_name}' gặp sự cố: {exc}"


def build_final_answer(provider, user_query: str, observation: str = "") -> str:
    """Tạo final answer an toàn khi provider hoặc tool gặp sự cố."""
    if observation and str(observation).strip():
        prompt = (
            "Bạn chỉ được trả lời bằng một câu trả lời cuối cùng cho người dùng, không được giải thích quá trình hoạt động.\n"
            f"Câu hỏi: {user_query}\n"
            f"Thông tin quan sát: {observation}"
        )
    else:
        prompt = (
            "Bạn chỉ được trả lời bằng một câu trả lời cuối cùng cho người dùng, không được giải thích quá trình hoạt động.\n"
            f"Câu hỏi: {user_query}"
        )

    try:
        answer = provider.generate(prompt, system_prompt=REACT_SYSTEM_PROMPT)
        if answer and str(answer).strip():
            return answer
    except Exception:
        pass

    if observation and str(observation).strip():
        return "Hiện tại tôi chưa nhận được đủ dữ liệu để trả lời chính xác, nhưng bạn có thể kiểm tra lại thông tin vừa thu được hoặc thử lại sau."
    return "Hiện tại tôi chưa nhận được đủ dữ liệu để trả lời chính xác. Bạn có thể thử lại sau."

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời
    try:
        response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    except Exception as exc:
        response = f"Hiện tại tôi không thể trả lời ngay lúc này. Lỗi: {exc}"

    print(f"🤖 Chatbot trả lời:\n{response}")

import re # Cần import thêm thư viện re ở đầu file app.py

def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) thực thụ.
    LLM tự suy luận cần dùng công cụ nào dựa trên câu hỏi của khách.
    """
    print(f"\n🤖 [REACT AGENT] Đang xử lý: {user_query}")
    
    # Khởi tạo lịch sử hội thoại cho vòng lặp ReAct
    agent_scratchpad = f"User: {user_query}\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Bước {step}/{MAX_ITERATIONS}) ---")

        # 1. Gửi toàn bộ quá trình suy luận hiện tại cho LLM
        response = provider.generate(agent_scratchpad, system_prompt=REACT_SYSTEM_PROMPT)
        print(f"{response}") # Hiển thị Thought và Action của LLM

        # 2. Kiểm tra nếu LLM đã đưa ra câu trả lời cuối cùng
        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
            print(f"\n🏁 KẾT QUẢ CUỐI CÙNG:\n{final_answer}")
            return final_answer

        # 3. Phân tích Action để gọi Tool (Định dạng: Action: tool_name["arg1", "arg2"])
        # Sử dụng Regex để tìm tên công cụ và các tham số bên trong ngoặc []
        action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response)
        
        if action_match:
            tool_name = action_match.group(1)
            # Tách các tham số, loại bỏ dấu ngoặc kép và khoảng trắng
            args_str = action_match.group(2)
            # Parse args: hỗ trợ cả "arg1" hoặc "arg1", "arg2"
            tool_args = [arg.strip().strip('"').strip("'") for arg in args_str.split(",") if arg.strip()]

            # 4. Thực thi Tool
            print(f"🛠️  Đang gọi công cụ: {tool_name} với tham số {tool_args}")
            observation = run_tool(tool_name, *tool_args)
            print(f"👁️  Observation (Kết quả): {observation}")

            # 5. Cập nhật scratchpad để LLM đọc ở vòng lặp sau
            agent_scratchpad += f"\n{response}\nObservation: {observation}\n"
        else:
            # Nếu không tìm thấy Action theo định dạng ReAct, yêu cầu LLM điều chỉnh hoặc dừng lại
            print("⚠️ Không nhận diện được Action. Đang yêu cầu AI tổng hợp câu trả lời...")
            agent_scratchpad += f"\n{response}\nObservation: Vui lòng cung cấp đúng định dạng Thought/Action hoặc đưa ra Final Answer."
            
    if step >= MAX_ITERATIONS:
        print(f"🛑 Đạt giới hạn {MAX_ITERATIONS} bước mà chưa có kết quả.")
        return "Xin lỗi, tôi cần thêm thông tin hoặc bộ phận kỹ thuật để xử lý yêu cầu này."

if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    # Chạy thử câu test số 3
    sample_query = tests[2]["question"]
    
    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)
    
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)

