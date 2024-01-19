from mlx_lm import load
from mlx_lm.utils import generate_step
import mlx.core as mx
import streamlit as st
from tqdm import tqdm

tqdm(disable=True, total=0)  # initialise internal lock

title = "MLX Chat"
ver = "0.6.5"
debug = False

st.set_page_config(
    page_title=title,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title(title)

assistant_greeting = "How may I help you?"

model_ref = st.sidebar.text_input("model", "mlx-community/Nous-Hermes-2-Mixtral-8x7B-DPO-4bit")
prompt_sys = st.sidebar.text_area("system prompt",
                                  "You are an AI assistant, a large language model trained by awesome data "
                                  "scientists. Answer as concisely as possible.")
n_ctx = st.sidebar.number_input('context length', value=300, min_value=100, step=100, max_value=32000)
st.sidebar.markdown("---")
actions = st.sidebar.columns(2)
st.sidebar.markdown("---")
st.sidebar.markdown(f"v{ver} / st {st.__version__}")


@st.cache_resource(show_spinner=True, hash_funcs={str: lambda x: None})
def load_model(ref):
    return load(ref)


model, tokenizer = load_model(model_ref)


def generate(the_prompt, the_model):
    tokens = []
    skip = 0
    for token, _ in zip(generate_step(mx.array(tokenizer.encode(the_prompt)), the_model, 0.7), range(n_ctx)):
        if token == tokenizer.eos_token_id:
            break
        tokens.append(token.item())
        s = tokenizer.decode(tokens)
        yield s[skip:]
        skip = len(s)


def show_chat(the_prompt, previous=""):
    if debug:
        print("---------------\n")
        print(the_prompt)
        print("---------------\n")
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response = previous

        for chunk in generate(the_prompt, model):
            response = (response + chunk).replace('�', '')
            message_placeholder.markdown(response + "▌")

        message_placeholder.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": assistant_greeting}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    full_prompt = f"<|im_start|>system\n{prompt_sys}\n"

    if len(st.session_state.messages) > 1:
        full_prompt += ("\nThe following text represents your previous conversations. DO NOT include this text "
                        "directly in your responses.\n\n")
        for msg in st.session_state.messages[:-1]:
            full_prompt += f"{'ME' if msg['role'] == 'assistant' else 'USER'}:\n\n{msg['content']}\n\n"

    full_prompt += "<|im_end|>\n"

    full_prompt += (f"<|im_start|>user\n{prompt}\n<|im_end|>\n"
                    f"<|im_start|>assistant\n")

    show_chat(full_prompt)

if st.session_state.messages and sum(msg["role"] == "assistant" for msg in st.session_state.messages) > 1:
    if actions[0].button("Reset"):
        st.session_state.messages = [{"role": "assistant", "content": assistant_greeting}]
        st.rerun()

if st.session_state.messages and sum(msg["role"] == "assistant" for msg in st.session_state.messages) > 1:
    if actions[1].button("Continue", key='continue'):
        user_prompts = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]
        last_prompt = user_prompts[-1] or "Please continue your response"
        assistant_responses = [msg["content"] for msg in st.session_state.messages if msg["role"] == "assistant"]
        last_assistant_response = assistant_responses[-1] if assistant_responses else ""
        full_prompt = (f"<|im_start|>user\n{last_prompt}<|im_end|>\n"
                       f"<|im_start|>assistant\n{last_assistant_response}\n")
        show_chat(full_prompt, last_assistant_response)
