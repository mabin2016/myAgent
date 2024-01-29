import streamlit as st
import requests
from metagpt.config import CONFIG

def send_request(choice, input_text):
    response = "请选择栏目"
    if choice == "技术文档生成":
        action = "nora_article"
    elif choice == "关键词订阅":
        action = "nora_keyword"
    elif choice == "网站列表订阅":
        action = "nora_oss"
    elif choice == "出行助手":
        action = "nora_travel"
    url = "http://0.0.0.0:8000/"
    url = f"{url}{action}?msg={input_text}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                st.write(line.decode('utf-8'))
    else:
        st.write("请求失败，请联系管理员")

def response_function(choice, input_text):
    return send_request(choice, input_text)

def main():
    # 添加选择器和文本输入框
    text_demo = f"""使用例子: 
    1. 技术文档生成: 
        请帮我生成mysql的使用教程
    2. 关键词订阅(需要关注公众号)：
        帮我订阅openai的新闻并发送给我
    3. 网站列表订阅(需要关注公众号)：
        从https://pitchhub.36kr.com/investevent爬取信息，获取融资时间，项目名称，所属行业，融资轮次，融资金额，投资方，详情链接字段，然后发给我
    4. 出行助手：
        我想明天去百色，帮我看下还有哪趟高铁有票，并且看下百色的天气如何，有哪些好玩的
    """
    st.text(text_demo)
    st.text("请扫码关注公众号，以获取订阅信息")
    st.image([CONFIG.WEINXINPUSHER_QRCODE_IMG])

    choice = st.selectbox(options=["技术文档生成", "关键词订阅", "网站列表订阅", "出行助手"], label="请选择", key="choice")
    input_text = st.text_input("请输入文本:", key="input_text")

    if st.button("提交"):
        with st.spinner("处理中，请不要重复点击提交按钮..."):
            response_function(choice, input_text)

if __name__ == "__main__":
    main()
