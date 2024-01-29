import streamlit as st
import requests

def send_request(choice, input_text):
    response = "请选择栏目"
    if choice == "技术文档生成":
        action = "nora_article"
    elif choice == "关键词订阅":
        action = "nora_keyword"
    elif choice == "网站列表订阅":
        action = "nora_oss"
    elif choice == "旅游胜地介绍":
        action = "nora_travel"
    url = "http://0.0.0.0:8000/"
    url = f"{url}{action}?msg={input_text}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                st.write(line.decode('utf-8'))

def response_function(choice, input_text):
    return send_request(choice, input_text)

def main():
    # 添加选择器和文本输入框
    choice = st.selectbox(options=["技术文档生成", "关键词订阅", "网站列表订阅", "生活助手"], label="请选择", key="choice")
    input_text = st.text_input("请输入文本:", key="input_text")

    # 当用户点击提交按钮时发送请求并显示结果
    if st.button("提交", key="submit"):
        result = response_function(choice, input_text)
        # st.write(result)

if __name__ == "__main__":
    main()
