import streamlit as st
import requests

def send_request(choice, input_text, input_mail):
    response = "请选择栏目"
    if choice == "技术文档生成":
        action = "nora_article"
    elif choice == "关键词订阅":
        action = "nora_keyword"
    # elif choice == "网站列表订阅":
    #     action = "nora_oss"
    elif choice == "出行助手":
        action = "nora_travel"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"http://localhost:8000/{action}?msg={input_text}&mail={input_mail}"
    print(url)
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                st.write(line.decode('utf-8'))
    else:
        st.write("请求失败，请联系管理员")

def main():
    # 添加选择器和文本输入框
    
    # 3. 网站列表订阅(需要填写邮箱),tips：只适合简单列表的网站，过于复杂的网站会抓取失败：
    #     从https://pitchhub.36kr.com/investevent爬取信息，获取融资时间，项目名称，所属行业，融资轮次，融资金额，投资方，详情链接字段，然后发给我
    text_demo = f"""这是一个简单智能体，使用例子: 
    1. 技术文档生成: 
        请帮我生成mysql的使用教程
    2. 出行助手：
        我想明天去上海，帮我看下还有哪趟高铁有票，并且看下上海的天气如何，有哪些好玩的
    3. 关键词订阅(需要填写邮箱)：
        帮我订阅openai的新闻并发送给我
        
    TODO: 
        1. 订阅网址：订阅指定网址，提取关键信息并总结
        2. 图表识别：上传表格的图片，识别文本并总结（技术栈：PaddleStructured、yi-vl-plus模型API）
        3. 图片生成：自然语言输入后提取关键信息组合成符合Stable Diffusion格式的提示词，调用Stable Diffusion接口生成图片
        4. 数据采集：爬取指定某个网站多个页面信息，提取文本和图片（ocr识别后转文本语义），清洗，入库（mysql和向量库），以便提供RAG服务
        5. 数据生成：训练数据生成：上传文本数据，选择模型，自动生成对应模型格式训练数据（比如问答对，工具调用的语料）
        6. SQL生成：训练NL2Sql模型，上传数据文件(csv)，输入自然语言，输出SQL语句
        
        其他：利用大模型推理和生成能力，结合工具API，比如 https://www.free-api.com，探索更多功能
        
    """
    st.text(text_demo)
    # st.text("请扫码关注公众号，以获取订阅信息")
    # st.image([CONFIG.WEINXINPUSHER_QRCODE_IMG])

    choice = st.selectbox(options=["技术文档生成", "关键词订阅", "出行助手"], label="请选择", key="choice")
    input_mail = st.text_input("请输入邮箱:", key="input_mail")
    input_text = st.text_input("请输入文本:", key="input_text")

    if st.button("提交"):
        with st.spinner("处理中，请不要重复点击提交按钮..."):
            send_request(choice, input_text, input_mail)

if __name__ == "__main__":
    main()
